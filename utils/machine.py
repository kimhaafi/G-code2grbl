import time, os
from threading import Event


def stream_gcode(ser, gcode_path, max_commands):
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
        print(grbl_out)
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
            Event().wait(0.1)  # Wait a bit before checking again

    with open(gcode_path, "r") as file:
        send_wake_up(ser)
        commands = 0

        for line in file:
            cleaned_line = remove_eol_chars(remove_comment(line))
            if cleaned_line:  # checks if string is empty
                print("Sending gcode:" + str(cleaned_line))

                if line.startswith("G") or "$H" in line:
                    while grbl_response != "ok":
                        ser.write(command)  # Send g-code
                        grbl_out = ser.readline()
                        grbl_response = grbl_out.strip().decode("utf-8")

                else:
                    command = str.encode(line + "\n")
                    ser.write(command)  # Send g-code

                    grbl_out = ser.readline()

                    grbl_response = grbl_out.strip().decode("utf-8")

                commands += 1
                while commands > max_commands:
                    wait_for_buffer(ser)
                    commands = 0

        print("End of gcode")
