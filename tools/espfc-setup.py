#!/usr/bin/env python3
"""ESP-FC guided setup & flasher.

One command takes a user from a fresh machine to a flashed ESP32:
  * auto-installs dependencies (PlatformIO, pyserial)
  * interactive menu (Quick Setup / Manual Config)
  * builds the firmware for the chosen board
  * detects the connected ESP32 and flashes it
  * (Quick Setup) pushes the chosen gyro/ESC config over the CLI

Run from the project root:
    python3 tools/espfc-setup.py
    python3 tools/espfc-setup.py --check   # only verify dependencies
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

# ---- option tables (values verified against the firmware source) -------------

BOARDS = ["esp32", "esp32s3", "esp32s2", "esp32c3"]

# CLI: set gyro_dev=<value>
GYROS = ["AUTO", "MPU6500", "MPU6050", "MPU9250", "ICM20602", "MPU6000",
         "LSM6DSO", "BMI160"]

# CLI: set output_motor_protocol=<value>
ESCS = ["DSHOT600", "DSHOT300", "DSHOT150", "ONESHOT125", "MULTISHOT",
        "PWM", "BRUSHED"]

# Receiver providers (configured via serial port / Configurator)
RECEIVERS = ["CRSF", "SBUS", "IBUS", "PPM"]

# Pin settings, grouped for the manual editor (CLI keys: set pin_<x>=<gpio>).
PIN_GROUPS = {
    "Motors / outputs": ["pin_output_0", "pin_output_1", "pin_output_2",
                          "pin_output_3", "pin_output_4", "pin_output_5",
                          "pin_output_6", "pin_output_7"],
    "Receiver input":   ["pin_input_rx", "pin_input_adc_0", "pin_input_adc_1"],
    "UART serial":      ["pin_serial_0_tx", "pin_serial_0_rx",
                          "pin_serial_1_tx", "pin_serial_1_rx",
                          "pin_serial_2_tx", "pin_serial_2_rx"],
    "SPI bus":          ["pin_spi_0_sck", "pin_spi_0_mosi", "pin_spi_0_miso",
                          "pin_spi_cs_0", "pin_spi_cs_1", "pin_spi_cs_2"],
    "I2C bus":          ["pin_i2c_scl", "pin_i2c_sda"],
    "Misc":             ["pin_button", "pin_buzzer", "pin_buzzer_invert",
                          "pin_led", "pin_led_invert", "pin_led_type"],
}

# Firmware default GPIOs for the ESP32 target (from Target/TargetESP32.h).
# -1 means "unassigned". Shown as a hint in the manual pin editor.
PIN_DEFAULTS = {
    "esp32": {
        "pin_output_0": 27, "pin_output_1": 25, "pin_output_2": 4,
        "pin_output_3": 12, "pin_output_4": -1, "pin_output_5": -1,
        "pin_output_6": -1, "pin_output_7": -1,
        "pin_input_rx": 35, "pin_input_adc_0": 36, "pin_input_adc_1": 39,
        "pin_serial_0_tx": 1, "pin_serial_0_rx": 3,
        "pin_serial_1_tx": 33, "pin_serial_1_rx": 32,
        "pin_serial_2_tx": 17, "pin_serial_2_rx": 16,
        "pin_spi_0_sck": 18, "pin_spi_0_mosi": 23, "pin_spi_0_miso": 19,
        "pin_spi_cs_0": 5, "pin_spi_cs_1": 13, "pin_spi_cs_2": -1,
        "pin_i2c_scl": 22, "pin_i2c_sda": 21,
        "pin_button": 0, "pin_buzzer": 26, "pin_led": 2,
    },
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "espfc-settings.txt")

def load_known_settings():
    """All valid CLI setting names (from the bundled reference file)."""
    try:
        with open(SETTINGS_FILE) as f:
            return [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return []

# ---- pretty printing ---------------------------------------------------------

class C:
    G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[94m"
    BOLD = "\033[1m"; DIM = "\033[2m"; END = "\033[0m"

def _supports_color():
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

if not _supports_color():
    for _n in ("G", "Y", "R", "B", "BOLD", "DIM", "END"):
        setattr(C, _n, "")

def info(msg):  print(f"{C.B}•{C.END} {msg}")
def ok(msg):    print(f"{C.G}✓{C.END} {msg}")
def warn(msg):  print(f"{C.Y}!{C.END} {msg}")
def err(msg):   print(f"{C.R}✗{C.END} {msg}")

def banner():
    print(f"""{C.BOLD}{C.B}
  ╔══════════════════════════════════════╗
  ║          ESP-FC  Setup  Tool         ║
  ║   build · configure · flash · fly    ║
  ╚══════════════════════════════════════╝{C.END}""")

# ---- dependency handling -----------------------------------------------------

def run(cmd, **kw):
    """Run a command, streaming output. Returns the exit code."""
    print(f"{C.DIM}$ {' '.join(cmd)}{C.END}")
    return subprocess.call(cmd, **kw)

VENV_DIR = os.path.join(PROJECT_ROOT, ".espfc-venv")

def venv_python(venv=VENV_DIR):
    win = os.path.join(venv, "Scripts", "python.exe")
    return win if os.path.exists(win) else os.path.join(venv, "bin", "python")

def in_our_venv():
    return os.environ.get("ESPFC_IN_VENV") == "1"

def venv_ready():
    vpy = venv_python()
    if not os.path.exists(vpy):
        return False
    code = subprocess.call([vpy, "-c", "import platformio, serial"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return code == 0

def pio_cmd():
    """Return a runnable PlatformIO command, or None if not available."""
    if in_our_venv():
        try:
            import platformio  # noqa: F401
            return [sys.executable, "-m", "platformio"]
        except ImportError:
            return None
    exe = shutil.which("pio") or shutil.which("platformio")
    if exe:
        return [exe]
    try:
        import platformio  # noqa: F401
        return [sys.executable, "-m", "platformio"]
    except ImportError:
        return None

def pip_install(pkg, py=None):
    return run([py or sys.executable, "-m", "pip", "install", "--upgrade",
                pkg]) == 0

def create_venv():
    """Create an isolated venv and install PlatformIO + pyserial into it."""
    info("Setting up an isolated environment (.espfc-venv) ...")
    if subprocess.call([sys.executable, "-m", "venv", VENV_DIR]) != 0:
        err("Could not create a virtualenv.")
        warn("Install the venv module first:  sudo apt install python3-venv")
        return False
    vpy = venv_python()
    pip_install("pip", vpy)  # best effort
    if pip_install("platformio", vpy) and pip_install("pyserial", vpy):
        ok("Dependencies installed in .espfc-venv")
        return True
    err("Failed to install dependencies inside the venv.")
    return False

def relaunch_in_venv():
    """Re-run this script using the venv's Python (deps available there)."""
    vpy = venv_python()
    info("Relaunching inside the isolated environment ...")
    env = dict(os.environ, ESPFC_IN_VENV="1")
    script = os.path.abspath(__file__)
    os.execve(vpy, [vpy, script, *sys.argv[1:]], env)

