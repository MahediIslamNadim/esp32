# ESP-FC — Pre-Flight Checklist

A step-by-step checklist to take an ESP-FC build from a flashed board to a safe
first flight. **Do every step with propellers OFF until Stage 6.**

> ⚠️ A misconfigured quad can spin motors unexpectedly. Keep props off, keep the
> battery disconnected while wiring, and keep hands clear during motor tests.

---

## Stage 0 — Bench setup (no battery)

- [ ] Firmware flashed: `pio run -e esp32 -t upload`
- [ ] Board boots — open the CLI: `pio device monitor` (115200 baud)
- [ ] `version` prints firmware info
- [ ] `status` runs without errors
- [ ] Frame built, all screws tight, motors mounted, ESCs soldered
- [ ] Wiring matches `esp32-connection-guide.md` (common ground confirmed)

## Stage 1 — Sensors (USB power only, no battery)

- [ ] `status` shows the **gyro/accel detected** (not "none")
- [ ] Board sitting still and level on the bench
- [ ] Calibrate the gyro — keep the board perfectly still:
      `gyro` (or use the Configurator's calibrate button)
- [ ] Accelerometer calibrated level
- [ ] (If used) magnetometer detected; calibrate by rotating on all axes
- [ ] (If used) barometer / GPS detected in `status`

## Stage 2 — Receiver & radio (props OFF)

- [ ] Receiver bound to the transmitter (solid bind LED)
- [ ] Correct RC protocol selected (CRSF / SBUS / IBUS / PPM) on UART2 (RX=16)
- [ ] Sticks move the channels in the Configurator/CLI receiver tab
- [ ] Channel map correct: Throttle, Roll, Pitch, Yaw, AUX in the right order
- [ ] Throttle reads **low/min** at rest, max at full
- [ ] Endpoints/trims: centered sticks ≈ 1500, range ≈ 1000–2000

## Stage 3 — Modes & failsafe (props OFF)

- [ ] **ARM** switch assigned to an AUX channel
- [ ] (Recommended) ANGLE / self-level mode on a switch for the first flight
- [ ] **Failsafe** configured — when you switch the TX off, the FC disarms
- [ ] Verify failsafe: power FC, arm (props off!), turn TX off → motors stop
- [ ] Low-battery / beeper warning set (if a buzzer is wired on GPIO 26)

## Stage 4 — Motors & ESCs (props OFF, battery connected)

- [ ] Props **removed** before connecting the battery
- [ ] Correct ESC protocol set (DShot300/600 or PWM/Oneshot) to match your ESCs
- [ ] Motor order correct via the motor test tab (M1→M4 map as expected)
- [ ] **Motor direction** correct for your mixer (reverse in ESC/CLI if needed)
- [ ] No motor stutters, all spin smoothly at low test throttle
- [ ] Mixer set to your frame type (e.g. quad X): check `mixer` / `dump`

## Stage 5 — Save & final bench checks

- [ ] Settings saved: `save` (board reboots)
- [ ] Re-check after reboot: `status` clean, sensors still detected
- [ ] Back up your config: run `dump` and save the output to a file
- [ ] Battery voltage reads correctly (compare to a multimeter)
- [ ] Arming prevented when: throttle high, board not level (if enabled), or
      failsafe active — confirm it **refuses to arm** in these cases

## Stage 6 — First flight (props ON, open area)

- [ ] Move to a wide, open, people-free area outdoors
- [ ] Props mounted in the correct rotation direction, nuts tight
- [ ] Stand back; battery freshly charged and strapped down
- [ ] Arm → apply gentle throttle → confirm it lifts level, no flips
- [ ] If it flips on takeoff → **disarm immediately**, recheck motor order &
      direction (Stage 4)
- [ ] Short hover ~30 cm; check it holds attitude (ANGLE mode)
- [ ] Land, disarm, check motor temperatures (warm OK, hot = problem)
- [ ] Disconnect battery before touching props

---

## Emergency reminders

- **Disarm** is your stop button — keep a finger on the arm switch.
- If anything feels wrong, **disarm and cut throttle**.
- Never arm with props on while connected to USB on the bench.
- Always disconnect the battery before working on the frame.

## Useful CLI commands

| Command | Purpose |
| ------- | ------- |
| `help` | list all commands |
| `status` | sensors, cycle time, live state |
| `version` | firmware version |
| `gyro` | gyro calibration |
| `mixer` | show / set mixer (frame type) |
| `get <name>` / `set <name>=<value>` | read / change a setting |
| `dump` | print full config (use to back up) |
| `defaults` | reset to factory defaults |
| `save` | save settings and reboot |
| `reboot` | restart the FC |

See also: [`esp32-connection-guide.md`](esp32-connection-guide.md) for wiring.
