import os, sys, serial, select
import serial.tools.list_ports
from utils.machine import stream_gcode
from dotenv import load_dotenv


def list_serial_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
        sys.exit(1)
    print("Available serial ports:")
    for i, port in enumerate(ports):
        print(f"{i + 1}: {port.device} - {port.description}")
    return ports


def select_serial_port(ports):
    while True:
        try:
            choice = int(input("Select a port number: "))
            if 1 <= choice <= len(ports):
                return ports[choice - 1].device
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def process_file(file_path, ser):
    print(f"Processing file: {file_path}")
    stream_gcode(ser, file_path)
    print(f"Finished processing: {file_path}")


def is_quit_pressed():
    if select.select([sys.stdin], [], [], 0.0)[0]:
        key = sys.stdin.read(1)
        return key.lower() == "q"
    return False


def main():
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python run.py <file_or_folder_path> [loop]")
        sys.exit(1)

    path = sys.argv[1]
    loop = len(sys.argv) > 2 and sys.argv[2].lower() == "loop"

    if not os.path.exists(path):
        print(f"Error: Path '{path}' does not exist.")
        sys.exit(1)

    ports = list_serial_ports()
    selected_port = select_serial_port(ports)

    try:
        ser = serial.Serial(selected_port, int(os.getenv("BAUD_RATE")))

        # stream_gcode(ser, "./gcode/homing.gcode", False)
        stream_gcode(ser, "./gcode/home.gcode", False)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    if loop:
        print("Loop mode activated. Press 'q' and Enter at any time to quit.")

    while True:
        if os.path.isfile(path) and (
            path.endswith(".gcode") or path.endswith(".ngc") or path.endswith(".nc")
        ):
            process_file(path, ser)
        elif os.path.isdir(path):
            for file in os.listdir(path):
                if (
                    file.endswith(".gcode")
                    or file.endswith(".ngc")
                    or file.endswith(".nc")
                ):
                    file_path = os.path.join(path, file)
                    process_file(file_path, ser)
                    if is_quit_pressed():
                        print("Quit signal received. Exiting.")
                        ser.close()
                        sys.exit(0)
        else:
            print(f"Error: '{path}' is neither a file nor a directory.")
            ser.close()
            sys.exit(1)

        if not loop:
            break
        else:
            print("All files processed. Restarting loop.")

            if is_quit_pressed():
                print("Quit signal received. Exiting.")
                break

    ser.close()
    print("Program completed.")


if __name__ == "__main__":
    main()
