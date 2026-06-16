# ESP-FC — ESP32 Flight Controller Firmware

[![PlatformIO Build](https://github.com/MahediIslamNadim/esp32/actions/workflows/build.yml/badge.svg)](https://github.com/MahediIslamNadim/esp32/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform: ESP32](https://img.shields.io/badge/Platform-ESP32-blue.svg)](https://www.espressif.com/)

A complete, **buildable** multirotor flight controller firmware for the **ESP32**
(and ESP32-S3/S2/C3), built with PlatformIO and the Arduino-ESP32 framework.

> Based on **[ESP-FC](https://github.com/rtlopez/esp-fc)** by Rafał Łopez (rtlopez).
> Licensed under the MIT License — see [`LICENSE`](LICENSE).

---

## ⚡ Quick start (one command)

New to this? Use the guided setup tool — it auto-installs dependencies, asks a few
questions, builds, detects your ESP32 and flashes it:

```bash
# Linux / macOS
./setup.sh
```
```bat
REM Windows: double-click setup.bat, or
python tools\espfc-setup.py
```

It runs a menu (**Quick Setup** / **Manual Config**), then prompts you to connect
the board and flashes it. See [`tools/README.md`](tools/README.md) for details.

For the manual route, see **Build & Flash** below.

---

## ✨ Features

- **Flight control** — PID controller, configurable rates, multiple flight modes
- **Attitude estimation (AHRS)** — Madgwick, Mahony, Kalman and **EKF** fusion
- **Sensors** — gyro / accelerometer, barometer, magnetometer, GPS, battery voltage & current
- **RC protocols** — CRSF, SBUS, IBUS, PPM
- **ESC protocols** — DShot, OneShot, Multishot, Brushed/PWM (via `EscDriver`)
- **Connectivity** — MSP & CLI, Blackbox logging, telemetry, WiFi / ESP-NOW
- **Dual-core** — separate gyro and PID tasks on FreeRTOS (ESP32)

## 🛠️ Requirements

- An ESP32 board (WROOM / DevKit / `lolin32`), or ESP32-S3 / S2 / C3
- [PlatformIO Core](https://platformio.org/install) (`pip install platformio`)
- Hardware to fly — see [`esp32-connection-guide.md`](esp32-connection-guide.md)

## 🚀 Build & Flash

```bash
# Build firmware
pio run -e esp32

# Build and flash to a connected ESP32 (USB)
pio run -e esp32 -t upload

# Open the serial monitor / CLI (115200 baud)
pio device monitor
```

Available environments: `esp32` (default), `esp32s3`, `esp32s2`, `esp32c3`.
Each push is automatically built for all four targets via GitHub Actions.

> ⚠️ Use **PlatformIO**, not the Arduino IDE — the firmware needs the custom
> partition table (`partitions_4M_nota.csv`) and specific build flags that the
> Arduino IDE does not provide.

## 📂 Project layout

```
esp32/
├── platformio.ini            # build targets, flags, partition table
├── partitions_4M_nota.csv    # custom ESP32 partition table (required)
├── src/main.cpp              # entry point (setup/loop, FreeRTOS tasks)
└── lib/                      # firmware libraries (PlatformIO)
    ├── Espfc/src/            # core firmware
    ├── AHRS/src/             # attitude estimation (Madgwick/Mahony/Kalman/EKF)
    ├── EscDriver/src/        # ESC protocols (DShot/PWM/…)
    ├── Gps/src/              # GPS parsing
    ├── betaflight/src/       # Betaflight-compatible blackbox/types
    ├── printf/src/           # lightweight printf
    ├── EspWire/src/          # I2C helper
    └── MultiButton/src/      # button handling
```

Inside `lib/Espfc/src/`:

| Folder | What it contains |
| ------ | ---------------- |
| `Control/` | PID, attitude fusion (incl. EKF wiring), rates |
| `Sensor/`  | gyro, accel, baro, mag, GPS, voltage |
| `Rc/`      | RC protocols (CRSF, SBUS, IBUS, PPM) |
| `Output/`  | motor / ESC mixing & output |
| `Device/`  | chip drivers (gyro / baro / mag) |
| `Connect/` | MSP / CLI |
| `Blackbox/`, `Telemetry/`, `Wireless/` | logging, telemetry, WiFi / ESP-NOW |
| `Target/`  | per-board pin definitions (`TargetESP32.h`, …) |
| `Utils/`   | math, filters, helpers |

Total: ~279 files, ~36,000 lines.

## 🔌 Wiring & pin mapping

Full wiring instructions are in **[`esp32-connection-guide.md`](esp32-connection-guide.md)**.

ESP32 default pins live in `lib/Espfc/src/Target/TargetESP32.h` and
`TargetEsp32Common.h`. Pins can also be remapped at runtime via the CLI
`resource` command — no re-flash needed.

Key defaults (ESP32):

| Function | GPIO | Function | GPIO |
| -------- | ---- | -------- | ---- |
| Motors M0–M3 | 27, 25, 4, 12 | Receiver (UART2 RX) | 16 |
| SPI (SCK/MOSI/MISO) | 18 / 23 / 19 | Gyro CS / Baro CS | 5 / 13 |
| I2C (SDA/SCL) | 21 / 22 | Battery voltage / current | 36 / 39 |
| Buzzer / LED / Button | 26 / 2 / 0 | | |

## ⚙️ Setup & flying

📖 Full walkthrough: **[SETUP.md](SETUP.md)** — complete step-by-step setup guide,
from installing tools to first flight.
🔧 Per-device settings: **[HARDWARE.md](HARDWARE.md)** — exact wiring + CLI for
each supported gyro, ESC protocol and receiver.

This firmware is flash-ready, but a flying drone still needs hardware assembly
and configuration:

1. Flash the firmware (`pio run -e esp32 -t upload`)
2. Wire the FC per the connection guide (IMU, receiver, ESCs, power)
3. Configure via CLI / Configurator: gyro calibration, receiver bind,
   motor direction, modes and failsafe
4. **Always test with props off first.**

Follow the step-by-step **[pre-flight checklist](pre-flight-checklist.md)** before
your first flight.

## 📜 License & credits

MIT — see [`LICENSE`](LICENSE).
Original firmware: **[ESP-FC](https://github.com/rtlopez/esp-fc)** by Rafał Łopez.
