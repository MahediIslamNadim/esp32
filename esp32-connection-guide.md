# ESP-FC — ESP32 Full Connection Guide

A complete wiring guide for building a flight controller with **ESP-FC** on a plain
**ESP32 (WROOM / DevKit / ESP32-mini)** board.

> All pin numbers below are the firmware **defaults** taken straight from
> `lib/Espfc/src/Target/TargetESP32.h`. Most can be remapped later from the
> Configurator / CLI, but wiring to these defaults is the easiest path.

---

## 1. Default pin map (ESP32)

| Function              | GPIO        | Notes                                        |
|-----------------------|-------------|----------------------------------------------|
| **Motor / Servo 0**   | `27`        | M0 (PWM / DShot / Oneshot)                    |
| **Motor / Servo 1**   | `25`        | M1                                            |
| **Motor / Servo 2**   | `4`         | M2                                            |
| **Motor / Servo 3**   | `12`        | M3 — also a strapping pin, see §8            |
| **UART0 TX**          | `1`         | MSP / CLI (USB programming port)              |
| **UART0 RX**          | `3`         | MSP / CLI                                     |
| **UART1 TX**          | `33`        | MSP (spare port)                              |
| **UART1 RX**          | `32`        | MSP                                           |
| **UART2 TX**          | `17`        | Serial RX telemetry (CRSF/SBUS back-channel)  |
| **UART2 RX**          | `16`        | **Receiver input** (CRSF / SBUS / IBUS …)     |
| **PPM / RX input**    | `35`        | input-only pin                                |
| **SPI SCK**           | `18`        | gyro / baro bus                               |
| **SPI MOSI**          | `23`        |                                               |
| **SPI MISO**          | `19`        |                                               |
| **SPI CS — Gyro**     | `5`         | chip-select for the IMU                       |
| **SPI CS — Baro**     | `13`        | chip-select for the barometer                 |
| **I2C SDA**           | `21`        | gyro / baro / mag (alternative to SPI)        |
| **I2C SCL**           | `22`        |                                               |
| **Buzzer**            | `26`        | active buzzer via transistor                  |
| **Button**            | `0`         | boot/bind button (strapping pin)              |
| **LED (status)**      | `2`         | onboard LED                                   |
| **ADC — Voltage**     | `36` (SVP)  | battery voltage divider                       |
| **ADC — Current**     | `39` (SVN)  | current sensor                                |

**Hard chip rules (do not violate):**
- GPIO `6–11` → reserved for the internal flash. **Never use.**
- GPIO `34–39` → **input only** (no output, no internal pull-ups).
- GPIO `20, 24, 28–31` → do not exist on the WROOM module.
- ESP32 ADC2 pins cannot be read while Wi-Fi is active — battery monitoring uses
  ADC1 pins (`36`, `39`) for this reason.

---

## 2. Power

```
LiPo (+) ──► BEC / ESC 5V out ──► ESP32 5V (VIN)
LiPo (–) ──► common GND ───────► ESP32 GND
```

