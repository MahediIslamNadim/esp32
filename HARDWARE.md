# ESP-FC — Hardware Configuration Reference

Wiring and CLI settings for each supported **gyro/IMU**, **ESC protocol**, and
**receiver**. All values below are taken straight from the firmware source, so
the option names match exactly what the CLI accepts.

Open the CLI with `pio device monitor` (115200 baud). After changing settings,
always run `save` (the board reboots). Confirm hardware with `status`.

> ⚠️ Configure everything with **props off** and the battery disconnected.

---

## 1. Gyro / IMU

Default pins (ESP32): SPI `SCK=18, MOSI=23, MISO=19, gyro CS=5`, or
I2C `SDA=21, SCL=22`. Power the IMU from **3V3** (never 5V).

**CLI keys** — `gyro_dev`, `gyro_bus`, `gyro_align`
(accelerometer mirrors these: `accel_dev`, `accel_bus`).

`gyro_dev` accepted values:
`AUTO, NONE, MPU6000, MPU6050, MPU6500, MPU9250, LSM6DSO, ICM20602, BMI160`

`gyro_bus` accepted values: `AUTO, I2C, SPI, SLV, NONE`

| IMU | Typical bus | Wiring | CLI |
| --- | ----------- | ------ | --- |
| **MPU6500** | SPI (or I2C) | SCK/MOSI/MISO + CS=5, 3V3, GND | `set gyro_dev=MPU6500` then `set gyro_bus=SPI` |
| **MPU6050** | I2C | SDA=21, SCL=22, 3V3, GND | `set gyro_dev=MPU6050` then `set gyro_bus=I2C` |
| **MPU9250** | SPI (or I2C) | as MPU6500; has built-in mag | `set gyro_dev=MPU9250` then `set gyro_bus=SPI` |
| **ICM20602** | SPI | SCK/MOSI/MISO + CS=5, 3V3, GND | `set gyro_dev=ICM20602` then `set gyro_bus=SPI` |

Leaving `gyro_dev=AUTO` lets the firmware auto-detect — set it explicitly only if
auto-detection fails.

After wiring + setting:
```
save
status        # should report the gyro detected
gyro          # calibrate, board flat and still
```

### Orientation (`gyro_align`)
If your IMU is mounted rotated, fix it without rewiring:
```
set gyro_align=CW90        # DEFAULT, CW0, CW90, CW180, CW270 (+ *_FLIP, CUSTOM)
save
```

---

## 2. ESC / Motors

Motor signal pins (ESP32): **M0=27, M1=25, M2=4, M3=12**. Common ground with the
ESCs is mandatory.

**CLI key** — `output_motor_protocol`

Accepted values:
`PWM, ONESHOT125, ONESHOT42, MULTISHOT, BRUSHED, DSHOT150, DSHOT300, DSHOT600, PROSHOT1000, DISABLED`

| ESC type | Set | Notes |
| -------- | --- | ----- |
| **BLHeli_S / 32 (digital)** | `set output_motor_protocol=DSHOT600` | Best choice; try `DSHOT300` on long wires |
| **DShot, slower/safer** | `set output_motor_protocol=DSHOT300` | More tolerant of noise |
| **Analog / older ESC** | `set output_motor_protocol=ONESHOT125` | or `PWM` for very old ESCs |
| **Brushed (tiny whoop)** | `set output_motor_protocol=BRUSHED` | Direct MOSFET drive, no ESC |

```
set output_motor_protocol=DSHOT600
save
```

Then, **props off, battery connected**, use the Configurator motor test tab to:
- verify motor order M1–M4,
- verify each motor's **direction** (reverse via DShot or by swapping two ESC
  wires on analog ESCs).

Useful related keys: `output_min_throttle`, `output_max_throttle`,
`output_min_command`, `output_dshot_telemetry`, `output_motor_poles`.

---

## 3. Receiver

Default receiver input: **UART2 RX=16, TX=17** (serial protocols), or **PPM=35**.
Power the RX from 5V or 3V3 per its spec; common ground required.

In ESP-FC the receiver is configured by assigning the **serial RX function to a
UART** and selecting the provider — easiest in the **Configurator** (Ports +
Receiver tabs). Supported providers in firmware:
`CRSF, SBUS, IBUS, SPEKTRUM, SUMD, SRXL, FPORT, JETIEXBUS`, plus **PPM**.

| Receiver | Protocol | Wiring | Setup |
| -------- | -------- | ------ | ----- |
| **ELRS / Crossfire** | CRSF | RX=16, TX=17 (telemetry), 5V, GND | Configurator → Receiver = Serial/CRSF on UART2 |
| **FrSky / Futaba** | SBUS | RX=16 (inverted), 5V, GND | Configurator → Serial/SBUS on UART2 |
| **FlySky (FS-iA6B)** | IBUS | RX=16, 5V, GND | Configurator → Serial/IBUS on UART2 |
| **Older RX** | PPM | PPM signal → GPIO 35, 5V, GND | Configurator → PPM input |

> CRSF and IBUS use a back-channel on TX=17 for telemetry — wire both for full
> two-way telemetry. SBUS is one-way (RX only) and is electrically inverted; most
> ESP32 SBUS setups work directly, but add an inverter if your RX needs it.

After binding and wiring:
```
save
status
```
Then confirm stick movement in the Configurator/CLI receiver view: throttle low
at rest, centered sticks ≈ 1500, range ≈ 1000–2000.

---

## 4. Battery monitoring

Voltage divider into **GPIO 36** (keep under 3.3 V), current sensor into **GPIO 39**.

| Key | Purpose |
| --- | ------- |
| `vbat_source` | voltage source |
| `vbat_scale` | calibrate reported voltage to a multimeter |
| `vbat_cell_warn` | per-cell low warning |
| `ibat_source`, `ibat_scale` | current sensor source / scale |

```
set vbat_scale=110      # adjust until reported V matches a multimeter
save
```

---

## 5. Save, verify, back up

```
save        # store + reboot
status      # sensors detected, no errors
dump        # full config — copy to a file as a backup
```

See also: [SETUP.md](SETUP.md) · [esp32-connection-guide.md](esp32-connection-guide.md) ·
[pre-flight-checklist.md](pre-flight-checklist.md)
