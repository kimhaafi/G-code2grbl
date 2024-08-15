import os
import sys
import serial
import serial.tools.list_ports
from utils.machine import stream_gcode
from dotenv import load_dotenv
import json
import signal
import time
import threading
import queue

load_dotenv()

PROGRESS_FILE = "gcode_progress.json"


class GCodeRunner:
    def __init__(self):
        self.ser = None
        self.running = False
        self.stop_requested = False
        self.current_file_index = 0
        self.files = []
        self.gcode_thread = None
        self.current_file = None
        self.command_queue = queue.Queue()
        self.port = None
        self.baud_rate = int(os.getenv("BAUD_RATE"))

    def load_progress(self):
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "r") as f:
                progress = json.load(f)
            self.files = progress.get("files", [])
            self.current_file_index = progress.get("current_index", 0)
        else:
            print("No progress file found. Please create a gcode_progress.json file.")
            sys.exit(1)

    def save_progress(self):
        progress = {"files": self.files, "current_index": self.current_file_index}
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)

    def connect_to_port(self):
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial ports found.")
            sys.exit(1)

        self.port = ports[int(os.getenv("PORT")) - 1].device
        self.connect()

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud_rate)
            print(f"Connected to {self.port}")
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            return False
        return True

    def reconnect(self):
        print("Attempting to reconnect...")
        for _ in range(5):  # Try to reconnect 5 times
            if self.connect():
                return True
            time.sleep(2)
        return False

    def gcode_processing_thread(self):
        while self.running and not self.stop_requested:
            if self.current_file_index < len(self.files):
                file = self.files[self.current_file_index]
                self.current_file = file
                print(f"Processing: {file}")
                try:
                    stream_gcode(self.ser, file)
                    print(f"Finished processing: {file}")
                    self.current_file_index += 1
                    self.save_progress()
                except serial.SerialException as e:
                    print(f"Serial communication error: {e}")
                    if not self.reconnect():
                        print("Failed to reconnect. Stopping processing.")
                        break
            else:
                self.current_file_index = 0  # Reset for next loop
            time.sleep(0.1)  # Small delay to prevent busy-waiting

        self.running = False
        print("G-code processing stopped.")

    def start_processing(self):
        self.running = True
        self.gcode_thread = threading.Thread(target=self.gcode_processing_thread)
        self.gcode_thread.start()

    def stop_processing(self):
        self.stop_requested = True
        if self.gcode_thread:
            self.gcode_thread.join()
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

    runner.connect_to_port()

    # Set up signal handler for graceful stopping
    signal.signal(signal.SIGTERM, runner.signal_handler)

    try:
        runner.start_processing()
        while runner.running and not runner.stop_requested:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Stopping...")
        runner.stop_processing()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if runner.ser:
            runner.ser.close()

    if runner.stop_requested:
        print(f"Stopped. Last file processed: {runner.current_file}")


if __name__ == "__main__":
    main()
