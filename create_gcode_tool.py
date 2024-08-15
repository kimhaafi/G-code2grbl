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


class Line:
    def __init__(self, curves, start_feedrate, end_feedrate, interpolation):
        self.curves = curves
        self.start_feedrate = start_feedrate
        self.end_feedrate = end_feedrate
        self.interpolation = interpolation


class GCodePainter:
    def __init__(self, master):
        self.master = master
        self.master.title(
            "G-code Painter with Bézier Curves and Interpolated Feedrates"
        )
        self.master.geometry("1200x800")

        self.canvas_width_mm = 100
        self.canvas_height_mm = 100
        self.lines = []
        self.current_line = []
        self.dragging = None
        self.drawing_line = False

        self.z_up = 5
        self.z_down = 0

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Canvas size inputs
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

        # Z height inputs
        z_frame = ttk.Frame(left_frame)
        z_frame.grid(row=2, column=0, pady=5)

        ttk.Label(z_frame, text="Z-up (mm):").grid(row=0, column=0)
        self.z_up_entry = ttk.Entry(z_frame, width=10)
        self.z_up_entry.insert(0, str(self.z_up))
        self.z_up_entry.grid(row=0, column=1)

        ttk.Label(z_frame, text="Z-down (mm):").grid(row=1, column=0)
        self.z_down_entry = ttk.Entry(z_frame, width=10)
        self.z_down_entry.insert(0, str(self.z_down))
        self.z_down_entry.grid(row=1, column=1)

        set_z_button = ttk.Button(
            left_frame, text="Set Z Heights", command=self.set_z_heights
        )
        set_z_button.grid(row=3, column=0, pady=5)

        self.start_line_button = ttk.Button(
            left_frame, text="Start Line", command=self.start_line
        )
        self.start_line_button.grid(row=4, column=0, pady=5)

        # Feedrate inputs for ending a line
        feedrate_frame = ttk.Frame(left_frame)
        feedrate_frame.grid(row=5, column=0, pady=5)

        ttk.Label(feedrate_frame, text="Start Feedrate:").grid(row=0, column=0)
        self.start_feedrate_entry = ttk.Entry(feedrate_frame, width=10)
        self.start_feedrate_entry.insert(0, "1000")
        self.start_feedrate_entry.grid(row=0, column=1)

        ttk.Label(feedrate_frame, text="End Feedrate:").grid(row=1, column=0)
        self.end_feedrate_entry = ttk.Entry(feedrate_frame, width=10)
        self.end_feedrate_entry.insert(0, "1000")
        self.end_feedrate_entry.grid(row=1, column=1)

        ttk.Label(feedrate_frame, text="Interpolation:").grid(row=2, column=0)
        self.interpolation_var = tk.StringVar(value="linear")
        self.interpolation_combo = ttk.Combobox(
            feedrate_frame,
            textvariable=self.interpolation_var,
            values=["linear", "exponential", "logarithmic"],
        )
        self.interpolation_combo.grid(row=2, column=1)

        self.end_line_button = ttk.Button(
            left_frame, text="End Line", command=self.end_line, state=tk.DISABLED
        )
        self.end_line_button.grid(row=6, column=0, pady=5)

        self.canvas = tk.Canvas(left_frame, width=600, height=600, bg="white")
        self.canvas.grid(row=7, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(7, weight=1)

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
            self.lines.clear()
            self.current_line.clear()
            self.redraw_canvas()
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter numeric values for width and height."
            )

    def set_z_heights(self):
        try:
            self.z_up = float(self.z_up_entry.get())
            self.z_down = float(self.z_down_entry.get())
            messagebox.showinfo(
                "Z Heights Set", f"Z-up: {self.z_up} mm\nZ-down: {self.z_down} mm"
            )
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter numeric values for Z heights."
            )

    def start_line(self):
        self.drawing_line = True
        self.current_line.clear()
        self.start_line_button.config(state=tk.DISABLED)
        self.end_line_button.config(state=tk.NORMAL)

    def end_line(self):
        self.drawing_line = False
        self.start_line_button.config(state=tk.NORMAL)
        self.end_line_button.config(state=tk.DISABLED)
        if self.current_line:
            try:
                start_feedrate = float(self.start_feedrate_entry.get())
                end_feedrate = float(self.end_feedrate_entry.get())
                interpolation = self.interpolation_var.get()
                self.lines.append(
                    Line(self.current_line, start_feedrate, end_feedrate, interpolation)
                )
                self.current_line = []
                self.redraw_canvas()
            except ValueError:
                messagebox.showerror(
                    "Invalid Input", "Please enter numeric values for feedrates."
                )

    def on_canvas_click(self, event):
        x_mm, y_mm = self.pixel_to_mm(event.x, event.y)

        if self.drawing_line:
            if not self.current_line or self.current_line[-1].end != (x_mm, y_mm):
                if self.current_line:
                    start = self.current_line[-1].end
                else:
                    start = (x_mm, y_mm)
                end = (x_mm, y_mm)
                control1 = (
                    start[0] + (end[0] - start[0]) / 3,
                    start[1] + (end[1] - start[1]) / 3,
                )
                control2 = (
                    start[0] + 2 * (end[0] - start[0]) / 3,
                    start[1] + 2 * (end[1] - start[1]) / 3,
                )
                self.current_line.append(BezierCurve(start, end, control1, control2))
        else:
            # Check if we're clicking on a control point
            for line in self.lines:
                for curve in line.curves:
                    if self.is_point_near(x_mm, y_mm, curve.control1):
                        self.dragging = (curve, "control1")
                        break
                    elif self.is_point_near(x_mm, y_mm, curve.control2):
                        self.dragging = (curve, "control2")
                        break
                if self.dragging:
                    break

            # Check current_line separately
            if not self.dragging:
                for curve in self.current_line:
                    if self.is_point_near(x_mm, y_mm, curve.control1):
                        self.dragging = (curve, "control1")
                        break
                    elif self.is_point_near(x_mm, y_mm, curve.control2):
                        self.dragging = (curve, "control2")
                        break

        self.redraw_canvas()

    def on_drag(self, event):
        x_mm, y_mm = self.pixel_to_mm(event.x, event.y)

        if self.dragging:
            curve, point = self.dragging
            if point == "control1":
                curve.control1 = (x_mm, y_mm)
            elif point == "control2":
                curve.control2 = (x_mm, y_mm)
            self.redraw_canvas()
        elif self.drawing_line and self.current_line:
            self.current_line[-1].end = (x_mm, y_mm)
            self.current_line[-1].control2 = (
                self.current_line[-1].start[0]
                + 2 * (x_mm - self.current_line[-1].start[0]) / 3,
                self.current_line[-1].start[1]
                + 2 * (y_mm - self.current_line[-1].start[1]) / 3,
            )
            self.redraw_canvas()

    def on_release(self, event):
        self.dragging = None

    def is_point_near(self, x, y, point, threshold=5):
        return math.hypot(x - point[0], y - point[1]) < threshold

    def redraw_canvas(self):
        self.canvas.delete("all")

        # Draw border
        self.canvas.create_rectangle(
            0, 0, self.canvas.winfo_width() - 1, self.canvas.winfo_height() - 1
        )

        # Draw all lines
        for line in self.lines:
            for curve in line.curves:
                self.draw_bezier_curve(curve)

        # Draw current line
        for curve in self.current_line:
            self.draw_bezier_curve(curve)

    def draw_bezier_curve(self, curve):
        start = self.mm_to_pixel(curve.start)
        end = self.mm_to_pixel(curve.end)
        control1 = self.mm_to_pixel(curve.control1)
        control2 = self.mm_to_pixel(curve.control2)

        # Draw curve
        points = [self.mm_to_pixel(curve.point_at(t / 100)) for t in range(101)]
        self.canvas.create_line(points, fill="blue", smooth=True, width=2)

        # Draw control points and lines
        self.canvas.create_line(start, control1, fill="gray", dash=(2, 2))
        self.canvas.create_line(end, control2, fill="gray", dash=(2, 2))
        self.canvas.create_oval(
            control1[0] - 5,
            control1[1] - 5,
            control1[0] + 5,
            control1[1] + 5,
            fill="green",
            outline="black",
        )
        self.canvas.create_oval(
            control2[0] - 5,
            control2[1] - 5,
            control2[0] + 5,
            control2[1] + 5,
            fill="green",
            outline="black",
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

    def pixel_to_mm(self, x_pixel, y_pixel):
        x_mm = x_pixel / self.canvas.winfo_width() * self.canvas_width_mm
        y_mm = (
            (self.canvas.winfo_height() - y_pixel)
            / self.canvas.winfo_height()
            * self.canvas_height_mm
        )
        return (x_mm, y_mm)

    def generate_gcode(self):
        gcode = "G21 ; Set units to millimeters\n"
        gcode += "G90 ; Use absolute coordinates\n"
        gcode += f"G0 Z{self.z_up:.2f} F{max(line.start_feedrate for line in self.lines):.2f} ; Lift the pen/tool\n"

        for i, line in enumerate(self.lines):
            gcode += f"G0 X{line.curves[0].start[0]:.2f} Y{line.curves[0].start[1]:.2f} F{line.start_feedrate:.2f} ; Move to starting point of line {i+1}\n"
            gcode += f"G0 Z{self.z_down:.2f} ; Lower the pen/tool\n"

            total_length = sum(self.curve_length(curve) for curve in line.curves)
            current_length = 0

            for curve in line.curves:
                curve_gcode, curve_length = self.curve_to_gcode(
                    curve,
                    line.start_feedrate,
                    line.end_feedrate,
                    current_length / total_length,
                    (current_length + self.curve_length(curve)) / total_length,
                    line.interpolation,
                )
                gcode += curve_gcode
                current_length += curve_length

            gcode += f"G0 Z{self.z_up:.2f} ; Lift the pen/tool\n"

        gcode += f"G0 X0 Y0 F{max(line.end_feedrate for line in self.lines):.2f} ; Return to origin\n"

        self.gcode_output.delete(1.0, tk.END)
        self.gcode_output.insert(tk.END, gcode)

    def curve_to_gcode(
        self, curve, start_feedrate, end_feedrate, start_t, end_t, interpolation
    ):
        # Convert Bézier curve to circular arc
        center, radius, start_angle, end_angle, direction = self.bezier_to_arc(curve)

        progress = (
            start_t + end_t
        ) / 2  # Use middle of the curve for feedrate calculation
        if interpolation == "linear":
            feedrate = start_feedrate + (end_feedrate - start_feedrate) * progress
        elif interpolation == "exponential":
            feedrate = start_feedrate * (end_feedrate / start_feedrate) ** progress
        elif interpolation == "logarithmic":
            feedrate = start_feedrate + (end_feedrate - start_feedrate) * math.log(
                1 + 9 * progress
            ) / math.log(10)

        # Generate G-code for the arc
        if direction == 1:
            gcode = f"G02 X{curve.end[0]:.4f} Y{curve.end[1]:.4f} I{center[0] - curve.start[0]:.4f} J{center[1] - curve.start[1]:.4f} F{feedrate:.2f} ; Clockwise arc\n"
        else:
            gcode = f"G03 X{curve.end[0]:.4f} Y{curve.end[1]:.4f} I{center[0] - curve.start[0]:.4f} J{center[1] - curve.start[1]:.4f} F{feedrate:.2f} ; Counterclockwise arc\n"

        return gcode, self.arc_length(radius, start_angle, end_angle)

    def bezier_to_arc(self, curve):
        # Calculate the midpoint of the Bézier curve
        mid = curve.point_at(0.5)

        # Calculate the center of the circular arc
        center_x = 2 * mid[0] - 0.5 * (curve.start[0] + curve.end[0])
        center_y = 2 * mid[1] - 0.5 * (curve.start[1] + curve.end[1])
        center = (center_x, center_y)

        # Calculate the radius
        radius = math.hypot(center[0] - curve.start[0], center[1] - curve.start[1])

        # Calculate start and end angles
        start_angle = math.atan2(curve.start[1] - center[1], curve.start[0] - center[0])
        end_angle = math.atan2(curve.end[1] - center[1], curve.end[0] - center[0])

        # Determine the direction (clockwise or counterclockwise)
        direction = (
            1
            if (curve.control1[0] - curve.start[0]) * (curve.control1[1] - curve.end[1])
            - (curve.control1[1] - curve.start[1]) * (curve.control1[0] - curve.end[0])
            > 0
            else -1
        )

        return center, radius, start_angle, end_angle, direction

    def arc_length(self, radius, start_angle, end_angle):
        angle = abs(end_angle - start_angle)
        if angle > math.pi:
            angle = 2 * math.pi - angle
        return radius * angle

    def curve_length(self, curve, segments=100):
        length = 0
        last_point = curve.start
        for i in range(1, segments + 1):
            t = i / segments
            point = curve.point_at(t)
            length += math.hypot(point[0] - last_point[0], point[1] - last_point[1])
            last_point = point
        return length

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
