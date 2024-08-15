import os
import sys
import serial
import serial.tools.list_ports
from utils.machine import stream_gcode
from dotenv import load_dotenv
import json
import signal
import time
import multiprocessing

load_dotenv()

PROGRESS_FILE = "gcode_progress.json"


class GCodeRunner:
    def __init__(self):
        self.running = multiprocessing.Value("b", False)
        self.stop_requested = multiprocessing.Value("b", False)
        self.current_file_index = multiprocessing.Value("i", 0)
        self.files = multiprocessing.Manager().list()
        self.gcode_process = None
        self.current_file = multiprocessing.Manager().Value(str, "")
        self.port = None
        self.baud_rate = int(os.getenv("BAUD_RATE"))

    def load_progress(self):
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "r") as f:
                progress = json.load(f)
            self.files.extend(progress.get("files", []))
            self.current_file_index.value = progress.get("current_index", 0)
        else:
            print("No progress file found. Please create a gcode_progress.json file.")
            sys.exit(1)

    def save_progress(self):
        progress = {
            "files": list(self.files),
            "current_index": self.current_file_index.value,
        }
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)

    def get_port(self):
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial ports found.")
            sys.exit(1)
        return ports[int(os.getenv("PORT")) - 1].device

    def gcode_processing(
        self,
        port,
        baud_rate,
        files,
        current_file_index,
        running,
        stop_requested,
        current_file,
    ):
        ser = None
        try:
            ser = serial.Serial(port, baud_rate)
            print(f"Connected to {port}")

            while running.value and not stop_requested.value:
                if current_file_index.value < len(files):
                    file = files[current_file_index.value]
                    current_file.value = file
                    print(f"Processing: {file}")
                    try:
                        stream_gcode(ser, file, int(os.getenv("MAX_COMMANDS")))
                        print(f"Finished processing: {file}")
                        with current_file_index.get_lock():
                            current_file_index.value += 1
                        self.save_progress()
                    except serial.SerialException as e:
                        print(f"Serial communication error: {e}")
                        break
                else:
                    with current_file_index.get_lock():
                        current_file_index.value = 0  # Reset for next loop
                time.sleep(0.1)  # Small delay to prevent busy-waiting

        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
        finally:
            running.value = False
            if ser:
                ser.close()
            print("G-code processing stopped.")

    def start_processing(self):
        self.running.value = True
        self.port = self.get_port()
        self.gcode_process = multiprocessing.Process(
            target=self.gcode_processing,
            args=(
                self.port,
                self.baud_rate,
                self.files,
                self.current_file_index,
                self.running,
                self.stop_requested,
                self.current_file,
            ),
        )
        self.gcode_process.start()

    def stop_processing(self):
        self.stop_requested.value = True
        if self.gcode_process:
            self.gcode_process.join()
        self.save_progress()

    def signal_handler(self, signum, frame):
        print("SIGTERM received. Stopping after current file completion...")
        self.stop_processing()


def main():
    runner = GCodeRunner()
    runner.load_progress()

    if not runner.files:
        print("No files to process.")
        return

    # Set up signal handler for graceful stopping
    signal.signal(signal.SIGTERM, runner.signal_handler)

    try:
        runner.start_processing()
        while runner.running.value and not runner.stop_requested.value:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Stopping...")
        runner.stop_processing()
    except Exception as e:
        print(f"An error occurred: {e}")

    if runner.stop_requested.value:
        print(f"Stopped. Last file processed: {runner.current_file.value}")


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Necessary for Windows
    main()
