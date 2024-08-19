import time
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
                    available_buffer_slots = int(buffer_info[0])
                    print("Available buffer slots:", available_buffer_slots)
                    return available_buffer_slots > 3
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

        for line in file:
            cleaned_line = remove_eol_chars(remove_comment(line))
            if cleaned_line:
                print("sending:", cleaned_line)
                send_command(ser, cleaned_line)
                wait_for_buffer(ser)

        print("End of gcode")
