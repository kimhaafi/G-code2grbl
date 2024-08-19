import os
import sys
import serial
import serial.tools.list_ports
from utils.machine import stream_gcode
from dotenv import load_dotenv
import tkinter as tk
from tkinter import ttk, filedialog
import multiprocessing
import queue
import json
import time

load_dotenv()

PROGRESS_FILE = "gcode_progress.json"


class GCodeProcessor(multiprocessing.Process):
    def __init__(
        self,
        port,
        baud_rate,
        file_queue,
        status_queue,
        stop_event,
        loop_flag,
        current_file_index,
    ):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.file_queue = file_queue
        self.status_queue = status_queue
        self.stop_event = stop_event
        self.loop_flag = loop_flag
        self.current_file_index = current_file_index

    def run(self):
        ser = None
        try:
            ser = serial.Serial(self.port, self.baud_rate)
            self.status_queue.put(("status", f"Connected to {self.port}"))

            while not self.stop_event.is_set():
                try:
                    file, index = self.file_queue.get(timeout=1)
                    self.current_file_index.value = index
                    self.status_queue.put(("status", f"Processing: {file}"))
                    self.status_queue.put(("save_progress", index))

                    # Stream the G-code file and frequently update progress
                    with open(file, "r") as f:
                        total_lines = sum(1 for _ in f)

                    with open(file, "r") as f:
                        for i, line in enumerate(f):
                            if self.stop_event.is_set():
                                self.status_queue.put(
                                    ("save_progress", index, i / total_lines)
                                )
                                break
                            stream_gcode(ser, line)
                            if i % 100 == 0:  # Update progress every 100 lines
                                self.status_queue.put(
                                    ("update_progress", index, i / total_lines)
                                )

                    if not self.stop_event.is_set():
                        self.file_queue.task_done()
                except queue.Empty:
                    if self.loop_flag.value and not self.file_queue.empty():
                        continue
                    elif self.file_queue.empty():
                        break
        except serial.SerialException as e:
            self.status_queue.put(("status", f"Error: {str(e)}"))
        finally:
            if ser:
                ser.close()
            self.status_queue.put(("finished", None))


class GCodeRunner:
    def __init__(self, master):
        self.master = master
        master.title("G-code Runner")
        master.geometry("500x400")

        self.file_queue = multiprocessing.JoinableQueue()
        self.status_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        self.loop_flag = multiprocessing.Value("b", False)
        self.processor = None
        self.current_file_index = multiprocessing.Value("i", 0)

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
        self.stop_button["state"] = "disabled"

        self.continue_button = ttk.Button(
            control_frame, text="Continue", command=self.on_continue
        )
        self.continue_button.pack(side=tk.LEFT, padx=5)
        self.continue_button["state"] = "disabled"

        self.loop_var = tk.BooleanVar()
        self.loop_checkbox = ttk.Checkbutton(
            control_frame,
            text="Loop",
            variable=self.loop_var,
            command=self.update_loop_flag,
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
            self.port_combo.set(ports[int(os.getenv("PORT")) - 1])

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
        port = self.port_combo.get().split(" - ")[0]
        files = self.file_list.get(0, tk.END)
        if not files:
            self.status_label["text"] = "Status: No files to process"
            return

        # Clear the queue before adding new files
        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
            except queue.Empty:
                break

        start_index = self.current_file_index.value
        start_progress = self.get_file_progress(start_index)

        # Add all files to the queue, starting from the current index
        for i in range(len(files)):
            adjusted_index = (start_index + i) % len(files)
            self.file_queue.put((files[adjusted_index], adjusted_index))

        self.stop_event.clear()
        self.processor = GCodeProcessor(
            port,
            int(os.getenv("BAUD_RATE")),
            self.file_queue,
            self.status_queue,
            self.stop_event,
            self.loop_flag,
            self.current_file_index,
        )
        self.processor.start()

        self.play_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.continue_button["state"] = "disabled"

    def on_stop(self):
        if self.processor:
            self.stop_event.set()
            self.status_label["text"] = (
                "Status: Stop requested. Waiting for current file to finish..."
            )

    def on_continue(self):
        self.load_progress()
        self.on_play()

    def update_loop_flag(self):
        self.loop_flag.value = self.loop_var.get()

    def update_status(self, message):
        self.status_label["text"] = message

    def on_finished(self):
        self.play_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.status_label["text"] = "Status: Idle"
        self.current_file_index.value = 0
        self.save_progress(0)
        if self.processor:
            self.processor.join()
            self.processor = None

    def process_queue(self):
        try:
            while True:
                try:
                    message = self.status_queue.get_nowait()
                    if message[0] == "status":
                        self.update_status(message[1])
                    elif message[0] == "finished":
                        self.on_finished()
                    elif message[0] == "save_progress":
                        if len(message) == 3:
                            self.save_progress(message[1], message[2])
                        else:
                            self.save_progress(message[1])
                    elif message[0] == "update_progress":
                        self.update_progress(message[1], message[2])
                except queue.Empty:
                    break
        finally:
            self.master.after(100, self.process_queue)

    def save_progress(self, current_index, file_progress=1.0):
        progress = {
            "files": list(self.file_list.get(0, tk.END)),
            "current_index": current_index % len(self.file_list.get(0, tk.END)),
            "file_progress": file_progress,
        }
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)

    def load_progress(self):
        if not os.path.exists(PROGRESS_FILE):
            return 0.0

        with open(PROGRESS_FILE, "r") as f:
            progress = json.load(f)

        saved_files = progress.get("files", [])
        current_files = list(self.file_list.get(0, tk.END))

        # If the saved file list is different from the current one, we keep the current list
        # but adjust the current_index if necessary
        if saved_files != current_files:
            self.current_file_index.value = min(
                progress.get("current_index", 0), len(current_files) - 1
            )
        else:
            self.current_file_index.value = progress.get("current_index", 0)

        return progress.get("file_progress", 0.0)

    def get_file_progress(self, index):
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "r") as f:
                progress = json.load(f)
            if progress["current_index"] == index:
                return progress.get("file_progress", 0.0)
        return 0.0

    def update_progress(self, file_index, progress):
        total_files = self.file_list.size()
        adjusted_index = file_index % total_files
        self.status_label["text"] = (
            f"Status: Processing file {adjusted_index + 1}/{total_files}, {progress:.1%} complete"
        )
        self.save_progress(adjusted_index, progress)

    def check_saved_progress(self):
        if os.path.exists(PROGRESS_FILE):
            file_progress = self.load_progress()
            if file_progress < 1.0:
                self.continue_button["state"] = "normal"
            else:
                self.continue_button["state"] = "disabled"
        else:
            self.current_file_index.value = 0
            self.continue_button["state"] = "disabled"

    def on_continue(self):
        file_progress = self.load_progress()
        self.on_play()


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Necessary for Windows
    root = tk.Tk()
    app = GCodeRunner(root)
    root.mainloop()
