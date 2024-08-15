# G-code2grbl

G-code2grbl is a Python-based tool for parsing G-code and sending commands to machines through Arduino using the GRBL firmware. This project provides a quick and easy way to control CNC machines, 3D printers, and other GRBL-compatible devices.

## Features

- Parse and stream G-code files to GRBL-controlled machines
- Support for multiple G-code file formats (.gcode, .ngc, .nc)
- GUI interface for easy file management and machine control
- Command-line interface for advanced users and automation
- Automatic port detection and selection
- Progress tracking and resumable operations
- Looping capability for repeated tasks
- Bézier curve to G-code conversion tool

## Requirements

- Python 3.x
- pyserial
- python-dotenv
- tkinter (for GUI version)

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/G-code2grbl.git
   cd G-code2grbl
   ```

2. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

3. Copy the `.env.example` file to `.env` and update the values:
   ```
   cp .env.example .env
   ```

## Usage

### GUI Version

Run the GUI application:

```
python gui.py
```

The GUI allows you to:

- Select the serial port
- Add, remove, and reorder G-code files
- Start, stop, and continue G-code streaming
- Enable looping for repeated operations

### Terminal Version

To run the command-line version:

```
python terminal.py
```

This interactive terminal allows you to:

- Add and remove G-code files
- List current G-code files
- Start and stop processing
- Manage serial port connection

### Standalone G-code Player

To run the standalone G-code player:

```
python play.py
```

This version uses a `gcode_progress.json` file to track progress and allow for resumable operations.

### Bézier Curve to G-code Converter

To run the Bézier curve to G-code conversion tool:

```
python create_gcode_tool.py
```

This GUI tool allows you to:

- Draw Bézier curves
- Convert curves to G-code
- Adjust feedrates and interpolation
- Save generated G-code

## Configuration

Update the `.env` file with your specific settings:

- `BAUD_RATE`: Set the baud rate for serial communication
- `MAX_COMMANDS`: Set the maximum number of commands to send at once
- `MAX_BUFFER_SIZE`: Set the maximum buffer size for the GRBL controller
- `PORT`: Set the port number for serial communication

## Utility Scripts

- `list_ports.py`: Lists available serial ports
- `utils/machine.py`: Contains utility functions for G-code streaming

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open-source and available under the MIT License.

## Acknowledgements

- GRBL firmware developers
- PySerial library developers
- All contributors to this project