def ensure_pip():
    try:
        import pip  # noqa: F401
        return True
    except ImportError:
        err("pip is not available for this Python. Install pip and re-run.")
        return False

def has_serial():
    try:
        import serial  # noqa: F401
        import serial.tools.list_ports  # noqa: F401
        return True
    except ImportError:
        return False

def check_dependencies():
    info(f"Python {sys.version.split()[0]}")

    # Already relaunched inside our venv: deps are installed there.
    if in_our_venv():
        if pio_cmd() and has_serial():
            ok("PlatformIO found"); ok("pyserial found")
            return True
        err("Isolated environment is incomplete — delete .espfc-venv and retry.")
        return False

    if os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0:
        warn("Running as root (sudo) is not recommended — run without sudo.")

    # A previously created venv we can reuse straight away.
    if venv_ready():
        ok("Using existing isolated environment (.espfc-venv)")
        relaunch_in_venv()  # does not return

    if not ensure_pip():
        return False

    have_pio = pio_cmd() is not None
    have_serial = has_serial()
    if have_pio and have_serial:
        ok("PlatformIO found"); ok("pyserial found")
        return True

    # Try a normal install first; if the system Python is externally managed
    # (PEP 668), fall back to an isolated venv and relaunch inside it.
    need_venv = False
    if not have_pio:
        warn("PlatformIO not found — installing...")
        if pip_install("platformio") and pio_cmd():
            ok("PlatformIO installed")
        else:
            need_venv = True
    if not need_venv and not have_serial:
        warn("pyserial not found — installing...")
        if pip_install("pyserial"):
            ok("pyserial installed")
        else:
            need_venv = True

    if need_venv:
        warn("System Python is externally managed — using an isolated venv.")
        if create_venv():
            relaunch_in_venv()  # does not return
        err("Could not set up dependencies. Try: pipx install platformio")
        return False
    return True

