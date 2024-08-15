import serial.tools.list_ports


def list_serial_ports():
    ports = serial.tools.list_ports.comports()

    if not ports:
        print("No serial ports found.")
    else:
        print("Available serial ports:")
        for index, port in enumerate(ports, start=1):
            print(f"{index}. {port.device} - {port.description}")


if __name__ == "__main__":
    list_serial_ports()
