# ESP-FC — ESP32 flight controller firmware

ESP-FC firmware for the **ESP32**, organized as PlatformIO libraries by subsystem.

> ✅ This project is **buildable with PlatformIO**. Each subsystem lives under
> `lib/<Name>/src/`, the entry point is `src/main.cpp`, and `platformio.ini`
> defines the targets, build flags and the custom partition table.
> (Note: it does **not** work in the Arduino IDE — use PlatformIO.)
>
> ```
> pio run -e esp32              # build
> pio run -e esp32 -t upload    # build + flash to ESP32
> pio device monitor            # open serial monitor (115200)
> ```
>
> Verified build: `esp32` env compiles and produces `firmware.bin`
> (Flash ~77%, RAM ~24%). Other envs available: `esp32s3`, `esp32s2`, `esp32c3`.

## Layout

| Folder | What it contains | Files |
| ------ | ---------------- | ----- |
| `src/` | Entry point (`main.cpp`) | 1 |
| `Espfc/` | Core firmware | 164 |
| `Espfc/Control/` | PID, attitude **Fusion** (incl. EKF wiring), Rates | |
| `Espfc/Sensor/` | gyro, accel, baro, mag, GPS, voltage | |
| `Espfc/Rc/` | RC protocols (CRSF, SBUS, IBUS, PPM) | |
| `Espfc/Output/` | motor/ESC mixing & output | |
| `Espfc/Device/` | chip drivers (gyro/baro/mag) | |
| `Espfc/Connect/` | MSP / CLI | |
| `Espfc/Blackbox/`, `Telemetry/`, `Wireless` | logging, telemetry, WiFi/ESP-NOW | |
| `Espfc/Target/` | per-board pin definitions (`TargetESP32.h`, ...) | |
| `Espfc/Utils/` | math, filters, helpers | |
| `AHRS/` | attitude estimation: Madgwick, Mahony, Kalman, **Ekf** | 9 |
| `EscDriver/` | ESC protocols (DSHOT/PWM/...) | 11 |
| `Gps/` | GPS parsing | 3 |
| `betaflight/` | Betaflight-compatible blackbox/types | 80 |
| `printf/`, `EspWire/`, `MultiButton/` | support libs | 9 |

Total: ~279 files, ~36,000 lines.

## Build configuration (for reference)

- `platformio.ini.reference` — copy of the build config (targets, flags).
- `partitions_4M_nota.csv` — the custom ESP32 partition table the firmware
  requires (Arduino IDE's default partitions will not match).

## Pin mapping

ESP32 default pins live in `Espfc/Target/TargetESP32.h` and
`Espfc/Target/TargetEsp32Common.h`. Pins can also be remapped at runtime via the
CLI `resource` command (no re-flash needed).