# ---- prompts -----------------------------------------------------------------

def choose(title, options, default_index=0):
    print(f"\n{C.BOLD}{title}{C.END}")
    for i, opt in enumerate(options):
        mark = f"{C.DIM}(default){C.END}" if i == default_index else ""
        print(f"  {i + 1}) {opt} {mark}")
    while True:
        raw = input(f"> [{default_index + 1}] ").strip()
        if raw == "":
            return options[default_index]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        warn("Invalid choice, try again.")

def confirm(question, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"{question} {suffix} ").strip().lower()
    if raw == "":
        return default
    return raw in ("y", "yes")

# ---- port detection ----------------------------------------------------------

def detect_port():
    try:
        from serial.tools import list_ports
    except ImportError:
        return None
    candidates = []
    for p in list_ports.comports():
        desc = (p.description or "") + (p.manufacturer or "")
        if any(k in desc for k in ("CP210", "CH340", "USB", "UART", "Silicon",
                                   "wch", "Espressif")):
            candidates.append(p.device)
    if not candidates:  # fall back to any non-bluetooth serial device
        candidates = [p.device for p in list_ports.comports()
                      if "Bluetooth" not in (p.description or "")]
    return candidates[0] if candidates else None

# ---- build / flash / configure ----------------------------------------------

def build(board):
    pio = pio_cmd()
    info(f"Building firmware for {C.BOLD}{board}{C.END} ...")
    return run(pio + ["run", "-e", board], cwd=PROJECT_ROOT) == 0

def flash(board, port=None):
    pio = pio_cmd()
    cmd = pio + ["run", "-e", board, "-t", "upload"]
    if port:
        cmd += ["--upload-port", port]
    info(f"Flashing {C.BOLD}{board}{C.END}" + (f" on {port}" if port else "") + " ...")
    return run(cmd, cwd=PROJECT_ROOT) == 0

def send_settings(port, settings):
    """Apply a dict of {name: value} to the board over the CLI, then save."""
    if not settings:
        return True
    if not port:
        print_settings_cli(settings)
        return False
    try:
        import serial
    except ImportError:
        warn("pyserial missing — apply these manually:")
        print_settings_cli(settings)
        return False
    cmds = [f"set {k}={v}" for k, v in settings.items()] + ["save"]
    info("Applying configuration over the CLI ...")
    try:
        with serial.Serial(port, 115200, timeout=2) as ser:
            time.sleep(2.0)  # let the board boot after flashing
            ser.write(b"\r\n")
            time.sleep(0.3)
            for c in cmds:
                ser.write((c + "\r\n").encode())
                print(f"  {C.DIM}>{C.END} {c}")
                time.sleep(0.3)
            time.sleep(2.0)  # allow save + reboot
        ok("Configuration applied and saved.")
        return True
    except Exception as e:  # noqa: BLE001
        warn(f"Auto-config failed ({e}). Apply these manually:")
        print_settings_cli(settings)
        return False

def print_settings_cli(settings):
    print(f"\n{C.BOLD}Open the CLI (pio device monitor) and run:{C.END}")
    for k, v in settings.items():
        print(f"  set {k}={v}")
    print("  save")

