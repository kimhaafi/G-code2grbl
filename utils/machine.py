import time, os
from threading import Event

BAUD_RATE = os.getenv("BAUD_RATE")
MAX_COMMANDS = os.getenv("MAX_COMMANDS")


def stream_gcode(ser, gcode_path):
    def remove_comment(string):
        if string.find(";") == -1:
            return string
        else:
            return string[: string.index(";")]

    def remove_eol_chars(string):
        return string.strip()

    def send_wake_up(ser):
        ser.write(str.encode("\r\n\r\n"))
        time.sleep(2)  # Wait for Printrbot to initialize
        ser.flushInput()  # Flush startup text in serial input

    def get_buffer_status(ser):
        ser.reset_input_buffer()
        command = str.encode("?" + "\n")
        ser.write(command)
        grbl_out = ser.readline().strip().decode("utf-8")
        if grbl_out.startswith("<") and grbl_out.endswith(">"):
            status_params = grbl_out[1:-1].split("|")
            for param in status_params:
                if param.lower() == "idle":
                    return True
        return False

    def wait_for_buffer(ser):
        while True:
            buffer_ready = get_buffer_status(ser)

            if buffer_ready:
                break
            Event().wait(0.01)  # Wait a bit before checking again

    with open(gcode_path, "r") as file:
        send_wake_up(ser)
        count_ok = 0
        for line in file:
            cleaned_line = remove_eol_chars(remove_comment(line))
            if cleaned_line:  # checks if string is empty
                print("Sending gcode:" + str(cleaned_line))
                # wait_for_buffer(ser)
                command = str.encode(line + "\n")
                ser.write(command)  # Send g-code

                grbl_out = ser.readline()

                grbl_response = grbl_out.strip().decode("utf-8")
                if line.startswith("G") or "$H" in line:
                    while grbl_response != "ok":
                        ser.write(command)  # Send g-code
                        grbl_out = ser.readline()
                        grbl_response = grbl_out.strip().decode("utf-8")

        print("End of gcode")
