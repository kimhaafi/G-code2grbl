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


class GCodeTerminal:
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
            print("No progress file found. Starting fresh.")

    def save_progress(self):
        progress = {"files": self.files, "current_index": self.current_file_index}
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)

    def list_serial_ports(self):
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial ports found.")
            sys.exit(1)
        print("Available serial ports:")
        for i, port in enumerate(ports):
            print(f"{i + 1}: {port.device} - {port.description}")
        return ports

    def select_serial_port(self, ports):
        while True:
            try:
                choice = int(input("Select a port number: "))
                if 1 <= choice <= len(ports):
                    return ports[choice - 1].device
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

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
                    stream_gcode(self.ser, file, int(os.getenv("MAX_COMMANDS")))
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

    def add_file(self):
        file_path = input("Enter the path to the G-code file: ")
        if os.path.exists(file_path) and file_path.lower().endswith(
            (".gcode", ".ngc", ".nc")
        ):
            self.files.append(file_path)
            print(f"Added file: {file_path}")
        else:
            print("Invalid file path or unsupported file type.")

    def remove_file(self):
        if not self.files:
            print("No files in the list.")
            return
        print("Current files:")
        for i, file in enumerate(self.files):
            print(f"{i + 1}: {file}")
        try:
            index = int(input("Enter the number of the file to remove: ")) - 1
            if 0 <= index < len(self.files):
                removed_file = self.files.pop(index)
                print(f"Removed file: {removed_file}")
            else:
                print("Invalid file number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    def list_files(self):
        if not self.files:
            print("No files in the list.")
        else:
            print("Current files:")
            for i, file in enumerate(self.files):
                print(f"{i + 1}: {file}")

    def main_loop(self):
        while True:
            print("\nG-code Terminal Menu:")
            print("1. Add G-code file")
            print("2. Remove G-code file")
            print("3. List G-code files")
            print("4. Start processing")
            print("5. Stop processing")
            print("6. Exit")

            choice = input("Enter your choice (1-6): ")

            if choice == "1":
                self.add_file()
            elif choice == "2":
                self.remove_file()
            elif choice == "3":
                self.list_files()
            elif choice == "4":
                if not self.running:
                    self.start_processing()
                else:
                    print("Processing is already running.")
            elif choice == "5":
                if self.running:
                    self.stop_processing()
                else:
                    print("Processing is not running.")
            elif choice == "6":
                if self.running:
                    self.stop_processing()
                if self.ser:
                    self.ser.close()
                print("Exiting G-code Terminal.")
                break
            else:
                print("Invalid choice. Please try again.")


def main():
    terminal = GCodeTerminal()
    terminal.load_progress()

    ports = terminal.list_serial_ports()
    terminal.port = terminal.select_serial_port(ports)

    if not terminal.connect():
        print("Failed to connect to the serial port. Exiting.")
        return

    try:
        terminal.main_loop()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Stopping...")
        if terminal.running:
            terminal.stop_processing()
    finally:
        if terminal.ser:
            terminal.ser.close()


if __name__ == "__main__":
    main()