def apply_config(port, gyro, esc):
    """Quick-setup convenience wrapper around send_settings()."""
    settings = {}
    if gyro and gyro != "AUTO":
        settings["gyro_dev"] = gyro
        settings["accel_dev"] = gyro
    if esc:
        settings["output_motor_protocol"] = esc
    send_settings(port, settings)

def receiver_hint(rx):
    print(f"\n{C.BOLD}Receiver ({rx}):{C.END}")
    if rx == "PPM":
        print("  Wire the PPM signal to GPIO 35, then enable PPM input in the "
              "ESP-FC Configurator.")
    else:
        print(f"  Wire the receiver to UART2 (RX=16, TX=17), then in the ESP-FC "
              f"Configurator set the receiver to Serial/{rx} on UART2.")
    print(f"  {C.DIM}(Receiver protocol is a serial-port function, set via the "
          f"Configurator — see HARDWARE.md){C.END}")

# ---- flows -------------------------------------------------------------------

def wait_for_board():
    print(f"\n{C.BOLD}{C.Y}>> Connect your ESP32 to USB now, then press "
          f"Enter.{C.END}")
    input()
    port = detect_port()
    if port:
        ok(f"Detected board on {C.BOLD}{port}{C.END}")
    else:
        warn("No port auto-detected; PlatformIO will pick one automatically.")
    return port

def quick_setup():
    print(f"\n{C.BOLD}{C.G}Quick Setup{C.END} — answer a few questions.")
    board = choose("Which board?", BOARDS)
    gyro = choose("Which gyro / IMU?", GYROS)
    esc = choose("Which ESC protocol?", ESCS)
    rx = choose("Which receiver?", RECEIVERS)

    print(f"\n{C.BOLD}Summary{C.END}")
    print(f"  board={board}  gyro={gyro}  esc={esc}  receiver={rx}")
    if not confirm("Proceed to build?"):
        return

    if not build(board):
        err("Build failed. Fix the error above and try again.")
        return
    ok("Build succeeded.")

    if not confirm("Flash to the board now?"):
        info("Skipped flashing. You can flash later from the menu.")
        return
    port = wait_for_board()
    if not flash(board, port):
        err("Flash failed. Check the cable / drivers and try again.")
        return
    ok("Flash complete! 🎉")

    if port and confirm("Apply the gyro/ESC config to the board now?"):
        apply_config(port, gyro, esc)
    else:
        apply_config(None, gyro, esc)  # prints commands when no port
    receiver_hint(rx)

    print(f"\n{C.G}{C.BOLD}Done.{C.END} Next: follow "
          f"pre-flight-checklist.md before flying (props off!).")

# ---- manual config editor ----------------------------------------------------

def edit_pins(settings, board="esp32"):
    """Customize any pin (motors, UART, SPI, I2C, buzzer, LED, …)."""
    defaults = PIN_DEFAULTS.get(board, {})
    while True:
        groups = list(PIN_GROUPS.keys())
        print(f"\n{C.BOLD}Edit pins{C.END} "
              f"{C.DIM}(values are GPIO numbers; -1 = unassigned){C.END}")
        if not defaults:
            print(f"  {C.DIM}(defaults shown for esp32 only; this is {board})"
                  f"{C.END}")
        for i, g in enumerate(groups):
            print(f"  {i + 1}) {g}")
        print(f"  0) Back")
        raw = input("> ").strip()
        if raw in ("0", "", "b", "back"):
            return
        if not (raw.isdigit() and 1 <= int(raw) <= len(groups)):
            warn("Pick a group number."); continue
        group = groups[int(raw) - 1]
        print(f"  {C.DIM}(blank = keep current/default){C.END}")
        for pin in PIN_GROUPS[group]:
            cur = settings.get(pin)
            if cur is not None:
                hint = f" {C.DIM}[set to: {cur}]{C.END}"
            elif pin in defaults:
                hint = f" {C.DIM}[default: {defaults[pin]}]{C.END}"
            else:
                hint = ""
            val = input(f"  {pin}{hint} = ").strip()
            if val:
                settings[pin] = val

