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

## Requirements

- Python 3.x
- pyserial
- python-dotenv
- PyQt6 (for GUI version)

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

### Command-line Version

To run the command-line version:

```
python terminal.py <file_or_folder_path> [loop]
```

- `<file_or_folder_path>`: Path to a single G-code file or a folder containing G-code files
- `[loop]`: Optional parameter to enable looping mode

### Standalone G-code Player

To run the standalone G-code player:

```
python play.py
```

This version uses a `gcode_progress.json` file to track progress and allow for resumable operations.

## Configuration

Update the `.env` file with your specific settings:

- `BAUD_RATE`: Set the baud rate for serial communication
- `MAX_COMMANDS`: Set the maximum number of commands to send at once
- `MAX_BUFFER_SIZE`: Set the maximum buffer size for the GRBL controller

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your chosen license here]

## Acknowledgements

- GRBL firmware developers
- PySerial library developers
- All contributors to this project
