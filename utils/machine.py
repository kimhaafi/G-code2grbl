import time, os
from threading import Event

BAUD_RATE = os.getenv("BAUD_RATE")
MAX_COMMANDS = os.getenv("MAX_COMMANDS")


def stream_gcode(ser, gcode_path, wait_for_completion=True):
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
                if param.startswith("Bf:"):
                    planner_buffer, rx_buffer = map(int, param[3:].split(","))
                    return planner_buffer, rx_buffer
        return None, None

    def wait_for_buffer(ser):
        MAX_BUFFER_SIZE = 15  # Update this to your GRBL's planner buffer size
        HALF_BUFFER_SIZE = MAX_BUFFER_SIZE // 2
        while True:
            planner_buffer, _ = get_buffer_status(ser)
            print(planner_buffer)
            if planner_buffer is not None and planner_buffer >= HALF_BUFFER_SIZE:
                break
            Event().wait(0.1)  # Wait a bit before checking again

    def wait_for_movement_completion(ser, cleaned_line):
        start_time = time.time()
        while (time.time() - start_time) < 20:
            ser.reset_input_buffer()
            command = str.encode("?" + "\n")
            ser.write(command)
            grbl_out = ser.readline().strip().decode("utf-8")
            if grbl_out.startswith("MPos") or grbl_out.startswith("WPos"):
                return

    with open(gcode_path, "r") as file:
        send_wake_up(ser)
        count_ok = 0
        for line in file:
            cleaned_line = remove_eol_chars(remove_comment(line))
            if cleaned_line:  # checks if string is empty
                if count_ok % 8 == 0:
                    Event().wait(0.5)
                print("Sending gcode:" + str(cleaned_line))
                wait_for_buffer(ser)
                command = str.encode(line + "\n")
                ser.write(command)  # Send g-code
                if wait_for_completion:
                    wait_for_movement_completion(ser, cleaned_line)

                grbl_out = ser.readline()

                grbl_response = grbl_out.strip().decode("utf-8")
                if "G1" in line or "G0" in line or "$H" in line:
                    while grbl_response != "ok":
                        ser.write(command)  # Send g-code
                        grbl_out = ser.readline()
                        grbl_response = grbl_out.strip().decode("utf-8")

                count_ok += 1

        print("End of gcode")
