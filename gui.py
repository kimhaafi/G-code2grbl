import os
import sys
import serial
import serial.tools.list_ports
from utils.machine import stream_gcode
from dotenv import load_dotenv
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import queue
import json

load_dotenv()

PROGRESS_FILE = "gcode_progress.json"


class GCodeRunner:
    def __init__(self, master):
        self.master = master
        master.title("G-code Runner")
        master.geometry("500x400")

        self.ser = None
        self.gcode_thread = None
        self.running = False
        self.stop_requested = False
        self.queue = queue.Queue()
        self.current_file_index = 0

        # Port selection
        ttk.Label(master, text="Select Port:").pack(pady=5)
        self.port_combo = ttk.Combobox(master)
        self.refresh_ports()
        self.port_combo.pack(pady=5)

        # File list and buttons
        list_frame = ttk.Frame(master)
        list_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        self.file_list = tk.Listbox(list_frame, selectmode=tk.MULTIPLE)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        list_buttons = ttk.Frame(list_frame)
        list_buttons.pack(side=tk.LEFT, padx=5)

        self.add_file_button = ttk.Button(
            list_buttons, text="Add File", command=self.add_file
        )
        self.add_file_button.pack(pady=2)

        self.remove_file_button = ttk.Button(
            list_buttons, text="Remove File", command=self.remove_file
        )
        self.remove_file_button.pack(pady=2)

        self.move_up_button = ttk.Button(
            list_buttons, text="Move Up", command=self.move_up
        )
        self.move_up_button.pack(pady=2)

        self.move_down_button = ttk.Button(
            list_buttons, text="Move Down", command=self.move_down
        )
        self.move_down_button.pack(pady=2)

        # Control buttons and loop option
        control_frame = ttk.Frame(master)
        control_frame.pack(pady=5)

        self.play_button = ttk.Button(control_frame, text="Play", command=self.on_play)
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.on_stop)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.continue_button = ttk.Button(
            control_frame, text="Continue", command=self.on_continue
        )
        self.continue_button.pack(side=tk.LEFT, padx=5)
        self.continue_button["state"] = "disabled"

        self.loop_var = tk.BooleanVar()
        self.loop_checkbox = ttk.Checkbutton(
            control_frame, text="Loop", variable=self.loop_var
        )
        self.loop_checkbox.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = ttk.Label(master, text="Status: Idle")
        self.status_label.pack(pady=5)

        # Start the queue processing
        self.process_queue()

        # Check for saved progress
        self.check_saved_progress()

    def refresh_ports(self):
        ports = [
            f"{port.device} - {port.description}"
            for port in serial.tools.list_ports.comports()
        ]
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.set(ports[0])

    def add_file(self):
        file_paths = filedialog.askopenfilenames(
            filetypes=[("G-code files", "*.gcode *.nc *.ngc")]
        )
        for file_path in file_paths:
            self.file_list.insert(tk.END, file_path)

    def remove_file(self):
        selected_indices = self.file_list.curselection()
        for index in reversed(selected_indices):
            self.file_list.delete(index)

    def move_up(self):
        selected_indices = self.file_list.curselection()
        for index in selected_indices:
            if index > 0:
                text = self.file_list.get(index)
                self.file_list.delete(index)
                self.file_list.insert(index - 1, text)
                self.file_list.selection_set(index - 1)

    def move_down(self):
        selected_indices = self.file_list.curselection()
        for index in reversed(selected_indices):
            if index < self.file_list.size() - 1:
                text = self.file_list.get(index)
                self.file_list.delete(index)
                self.file_list.insert(index + 1, text)
                self.file_list.selection_set(index + 1)

    def on_play(self):
        if not self.ser:
            port = self.port_combo.get().split(" - ")[0]
            try:
                self.ser = serial.Serial(port, int(os.getenv("BAUD_RATE")))
                self.queue.put(("status", f"Connected to {port}"))
            except serial.SerialException as e:
                self.queue.put(("status", f"Error: {str(e)}"))
                return

        files = self.file_list.get(0, tk.END)
        if not files:
            self.queue.put(("status", "No files to process"))
            return

        self.running = True
        self.stop_requested = False
        self.current_file_index = 0
        self.gcode_thread = threading.Thread(target=self.process_files, args=(files,))
        self.gcode_thread.start()
        self.play_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.continue_button["state"] = "disabled"

    def on_stop(self):
        self.stop_requested = True
        self.queue.put(
            ("status", "Stop requested. Waiting for current file to finish...")
        )

    def on_continue(self):
        if not self.ser:
            port = self.port_combo.get().split(" - ")[0]
            try:
                self.ser = serial.Serial(port, int(os.getenv("BAUD_RATE")))
                self.queue.put(("status", f"Connected to {port}"))
            except serial.SerialException as e:
                self.queue.put(("status", f"Error: {str(e)}"))
                return

        files = self.file_list.get(0, tk.END)
        if not files:
            self.queue.put(("status", "No files to process"))
            return

        self.running = True
        self.stop_requested = False
        self.gcode_thread = threading.Thread(target=self.process_files, args=(files,))
        self.gcode_thread.start()
        self.play_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.continue_button["state"] = "disabled"

    def process_files(self, files):
        while self.running and not self.stop_requested:
            for i in range(self.current_file_index, len(files)):
                self.current_file_index = i
                if self.stop_requested:
                    self.save_progress()
                    break
                file = files[i]
                self.queue.put(("status", f"Processing: {file}"))
                stream_gcode(self.ser, file)
            if not self.loop_var.get():
                break
            self.current_file_index = 0
        self.queue.put(("finished", None))

    def update_status(self, message):
        self.status_label["text"] = message

    def on_finished(self):
        self.play_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.status_label["text"] = "Status: Idle"
        self.running = False
        self.stop_requested = False
        self.check_saved_progress()

    def process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                if message[0] == "status":
                    self.update_status(message[1])
                elif message[0] == "finished":
                    self.on_finished()
                self.queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_queue)

    def save_progress(self):
        progress = {
            "files": list(self.file_list.get(0, tk.END)),
            "current_index": self.current_file_index,
        }
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)

    def load_progress(self):
        with open(PROGRESS_FILE, "r") as f:
            progress = json.load(f)
        self.file_list.delete(0, tk.END)
        for file in progress["files"]:
            self.file_list.insert(tk.END, file)
        self.current_file_index = progress["current_index"]

    def check_saved_progress(self):
        if os.path.exists(PROGRESS_FILE):
            self.continue_button["state"] = "normal"
            self.load_progress()
        else:
            self.continue_button["state"] = "disabled"


if __name__ == "__main__":
    root = tk.Tk()
    app = GCodeRunner(root)
    root.mainloop()