- Feed the ESP32 from a **5V BEC** (the ESC's built-in 5V, or a separate UBEC).
- The ESP32's onboard regulator makes 3.3V for the chip; sensors are powered from
  the board's **3V3** pin.
- **Common ground is mandatory** — ESCs, receiver, sensors and the ESP32 must all
  share GND.
- Do **not** power from USB and the BEC at the same time unless your board has a
  power-path diode.

---

## 3. IMU — Gyro / Accelerometer (required)

The IMU is the only mandatory sensor. Connect it on **SPI** (preferred, up to
4 kHz) or **I2C** (up to 2 kHz).

### Option A — SPI (recommended, e.g. MPU6000 / ICM-42688 / BMI270)
```
IMU SCLK  ──► GPIO18 (SCK)
IMU MOSI  ──► GPIO23 (MOSI)
IMU MISO  ──► GPIO19 (MISO)
IMU CS    ──► GPIO5  (CS gyro)
IMU VCC   ──► 3V3
IMU GND   ──► GND
IMU INT   ──► (optional) GPIO34   ; data-ready interrupt, input-only pin
```

### Option B — I2C (e.g. MPU6050 / MPU9250)
```
IMU SDA   ──► GPIO21
IMU SCL   ──► GPIO22
IMU VCC   ──► 3V3
IMU GND   ──► GND
```
- Add 4.7 kΩ pull-ups on SDA/SCL if your sensor breakout doesn't already have them.

> Mount the IMU rigidly and vibration-damped, with the arrow/dot pointing forward.
> Set the correct board alignment in the Configurator afterwards.

---

## 4. Radio Receiver (required to fly)

Default receiver port is **UART2** (`RX = GPIO16`, `TX = GPIO17`).

### CRSF (ELRS / Crossfire) — recommended
```
RX module TX  ──► GPIO16 (ESP32 UART2 RX)
RX module RX  ──► GPIO17 (ESP32 UART2 TX)   ; needed for telemetry
RX module 5V  ──► 5V
RX module GND ──► GND
```

### SBUS (Frsky / Futaba)
```
RX SBUS out ──► GPIO16   ; SBUS is inverted + UART; ESP-FC handles inversion
RX 5V       ──► 5V
RX GND      ──► GND
```

### PPM
```
RX PPM out ──► GPIO35   (dedicated PPM input pin, input-only)
```

Enable the matching protocol (CRSF / SBUS / IBUS / PPM) and `Serial RX` on UART2
in the Configurator.

---

## 5. ESC / Motors

Default 4 outputs: **M0=27, M1=25, M2=4, M3=12**.

```
ESC1 signal ──► GPIO27   ESC1 GND ──► GND
ESC2 signal ──► GPIO25   ESC2 GND ──► GND
ESC3 signal ──► GPIO4    ESC3 GND ──► GND
ESC4 signal ──► GPIO12   ESC4 GND ──► GND
```

- Supported protocols: **PWM, Oneshot125, Multishot, DShot150/300/600** (DShot
  telemetry is supported on ESP32).
- Only the **signal** and **GND** wires go to the FC. ESC power comes from the
  battery, not from the ESP32.
- GPIO12 (M3) is a strapping pin — see §8 if the board won't flash/boot.
- The motor order / direction is set per ESC protocol in the mixer; verify with
  props **off** first.

---

## 6. Optional sensors & peripherals

### Barometer (altitude) — SPI or I2C
```
SPI:  SCK→18, MOSI→23, MISO→19, CS→GPIO13, VCC→3V3, GND→GND
I2C:  SDA→21, SCL→22, VCC→3V3, GND→GND
```
Supported: BMP280, BMP388, MS5611, SPL06, DPS310, …

### Magnetometer / Compass — I2C
```
SDA→GPIO21, SCL→GPIO22, VCC→3V3, GND→GND
```
Supported: HMC5883, QMC5883, IST8310, AK8963, …

### GPS — a spare UART (e.g. UART1)
```
GPS TX ──► GPIO32 (UART1 RX)
GPS RX ──► GPIO33 (UART1 TX)
GPS VCC ──► 5V (or 3V3 per module)
GPS GND ──► GND
```
Set the UART1 function to `GPS` and choose the baud (usually 9600/115200).

### Buzzer
```
GPIO26 ──► transistor base (via ~1kΩ) ──► buzzer ; buzzer + to 5V, emitter to GND
```
Use a transistor/MOSFET — don't drive the buzzer directly from the GPIO.

### Status LED
- Onboard LED on **GPIO2** works out of the box.
- For WS2812 addressable LEDs, assign a free output pin in the Configurator.

### Battery monitoring
```
Battery + ──► voltage divider ──► GPIO36 (ADC voltage)
Current sensor signal ──────────► GPIO39 (ADC current)
```
- ADC scale in firmware = `3.3V / 4096`. Size the divider so a full pack stays
  **below 3.3V** at the pin (e.g. for 4S use ~22k:4.7k after the board divider).
- Set the voltage/current scale in the Configurator to calibrate.

---

## 7. Programming & telemetry (UART0 / USB)

- **UART0** (`TX=1 / RX=3`) is the USB programming + **MSP/CLI** port.
- Flash the firmware and connect the **ESP-FC Configurator** over this USB port.
- A **Wi-Fi MSP** soft-serial port is also available — connect to the ESP32's
  access point and configure wirelessly (see `docs/wireless.md`).

---

## 8. Boot / strapping pin warnings (read before first flash)

Some default pins double as ESP32 strapping pins. If the board won't flash or
boot, an attached device may be holding one of these at the wrong level:

| GPIO | Role          | Rule                                                        |
|------|---------------|-------------------------------------------------------------|
| `0`  | Button        | Must be **HIGH** at boot; LOW = enter flash mode.           |
| `2`  | LED           | Must be floating or LOW to enter the serial bootloader.     |
| `5`  | Gyro CS       | Strapping; recommended output — fine as CS.                 |
| `12` | Motor 3       | Must be **LOW** at boot, or 3.3V flash can brown out.       |
| `15` | (free/SD CS)  | Internal pull-up; LOW silences boot log.                    |

Tip: disconnect the receiver/ESC signal lines during the very first flash if you
hit boot problems, then reconnect.

---

## 9. Quick wiring checklist

- [ ] Common ground between ESP32, ESCs, receiver, and all sensors
- [ ] ESP32 powered from a 5V BEC (not relying on USB in flight)
- [ ] IMU on SPI (CS=5) or I2C (SDA=21/SCL=22), powered from 3V3
- [ ] Receiver on UART2 (RX=16, TX=17) with the right protocol selected
- [ ] 4 ESC signal wires on GPIO 27 / 25 / 4 / 12
- [ ] Battery divider keeps GPIO36 below 3.3V
- [ ] First power-up with **props removed** — check motor order and direction
- [ ] Strapping pins (0, 2, 12) not held at the wrong level during flashing

---

## Reference

- Full pin tables for all boards: `docs/connections.md`
- General wiring notes: `docs/wiring.md`
- CLI commands: `docs/cli.md`
- Wireless setup: `docs/wireless.md`
- Source of truth for ESP32 defaults: `lib/Espfc/src/Target/TargetESP32.h`
