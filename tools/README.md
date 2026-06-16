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

## Manual Config — full customization

`Manual Config` lets you change **anything** before flashing:

- **Edit pins** — every pin grouped by function: motors/outputs, receiver input,
  UART (×3), SPI bus + chip-selects, I2C, buzzer/LED/button. Enter GPIO numbers.
- **Edit a setting** — set any of the firmware's **343** CLI settings by name
  (type part of a name to search): gyro, ESC, rates, PID, filters, features,
  battery, GPS, and more.
- **Show / clear** pending changes, then **build → flash → apply** in one go.

All valid setting names live in [`espfc-settings.txt`](espfc-settings.txt)
(generated from the firmware source).

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
