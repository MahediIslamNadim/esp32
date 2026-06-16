# ESP-FC Setup Tool — Documentation

`espfc-setup.py` is a guided installer & flasher. With one command it installs
everything, lets you configure the firmware, then builds and flashes your ESP32.

- [Run it](#run-it)
- [What it does](#what-it-does)
- [Main menu](#main-menu)
- [Quick Setup](#quick-setup)
- [Manual Config](#manual-config)
- [Pins](#pins)
- [Settings](#settings)
- [Flashing](#flashing)
- [Command-line options](#command-line-options)
- [How configuration is applied](#how-configuration-is-applied)
- [Dependencies & the venv](#dependencies--the-venv)
- [Troubleshooting](#troubleshooting)

---

## Run it

**Linux / macOS**
```bash
git pull          # if you already cloned
./setup.sh
```

**Windows** — double-click `setup.bat`, or:
```bat
python tools\espfc-setup.py
```

**One-liner (no clone needed, Linux/macOS):**
```bash
curl -fsSL https://raw.githubusercontent.com/MahediIslamNadim/esp32/main/setup.sh | bash
```

> Do **not** run with `sudo` — see [Dependencies & the venv](#dependencies--the-venv).

## What it does

1. **Checks dependencies** — Python, pip; installs **PlatformIO** and **pyserial**
   (in an isolated venv if the system Python is externally managed).
2. Shows the **main menu** — Quick Setup or Manual Config.
3. **Builds** the firmware for your board.
4. **Prompts you to connect the ESP32**, auto-detects the serial port.
5. **Flashes** the board.
6. **Applies your settings** over the CLI and saves them.

## Main menu

```
Main menu
  1) Quick Setup   (recommended)
  2) Manual Config
  3) Exit
```

| Option | Use it when |
| ------ | ----------- |
| **Quick Setup** | You want to get flying fast — answer 4 questions and go. |
| **Manual Config** | You want full control over pins and every firmware setting. |
| **Exit** | Quit (Ctrl-C also works anywhere). |

## Quick Setup

Answer four questions, each with a sensible default:

| Question | Options | CLI setting applied |
| -------- | ------- | ------------------- |
| **Board** | `esp32` (default), `esp32s3`, `esp32s2`, `esp32c3` | build target |
| **Gyro / IMU** | `AUTO`, `MPU6500`, `MPU6050`, `MPU9250`, `ICM20602`, `MPU6000`, `LSM6DSO`, `BMI160` | `gyro_dev`, `accel_dev` |
| **ESC protocol** | `DSHOT600`, `DSHOT300`, `DSHOT150`, `ONESHOT125`, `MULTISHOT`, `PWM`, `BRUSHED` | `output_motor_protocol` |
| **Receiver** | `CRSF`, `SBUS`, `IBUS`, `PPM` | wiring/Configurator hint (serial-port function) |

Then it builds, asks you to connect the board, flashes, and applies the gyro/ESC
settings automatically. The receiver choice prints exact wiring + Configurator
instructions (the receiver protocol is a serial-port function, not a `set` key).

## Manual Config

Full customization. Pick a board, then a working menu:

```
Manual menu  (board=esp32, pending=0)
  1) Edit pins
  2) Edit a setting (gyro, ESC, rates, filters, features, …)
  3) Show pending changes
  4) Clear pending changes
  5) Build, flash & apply
  0) Back to main menu
```

You stage as many changes as you like ("pending"), then option **5** builds,
flashes and applies them all in one pass.

### Pins

`Edit pins` groups every pin by function. Each prompt shows the firmware
**default GPIO** for the esp32 target; press Enter to keep it.

```
Edit pins (values are GPIO numbers; -1 = unassigned)
  1) Motors / outputs    pin_output_0..7
  2) Receiver input      pin_input_rx, pin_input_adc_0/1
  3) UART serial         pin_serial_0/1/2_tx/rx
  4) SPI bus             pin_spi_0_sck/mosi/miso, pin_spi_cs_0/1/2
  5) I2C bus             pin_i2c_scl/sda
  6) Misc                pin_button, pin_buzzer(_invert), pin_led(_invert/_type)
```

Example:
```
  pin_output_0 [default: 27] = 26     # remap motor 0 to GPIO 26
  pin_output_1 [default: 25] =        # keep default
```

> Defaults are shown for **esp32**. On s3/s2/c3 the tool says so and shows no
> default (those boards differ) — enter the GPIO you want explicitly.

### Settings

`Edit a setting` lets you set **any** of the firmware's **343** CLI settings.
Type part of a name to search:

```
setting name> gyro_lpf
  3 matches:
    gyro_lpf_type
    gyro_lpf_freq
    gyro_lpf2_freq
```
Type the full name to set it:
```
setting name> gyro_lpf_freq
gyro_lpf_freq = 120
✓ set gyro_lpf_freq=120 (pending)
```

All valid names live in [`espfc-settings.txt`](espfc-settings.txt) (generated
from the firmware source). See [`../HARDWARE.md`](../HARDWARE.md) for the meaning
and accepted values of the common ones.

## Flashing

After building, the tool prints:

```
>> Connect your ESP32 to USB now, then press Enter.
```

It auto-detects the serial port (CP210x/CH340/USB-UART). If none is found,
PlatformIO picks one automatically during upload. Then it flashes and reports
success.

## Command-line options

```
python3 tools/espfc-setup.py            # interactive
python3 tools/espfc-setup.py --check    # verify dependencies only, then exit
./setup.sh --check                      # same, via the bootstrapper
```

## How configuration is applied

After flashing, the tool opens the serial port at 115200 and sends your settings
as CLI commands, then saves:

```
set gyro_dev=MPU6500
set output_motor_protocol=DSHOT600
set pin_output_0=26
save
```

If pyserial is unavailable or no port is found, it prints these commands so you
can paste them into `pio device monitor` yourself.

## Dependencies & the venv

On Debian/Kali/Ubuntu the system Python is "externally managed" (PEP 668), so a
plain `pip install` is blocked. The tool handles this automatically:

1. It creates an isolated virtualenv at **`.espfc-venv`**.
2. Installs PlatformIO + pyserial inside it.
3. Relaunches itself using that venv's Python.

This needs **no `sudo`** and never touches the system Python. If venv creation
fails, install the module once:
```bash
sudo apt install python3-venv
```
then re-run `./setup.sh` (without sudo).

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `externally-managed-environment` | Don't use sudo; the tool makes a venv automatically. |
| `Could not create a virtualenv` | `sudo apt install python3-venv`, then re-run. |
| Upload fails | Hold the **BOOT** button while flashing; unplug devices on GPIO 0/2/12. |
| No port detected | Install the USB driver (CP210x / CH340); PlatformIO can still auto-pick. |
| No gyro after flash | Check wiring/bus; set `gyro_dev` explicitly in Manual Config. |
| Settings didn't apply | pyserial/port issue — paste the printed `set …` lines into `pio device monitor`. |

---

See also: [`../SETUP.md`](../SETUP.md) ·
[`../HARDWARE.md`](../HARDWARE.md) ·
[`../pre-flight-checklist.md`](../pre-flight-checklist.md)
