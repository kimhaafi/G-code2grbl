import time
import serial
from threading import Event


def stream_gcode(ser, gcode_path, max_commands=8):
    def remove_comment(string):
        if ";" in string:
            return string[: string.index(";")]
        return string

    def remove_eol_chars(string):
        return string.strip()

    def send_wake_up(ser):
        ser.write(b"\r\n\r\n")
        time.sleep(2)  # Wait for GRBL to initialize
        ser.reset_input_buffer()  # Flush startup text in serial input

    def get_buffer_status(ser):
        ser.reset_input_buffer()
        ser.write(b"?")
        grbl_out = ser.readline().strip().decode("utf-8")
        if grbl_out.startswith("<"):
            parts = grbl_out.split("|")
            for part in parts:
                if part.startswith("Bf:"):
                    buffer_info = part.split(":")[1].split(",")
                    available_buffer_slots = int(buffer_info[1])
                    return available_buffer_slots > 0
        return False

    def wait_for_buffer(ser):
        while not get_buffer_status(ser):
            Event().wait(0.1)  # Wait a bit before checking again

    def send_command(ser, command):
        ser.write(command.encode() + b"\n")
        while True:
            grbl_out = ser.readline().strip().decode("utf-8")
            if grbl_out == "ok":
                return
            if grbl_out.startswith("error"):
                print(f"Error: {grbl_out}")
                return

    with open(gcode_path, "r") as file:
        send_wake_up(ser)
        command_queue = []

        for line in file:
            cleaned_line = remove_eol_chars(remove_comment(line))
            if cleaned_line:
                while len(command_queue) >= max_commands:
                    wait_for_buffer(ser)
                    send_command(ser, command_queue.pop(0))

                if cleaned_line.startswith("G") or "$H" in cleaned_line:
                    command_queue.append(cleaned_line)
                else:
                    send_command(ser, cleaned_line)

        # Send any remaining commands in the queue
        while command_queue:
            wait_for_buffer(ser)
            send_command(ser, command_queue.pop(0))

        print("End of gcode")
