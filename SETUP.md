# ESP-FC — Complete Setup Guide (Step by Step)

This guide takes you from a bare ESP32 to a configured flight controller, **one
step at a time**. Do it in order. Keep **propellers OFF** until the very end.

Related docs:
- **[esp32-connection-guide.md](esp32-connection-guide.md)** — full wiring
- **[pre-flight-checklist.md](pre-flight-checklist.md)** — final safety checklist

---

## Step 1 — Install the tools

1. Install **PlatformIO Core**:
   ```bash
   pip install --upgrade platformio
   ```
2. Verify:
   ```bash
   pio --version
   ```
3. (Optional) Install the **ESP-FC Configurator** (Web/desktop) for a GUI — the
   CLI alone is enough to complete this guide.

## Step 2 — Get the firmware

```bash
git clone https://github.com/MahediIslamNadim/esp32.git
cd esp32
```

## Step 3 — Build the firmware

```bash
pio run -e esp32          # use esp32s3 / esp32s2 / esp32c3 for those boards
```
A successful build ends with `[SUCCESS]` and creates `.pio/build/esp32/firmware.bin`.

## Step 4 — Flash the ESP32

1. Connect the ESP32 to USB.
2. Flash:
   ```bash
   pio run -e esp32 -t upload
   ```
3. If upload fails, hold the **BOOT** button while it starts, or unplug signal
   wires on strapping pins (GPIO 0, 2, 12) — see the connection guide §8.

## Step 5 — Open the CLI

```bash
pio device monitor          # 115200 baud
```
Type `help` and press Enter. You should see a list of commands. Also run:
```
version
status
```
`status` should report a detected **gyro** once the IMU is wired.

## Step 6 — Wire the hardware

Follow **[esp32-connection-guide.md](esp32-connection-guide.md)** and confirm:

- [ ] Common ground between ESP32, ESCs, receiver, sensors
- [ ] IMU on SPI (CS=5) or I2C (SDA=21 / SCL=22), powered from 3V3
- [ ] Receiver on UART2 (RX=16, TX=17)
- [ ] 4 ESC signal wires on GPIO 27 / 25 / 4 / 12
- [ ] Battery voltage divider into GPIO 36 (kept under 3.3 V)
- [ ] Powered from a 5 V BEC in flight (not USB)

> Keep the **battery disconnected** and **props off** for all configuration below.

## Step 7 — Select your gyro / IMU

In `status`, check the gyro is detected. Supported IMUs include:
`MPU6000, MPU6050, MPU6500, MPU9250, ICM20602, BMI160, LSM6DSO`.

If detection is wrong, set the device explicitly via `set` (see `dump` for the
exact key name on your build), then `save`.

## Step 8 — Calibrate the sensors

1. Place the board **flat and still**.
2. Calibrate the gyro:
   ```
   gyro
   ```
3. Calibrate the accelerometer **level** (Configurator button or matching CLI).
4. (If a magnetometer is fitted) calibrate by rotating on all axes.
5. Confirm the artificial horizon / attitude is stable and level.

## Step 9 — Set up the receiver

1. Bind your receiver to the transmitter.
2. Select the RC protocol matching your RX: **CRSF / SBUS / IBUS / PPM**.
3. Confirm in the Configurator/CLI receiver view that:
   - Throttle reads low at rest, high at full
   - Roll / Pitch / Yaw move the right channels
   - Centered sticks ≈ 1500, range ≈ 1000–2000

## Step 10 — Configure ESCs & motors

1. **Props off. Battery connected.**
2. Choose the ESC protocol to match your ESCs:
   `PWM, ONESHOT125, ONESHOT42, MULTISHOT, DSHOT150, DSHOT300, DSHOT600, PROSHOT, BRUSHED`.
3. Use the motor test tab to verify:
   - [ ] Motor order M1–M4 maps to the correct arms
   - [ ] Each motor spins in the **correct direction** for your mixer
     (reverse in the ESC or via DShot if wrong)
4. Set the **mixer** for your frame (e.g. quad X):
   ```
   mixer
   ```

## Step 11 — Modes, arming & failsafe

1. Assign an **ARM** switch to an AUX channel.
2. (Recommended for first flight) assign **ANGLE / self-level** to a switch.
3. Configure **failsafe** so the FC disarms when the radio link is lost.
4. Test failsafe (props off): arm → turn the TX off → motors must stop.

## Step 12 — Battery & voltage

1. Compare the FC-reported battery voltage to a multimeter; adjust the voltage
   scale if needed.
2. Set the low-voltage warning (and buzzer on GPIO 26 if fitted).

## Step 13 — Save & back up

```
save        # saves and reboots
```
After reboot, back up the full configuration:
```
dump
```
Copy the output into a text file so you can restore it later.

## Step 14 — Final checks & first flight

Run through the **[pre-flight-checklist.md](pre-flight-checklist.md)**, then:

1. Move to a wide, open, people-free outdoor area.
2. Mount props in the correct rotation; tighten nuts.
3. Arm → gentle throttle → confirm a level, stable lift-off.
4. If it flips, **disarm immediately** and recheck motor order/direction.
5. Short hover, land, disarm, **disconnect the battery**.

---

## Troubleshooting

| Symptom | Likely cause / fix |
| ------- | ------------------ |
| Upload fails | Hold BOOT during flash; free strapping pins 0/2/12 |
| No gyro in `status` | Check SPI/I2C wiring, CS=5, 3V3 power, correct IMU |
| No receiver channels | Wrong protocol or RX on wrong UART (RX=16) |
| Motors spin wrong way | Reverse motor in ESC / DShot direction |
| Won't arm | Throttle not low, not level, failsafe active, or arm switch unset |
| Voltage wrong | Adjust voltage scale; check the divider on GPIO 36 |
| Flips on takeoff | Motor order or direction wrong (redo Step 10) |

## Reset everything

```
defaults     # factory reset
save
```

See **[README.md](README.md)** for build details and **the CLI `help`** command
for the full list of options on your firmware build.
