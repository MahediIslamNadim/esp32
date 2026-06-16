# ESP-FC Setup Tool

`espfc-setup.py` is a guided installer & flasher. It auto-installs dependencies,
asks a few questions, builds the firmware, detects your ESP32 and flashes it —
then pushes your gyro/ESC config to the board automatically.

## Run it

**Linux / macOS**
```bash
./setup.sh
# or directly:
python3 tools/espfc-setup.py
```

**Windows** — double-click `setup.bat`, or:
```bat
python tools\espfc-setup.py
```

**One-liner (no clone needed, Linux/macOS):**
```bash
curl -fsSL https://raw.githubusercontent.com/MahediIslamNadim/esp32/main/setup.sh | bash
```

## What it does

1. **Checks dependencies** — Python, pip; installs **PlatformIO** and **pyserial**
   if missing.
2. **Menu** — `Quick Setup` or `Manual Config`.
3. **Quick Setup** — pick board, gyro, ESC and receiver.
4. **Builds** the firmware (`pio run -e <board>`).
5. **Prompts you to connect the ESP32**, then auto-detects the serial port.
6. **Flashes** the board.
7. **Applies your config** over the CLI (`set gyro_dev=…`, `set output_motor_protocol=…`, `save`).

## Options

```
python3 tools/espfc-setup.py --check    # verify dependencies only, then exit
```

## Notes

- **Do not use `sudo`.** On Debian/Kali/Ubuntu the system Python is
  "externally managed" (PEP 668), so the tool automatically creates an isolated
  virtualenv (`.espfc-venv`) and installs PlatformIO + pyserial there, then
  relaunches itself inside it. (If venv creation fails, run once:
  `sudo apt install python3-venv`.)
- **Receiver protocol** (CRSF/SBUS/IBUS/PPM) is a serial-port function and is set
  in the ESP-FC Configurator — the tool prints exact instructions for your choice.
- **USB drivers** (CP210x / CH340) may need a manual install on Windows; if no
  port is detected, install the driver and re-run.
- See [`../HARDWARE.md`](../HARDWARE.md) for every per-device setting and
  [`../pre-flight-checklist.md`](../pre-flight-checklist.md) before flying.
