import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import math


class BezierCurve:
    def __init__(self, start, end, control1, control2):
        self.start = start
        self.end = end
        self.control1 = control1
        self.control2 = control2

    def point_at(self, t):
        x = (
            (1 - t) ** 3 * self.start[0]
            + 3 * (1 - t) ** 2 * t * self.control1[0]
            + 3 * (1 - t) * t**2 * self.control2[0]
            + t**3 * self.end[0]
        )
        y = (
            (1 - t) ** 3 * self.start[1]
            + 3 * (1 - t) ** 2 * t * self.control1[1]
            + 3 * (1 - t) * t**2 * self.control2[1]
            + t**3 * self.end[1]
        )
        return (x, y)


class GCodePainter:
    def __init__(self, master):
        self.master = master
        self.master.title("G-code Painter with Bézier Curves")
        self.master.geometry("1000x700")

        self.canvas_width_mm = 100
        self.canvas_height_mm = 100
        self.points = []
        self.curves = []
        self.current_curve = None
        self.dragging = None
        self.drawing_line = False

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        size_frame = ttk.Frame(left_frame)
        size_frame.grid(row=0, column=0, pady=5)

        ttk.Label(size_frame, text="Canvas Size (mm):").grid(row=0, column=0)
        self.width_entry = ttk.Entry(size_frame, width=10)
        self.width_entry.grid(row=0, column=1)
        ttk.Label(size_frame, text="x").grid(row=0, column=2)
        self.height_entry = ttk.Entry(size_frame, width=10)
        self.height_entry.grid(row=0, column=3)

        set_size_button = ttk.Button(
            left_frame, text="Set Canvas Size", command=self.set_canvas_size
        )
        set_size_button.grid(row=1, column=0, pady=5)

        self.start_line_button = ttk.Button(
            left_frame, text="Start Line", command=self.start_line
        )
        self.start_line_button.grid(row=2, column=0, pady=5)

        self.end_line_button = ttk.Button(
            left_frame, text="End Line", command=self.end_line, state=tk.DISABLED
        )
        self.end_line_button.grid(row=3, column=0, pady=5)

        self.canvas = tk.Canvas(left_frame, width=600, height=600, bg="white")
        self.canvas.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(4, weight=1)

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)

        self.gcode_output = tk.Text(right_frame, wrap=tk.WORD, width=40, height=20)
        self.gcode_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.gcode_output.insert(tk.END, "G-code will appear here")

        generate_button = ttk.Button(
            right_frame, text="Generate G-code", command=self.generate_gcode
        )
        generate_button.grid(row=1, column=0, pady=5)

        save_button = ttk.Button(
            right_frame, text="Save G-code", command=self.save_gcode
        )
        save_button.grid(row=2, column=0, pady=5)

        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

    def set_canvas_size(self):
        try:
            self.canvas_width_mm = float(self.width_entry.get())
            self.canvas_height_mm = float(self.height_entry.get())
            self.points.clear()
            self.curves.clear()
            self.current_curve = None
            self.redraw_canvas()
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter numeric values for width and height."
            )

    def start_line(self):
        self.drawing_line = True
        self.start_line_button.config(state=tk.DISABLED)
        self.end_line_button.config(state=tk.NORMAL)

    def end_line(self):
        self.drawing_line = False
        self.start_line_button.config(state=tk.NORMAL)
        self.end_line_button.config(state=tk.DISABLED)
        self.current_curve = None

    def on_canvas_click(self, event):
        if not self.drawing_line:
            return

        x_mm = event.x / self.canvas.winfo_width() * self.canvas_width_mm
        y_mm = (
            (self.canvas.winfo_height() - event.y)
            / self.canvas.winfo_height()
            * self.canvas_height_mm
        )

        if self.current_curve is None:
            self.current_curve = BezierCurve(
                (x_mm, y_mm), (x_mm, y_mm), (x_mm, y_mm), (x_mm, y_mm)
            )
        else:
            self.curves.append(self.current_curve)
            self.current_curve = BezierCurve(
                self.current_curve.end, (x_mm, y_mm), (x_mm, y_mm), (x_mm, y_mm)
            )

        self.redraw_canvas()

    def on_drag(self, event):
        if not self.drawing_line or self.current_curve is None:
            return

        x_mm = event.x / self.canvas.winfo_width() * self.canvas_width_mm
        y_mm = (
            (self.canvas.winfo_height() - event.y)
            / self.canvas.winfo_height()
            * self.canvas_height_mm
        )

        if self.dragging is None:
            dx = x_mm - self.current_curve.end[0]
            dy = y_mm - self.current_curve.end[1]
            self.current_curve.control1 = (
                self.current_curve.start[0] + dx / 3,
                self.current_curve.start[1] + dy / 3,
            )
            self.current_curve.control2 = (
                self.current_curve.end[0] - dx / 3,
                self.current_curve.end[1] - dy / 3,
            )
            self.current_curve.end = (x_mm, y_mm)
        elif self.dragging == "control1":
            self.current_curve.control1 = (x_mm, y_mm)
        elif self.dragging == "control2":
            self.current_curve.control2 = (x_mm, y_mm)

        self.redraw_canvas()

    def on_release(self, event):
        self.dragging = None

    def redraw_canvas(self):
        self.canvas.delete("all")

        # Draw border
        self.canvas.create_rectangle(
            0, 0, self.canvas.winfo_width() - 1, self.canvas.winfo_height() - 1
        )

        # Draw curves
        for curve in self.curves:
            self.draw_bezier_curve(curve)

        # Draw current curve
        if self.current_curve:
            self.draw_bezier_curve(self.current_curve)

    def draw_bezier_curve(self, curve):
        start = self.mm_to_pixel(curve.start)
        end = self.mm_to_pixel(curve.end)
        control1 = self.mm_to_pixel(curve.control1)
        control2 = self.mm_to_pixel(curve.control2)

        # Draw curve
        points = [self.mm_to_pixel(curve.point_at(t / 100)) for t in range(101)]
        self.canvas.create_line(points, fill="blue", smooth=True)

        # Draw control points and lines
        self.canvas.create_line(start, control1, fill="gray", dash=(2, 2))
        self.canvas.create_line(end, control2, fill="gray", dash=(2, 2))
        self.canvas.create_oval(
            control1[0] - 3,
            control1[1] - 3,
            control1[0] + 3,
            control1[1] + 3,
            fill="green",
        )
        self.canvas.create_oval(
            control2[0] - 3,
            control2[1] - 3,
            control2[0] + 3,
            control2[1] + 3,
            fill="green",
        )

        # Draw end points
        self.canvas.create_oval(
            start[0] - 3, start[1] - 3, start[0] + 3, start[1] + 3, fill="red"
        )
        self.canvas.create_oval(
            end[0] - 3, end[1] - 3, end[0] + 3, end[1] + 3, fill="red"
        )

    def mm_to_pixel(self, point_mm):
        x_pixel = point_mm[0] / self.canvas_width_mm * self.canvas.winfo_width()
        y_pixel = self.canvas.winfo_height() - (
            point_mm[1] / self.canvas_height_mm * self.canvas.winfo_height()
        )
        return (x_pixel, y_pixel)

    def generate_gcode(self):
        gcode = "G21 ; Set units to millimeters\n"
        gcode += "G90 ; Use absolute coordinates\n"
        gcode += "G0 Z5 ; Lift the pen/tool\n"

        for i, curve in enumerate(self.curves):
            if i == 0:
                gcode += f"G0 X{curve.start[0]:.2f} Y{curve.start[1]:.2f} ; Move to starting point\n"
                gcode += "G0 Z0 ; Lower the pen/tool\n"

            gcode += self.curve_to_gcode(curve)

        gcode += "G0 Z5 ; Lift the pen/tool\n"
        gcode += "G0 X0 Y0 ; Return to origin\n"

        self.gcode_output.delete(1.0, tk.END)
        self.gcode_output.insert(tk.END, gcode)

    def curve_to_gcode(self, curve, segments=10):
        gcode = ""
        for i in range(1, segments + 1):
            t = i / segments
            point = curve.point_at(t)
            gcode += f"G1 X{point[0]:.2f} Y{point[1]:.2f} ; Bézier curve point\n"
        return gcode

    def save_gcode(self):
        gcode = self.gcode_output.get(1.0, tk.END)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".gcode",
            filetypes=[("G-code files", "*.gcode"), ("All files", "*.*")],
        )
        if file_path:
            with open(file_path, "w") as file:
                file.write(gcode)
            messagebox.showinfo("Save Successful", f"G-code saved to {file_path}")


def main():
    root = tk.Tk()
    app = GCodePainter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