def edit_setting(settings, known):
    """Set any of the firmware's CLI settings by name."""
    print(f"\n{C.BOLD}Edit a setting{C.END} "
          f"{C.DIM}(type part of a name to search, blank to cancel){C.END}")
    query = input("setting name> ").strip()
    if not query:
        return
    if known and query not in known:
        matches = [s for s in known if query in s]
        if not matches:
            warn(f"No setting matches '{query}'."); return
        if len(matches) > 1:
            print(f"  {len(matches)} matches:")
            for m in matches[:40]:
                print(f"    {m}")
            if len(matches) > 40:
                print(f"    ... (+{len(matches) - 40} more)")
            return
        query = matches[0]
        info(f"Using '{query}'")
    val = input(f"{query} = ").strip()
    if val:
        settings[query] = val
        ok(f"set {query}={val} (pending)")

def show_pending(settings):
    if not settings:
        print(f"\n{C.DIM}No changes yet.{C.END}")
        return
    print(f"\n{C.BOLD}Pending changes ({len(settings)}):{C.END}")
    for k, v in settings.items():
        print(f"  set {k}={v}")

def manual_config():
    print(f"\n{C.BOLD}{C.G}Manual Config{C.END} — full customization "
          f"(pins + any setting).")
    known = load_known_settings()
    if known:
        info(f"{len(known)} settings available (see tools/espfc-settings.txt)")
    board = choose("Which board?", BOARDS)
    settings = {}

    while True:
        print(f"""
{C.BOLD}Manual menu{C.END}  {C.DIM}(board={board}, pending={len(settings)}){C.END}
  1) Edit pins
  2) Edit a setting (gyro, ESC, rates, filters, features, …)
  3) Show pending changes
  4) Clear pending changes
  5) Build, flash & apply
  0) Back to main menu""")
        choice = input("> ").strip()
        if choice == "1":
            edit_pins(settings, board)
        elif choice == "2":
            edit_setting(settings, known)
        elif choice == "3":
            show_pending(settings)
        elif choice == "4":
            settings.clear(); ok("Cleared.")
        elif choice == "5":
            break
        elif choice in ("0", "", "b", "back"):
            return
        else:
            warn("Pick 0–5.")

    show_pending(settings)
    if not confirm("Build now?"):
        return
    if not build(board):
        err("Build failed."); return
    ok("Build succeeded.")
    if not confirm("Flash to the board now?"):
        if settings:
            print_settings_cli(settings)
        return
    port = wait_for_board()
    if not flash(board, port):
        err("Flash failed."); return
    ok("Flash complete! 🎉")
    if settings:
        if port and confirm("Apply your settings to the board now?"):
            send_settings(port, settings)
        else:
            print_settings_cli(settings)
    print(f"\n{C.G}{C.BOLD}Done.{C.END} Verify with 'pio device monitor' → "
          f"'dump', then see pre-flight-checklist.md.")

def menu():
    while True:
        print(f"""
{C.BOLD}Main menu{C.END}
  1) Quick Setup   {C.DIM}(recommended){C.END}
  2) Manual Config
  3) Exit""")
        choice = input("> ").strip()
        if choice == "1":
            quick_setup()
        elif choice == "2":
            manual_config()
        elif choice in ("3", "q", "quit", "exit", ""):
            print("Bye 👋")
            return
        else:
            warn("Pick 1, 2 or 3.")

# ---- entry point -------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="ESP-FC guided setup & flasher")
    ap.add_argument("--check", action="store_true",
                    help="verify dependencies and exit")
    args = ap.parse_args()

    banner()
    info("Checking dependencies...")
    if not check_dependencies():
        err("Missing required dependencies. See messages above.")
        sys.exit(1)
    ok("All set.")

    if args.check:
        return

    if not os.path.exists(os.path.join(PROJECT_ROOT, "platformio.ini")):
        err("platformio.ini not found — run this from the ESP-FC project root.")
        sys.exit(1)

    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted. Bye 👋")

if __name__ == "__main__":
    main()
