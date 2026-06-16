#!/usr/bin/env python3
"""ESP-FC Configurator — a desktop GUI for tuning a flashed ESP32 flight controller.

Talks to the firmware over USB serial using the MSP protocol (the same protocol
Betaflight Configurator uses), so no firmware changes are needed — every command
used here is already handled by `lib/Espfc/src/Connect/MspProcessor.cpp`.

Four tabs:
  * Setup       — live attitude (roll/pitch/yaw), level/gyro calibration,
                  accelerometer trim and board alignment. This is how you fix a
                  crookedly-mounted board: put the drone on a flat surface and
                  nudge the trim until the live readout shows 0/0.
  * PID Tuning  — read/edit roll, pitch and yaw P/I/D gains (flight stability).
  * Rates       — RC rate / super-rate / expo per axis (stick sensitivity / feel).
  * Motors      — per-motor test sliders, with a safety arm gate and STOP ALL.

Run from the project root:
    python3 tools/espfc-configurator.py

Requires: pyserial (pip install pyserial). tkinter ships with most Python builds.

SAFETY: remove all propellers before using the Motors tab.
"""

import struct
import threading
import time
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    raise SystemExit(
        "pyserial is required. Install it with:\n    pip install pyserial"
    )


# --------------------------------------------------------------------------- #
# MSP protocol command IDs (from lib/betaflight/src/msp/msp_protocol.h)
# --------------------------------------------------------------------------- #
MSP_API_VERSION = 1
MSP_FC_VARIANT = 2
MSP_NAME = 10
MSP_BOARD_ALIGNMENT_CONFIG = 38
MSP_SET_BOARD_ALIGNMENT_CONFIG = 39
MSP_STATUS = 101
MSP_RAW_IMU = 102
MSP_MOTOR = 104
MSP_RC = 105
MSP_ATTITUDE = 108
MSP_ANALOG = 110
MSP_RC_TUNING = 111
MSP_PID = 112
MSP_SET_PID = 202
MSP_SET_RC_TUNING = 204
MSP_ACC_CALIBRATION = 205
MSP_MAG_CALIBRATION = 206
MSP_SET_MOTOR = 214
MSP_ACC_TRIM = 240
MSP_SET_ACC_TRIM = 239
MSP_EEPROM_WRITE = 250

PID_ITEM_COUNT = 10      # FC_PID_ITEM_COUNT in ModelConfig.h (roll/pitch/yaw first)
MOTOR_COUNT = 4          # OUTPUT_CHANNELS / ESC_CHANNEL_COUNT on ESP32
MOTOR_MIN = 1000
MOTOR_MAX = 2000
MOTOR_TEST_LIMIT = 1300  # cap the test slider (~30%) so nothing runs away


# --------------------------------------------------------------------------- #
# MSP transport: a background reader thread parses frames; request() blocks
# until the matching reply (or ack) arrives.
# --------------------------------------------------------------------------- #
class Msp:
    def __init__(self):
        self.ser = None
        self._responses = {}          # cmd -> latest payload bytes
        self._events = {}             # cmd -> threading.Event
        self._lock = threading.Lock()
        self._reader = None
        self._running = False

    # -- connection -------------------------------------------------------- #
    def connect(self, port, baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0.1)
        self._running = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def disconnect(self):
        self._running = False
        if self._reader:
            self._reader.join(timeout=1.0)
        if self.ser:
            self.ser.close()
            self.ser = None

    @property
    def connected(self):
        return self.ser is not None and self.ser.is_open

    # -- framing ----------------------------------------------------------- #
    @staticmethod
    def _encode(cmd, data=b""):
        size = len(data)
        frame = bytearray(b"$M<")
        frame.append(size)
        frame.append(cmd)
        crc = size ^ cmd
        for b in data:
            frame.append(b)
            crc ^= b
        frame.append(crc & 0xFF)
        return bytes(frame)

    def _event(self, cmd):
        ev = self._events.get(cmd)
        if ev is None:
            ev = threading.Event()
            self._events[cmd] = ev
        return ev

    def send(self, cmd, data=b""):
        if not self.connected:
            return
        with self._lock:
            self.ser.write(self._encode(cmd, data))

    def request(self, cmd, data=b"", timeout=0.6):
        """Send a command and wait for the matching reply payload (or None)."""
        if not self.connected:
            return None
        ev = self._event(cmd)
        ev.clear()
        self.send(cmd, data)
        if ev.wait(timeout):
            return self._responses.get(cmd)
        return None

    def latest(self, cmd):
        return self._responses.get(cmd)

    # -- reader ------------------------------------------------------------ #
    def _read_loop(self):
        state = 0
        size = cmd = crc = 0
        payload = bytearray()
        while self._running:
            try:
                chunk = self.ser.read(256)
            except (OSError, serial.SerialException):
                break
            for b in chunk:
                if state == 0:
                    if b == ord("$"):
                        state = 1
                elif state == 1:
                    state = 2 if b == ord("M") else 0
                elif state == 2:
                    # direction: '>' reply, '!' error, '<' request (echo)
                    state = 3 if b in (ord(">"), ord("!")) else 0
                elif state == 3:
                    size = b
                    crc = b
                    state = 4
                elif state == 4:
                    cmd = b
                    crc ^= b
                    payload = bytearray()
                    state = 5 if size > 0 else 6
                elif state == 5:
                    payload.append(b)
                    crc ^= b
                    if len(payload) >= size:
                        state = 6
                elif state == 6:
                    if (crc & 0xFF) == b:
                        self._responses[cmd] = bytes(payload)
                        self._event(cmd).set()
                    state = 0


# --------------------------------------------------------------------------- #
# decode helpers
# --------------------------------------------------------------------------- #
def s16(buf, off):
    return struct.unpack_from("<h", buf, off)[0]


def u16(buf, off):
    return struct.unpack_from("<H", buf, off)[0]


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #
class App(ttk.Frame):
    POLL_MS = 120

    def __init__(self, root):
        super().__init__(root, padding=8)
        self.root = root
        self.msp = Msp()
        self.pack(fill="both", expand=True)
        self.motor_vars = []
        self.motor_arm = tk.BooleanVar(value=False)
        self._last_att = (0.0, 0.0, 0.0)   # last roll/pitch/yaw in degrees
        self.GRAPH_SAMPLES = 200
        self.gyro_hist = [deque([0] * self.GRAPH_SAMPLES, maxlen=self.GRAPH_SAMPLES)
                          for _ in range(3)]
        self._build_connection_bar()
        self._build_tabs()
        self._build_statusbar()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll()

    # -- top connection bar ------------------------------------------------ #
    def _build_connection_bar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Port:").pack(side="left")
        self.port_cb = ttk.Combobox(bar, width=22, state="readonly")
        self.port_cb.pack(side="left", padx=4)
        ttk.Button(bar, text="⟳", width=3, command=self._refresh_ports).pack(side="left")
        ttk.Label(bar, text="Baud:").pack(side="left", padx=(8, 0))
        self.baud_cb = ttk.Combobox(bar, width=8, state="readonly",
                                    values=["115200", "230400", "420000"])
        self.baud_cb.set("115200")
        self.baud_cb.pack(side="left", padx=4)
        self.connect_btn = ttk.Button(bar, text="Connect", command=self._toggle_connect)
        self.connect_btn.pack(side="left", padx=8)
        self.fc_lbl = ttk.Label(bar, text="not connected", foreground="#888")
        self.fc_lbl.pack(side="left", padx=8)
        self._refresh_ports()

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if ports and not self.port_cb.get():
            self.port_cb.set(ports[0])

    def _toggle_connect(self):
        if self.msp.connected:
            self.msp.disconnect()
            self.connect_btn.config(text="Connect")
            self.fc_lbl.config(text="not connected", foreground="#888")
            return
        port = self.port_cb.get()
        if not port:
            messagebox.showwarning("No port", "Select a serial port first.")
            return
        try:
            self.msp.connect(port, int(self.baud_cb.get()))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Connect failed", str(e))
            return
        self.connect_btn.config(text="Disconnect")
        time.sleep(0.2)
        variant = self.msp.request(MSP_FC_VARIANT)
        api = self.msp.request(MSP_API_VERSION)
        name = ""
        if variant:
            name = variant.decode("ascii", "ignore").strip()
        if api and len(api) >= 3:
            name += f"  API {api[1]}.{api[2]}"
        self.fc_lbl.config(text=name or "connected", foreground="#080")
        # pull current config into the editors
        self.read_pids()
        self.read_rates()
        self.read_trim()
        self.read_alignment()

    # -- tabs -------------------------------------------------------------- #
    def _build_tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self._build_setup_tab(nb)
        self._build_sensors_tab(nb)
        self._build_pid_tab(nb)
        self._build_rates_tab(nb)
        self._build_motor_tab(nb)

    # ---- Setup / calibration tab ---------------------------------------- #
    def _build_setup_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Setup")

        att = ttk.LabelFrame(tab, text="Live attitude (how the board sees 'level')",
                             padding=10)
        att.pack(fill="x")
        self.roll_lbl = self._big_readout(att, "Roll", 0)
        self.pitch_lbl = self._big_readout(att, "Pitch", 1)
        self.yaw_lbl = self._big_readout(att, "Yaw", 2)
        ttk.Label(att, text="Place the drone on a flat surface — roll & pitch "
                            "should read ~0.0°. If not, the board is mounted "
                            "crooked; fix it with trim / alignment below.",
                  wraplength=520, foreground="#555").grid(
            row=1, column=0, columnspan=3, pady=(8, 0), sticky="w")

        cal = ttk.LabelFrame(tab, text="Calibration", padding=10)
        cal.pack(fill="x", pady=8)
        ttk.Button(cal, text="Calibrate gyro / level  (keep still & flat)",
                   command=self.calibrate_acc).pack(side="left")
        ttk.Button(cal, text="Calibrate magnetometer",
                   command=self.calibrate_mag).pack(side="left", padx=6)

        trim = ttk.LabelFrame(tab, text="Accelerometer trim  (zero the live readout)",
                              padding=10)
        trim.pack(fill="x", pady=8)
        self.trim_pitch = self._trim_row(trim, "Pitch trim", 0)
        self.trim_roll = self._trim_row(trim, "Roll trim", 1)
        btns = ttk.Frame(trim)
        btns.grid(row=2, column=0, columnspan=5, pady=(8, 0), sticky="w")
        ttk.Button(btns, text="Read", command=self.read_trim).pack(side="left")
        ttk.Button(btns, text="Save trim", command=self.write_trim).pack(side="left", padx=6)

        align = ttk.LabelFrame(tab, text="Board alignment  (degrees, for a badly "
                                         "rotated mount)", padding=10)
        align.pack(fill="x", pady=8)
        self.align_roll = self._align_row(align, "Roll°", 0)
        self.align_pitch = self._align_row(align, "Pitch°", 1)
        self.align_yaw = self._align_row(align, "Yaw°", 2)
        abtns = ttk.Frame(align)
        abtns.grid(row=1, column=0, columnspan=6, pady=(8, 0), sticky="w")
        ttk.Button(abtns, text="Read", command=self.read_alignment).pack(side="left")
        ttk.Button(abtns, text="Auto-fill from current tilt",
                   command=self.autofill_alignment).pack(side="left", padx=6)
        ttk.Button(abtns, text="Save alignment",
                   command=self.write_alignment).pack(side="left", padx=6)
        ttk.Label(align, text="Auto-fill copies the live roll/pitch into the fields so "
                             "the firmware cancels the mount tilt. Save, then check the "
                             "readout reads ~0; if it moved the wrong way, negate the value.",
                  wraplength=520, foreground="#555").grid(
            row=2, column=0, columnspan=6, pady=(6, 0), sticky="w")

        ttk.Separator(tab).pack(fill="x", pady=6)
        ttk.Button(tab, text="💾  Save all settings to flash (EEPROM)",
                   command=self.save_eeprom).pack(anchor="w")

    def _big_readout(self, parent, name, col):
        f = ttk.Frame(parent)
        f.grid(row=0, column=col, padx=18)
        ttk.Label(f, text=name, foreground="#777").pack()
        lbl = ttk.Label(f, text="--.-°", font=("TkDefaultFont", 22, "bold"))
        lbl.pack()
        return lbl

    def _trim_row(self, parent, name, row):
        ttk.Label(parent, text=name).grid(row=row, column=0, sticky="w", padx=(0, 6))
        var = tk.IntVar(value=0)
        ttk.Label(parent, textvariable=var, width=6, anchor="e").grid(row=row, column=1)
        for col, (txt, delta) in enumerate(
                [("-10", -10), ("-1", -1), ("+1", 1), ("+10", 10)], start=2):
            ttk.Button(parent, text=txt, width=4,
                       command=lambda d=delta, v=var: self._nudge_trim(v, d)
                       ).grid(row=row, column=col, padx=2)
        return var

    def _nudge_trim(self, var, delta):
        var.set(max(-300, min(300, var.get() + delta)))
        self.write_trim()  # apply live so you see the readout move

    def _align_row(self, parent, name, col):
        ttk.Label(parent, text=name).grid(row=0, column=col * 2, sticky="e")
        var = tk.IntVar(value=0)
        ttk.Spinbox(parent, from_=-180, to=180, width=6, textvariable=var).grid(
            row=0, column=col * 2 + 1, padx=(2, 12))
        return var

    # ---- Sensors tab (live gyro graph) ---------------------------------- #
    GYRO_COLORS = ("#d22", "#2a2", "#26d")  # roll, pitch, yaw

    def _build_sensors_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Sensors")
        ttk.Label(tab, text="Live gyro (°/s). Sitting still it should hug the centre "
                            "line; spikes/noise hint at vibration or mounting issues.",
                  wraplength=560, foreground="#555").pack(anchor="w", pady=(0, 6))
        legend = ttk.Frame(tab)
        legend.pack(anchor="w", pady=(0, 4))
        for name, col in zip(("Roll", "Pitch", "Yaw"), self.GYRO_COLORS):
            tk.Label(legend, text="■", fg=col).pack(side="left")
            ttk.Label(legend, text=name).pack(side="left", padx=(0, 10))
        self.gyro_scale = tk.IntVar(value=500)  # ± full-scale °/s
        ttk.Label(legend, text="Scale ±°/s:").pack(side="left", padx=(10, 2))
        ttk.Combobox(legend, width=6, state="readonly", textvariable=self.gyro_scale,
                     values=[100, 250, 500, 1000, 2000]).pack(side="left")
        self.gyro_canvas = tk.Canvas(tab, height=260, bg="#111",
                                     highlightthickness=0)
        self.gyro_canvas.pack(fill="both", expand=True)
        self.gyro_val_lbl = ttk.Label(tab, text="R: 0   P: 0   Y: 0  °/s")
        self.gyro_val_lbl.pack(anchor="w", pady=(4, 0))

    def _draw_gyro(self):
        c = self.gyro_canvas
        c.delete("all")
        w = c.winfo_width() or 1
        h = c.winfo_height() or 1
        mid = h / 2
        full = max(1, self.gyro_scale.get())
        # centre + quarter grid lines
        c.create_line(0, mid, w, mid, fill="#444")
        for frac in (0.25, 0.75):
            c.create_line(0, h * frac, w, h * frac, fill="#222")
        n = self.GRAPH_SAMPLES
        step = w / (n - 1)
        for axis in range(3):
            pts = []
            for i, v in enumerate(self.gyro_hist[axis]):
                y = mid - (v / full) * mid
                y = max(0, min(h, y))
                pts.extend((i * step, y))
            if len(pts) >= 4:
                c.create_line(*pts, fill=self.GYRO_COLORS[axis], width=1)

    # ---- PID tab --------------------------------------------------------- #
    def _build_pid_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="PID Tuning")
        ttk.Label(tab, text="Flight stability gains. Higher P = sharper correction; "
                            "too high = oscillation. Change a little at a time.",
                  wraplength=560, foreground="#555").pack(anchor="w", pady=(0, 8))
        grid = ttk.Frame(tab)
        grid.pack(anchor="w")
        for c, h in enumerate(["", "P", "I", "D"]):
            ttk.Label(grid, text=h, width=6, anchor="center").grid(row=0, column=c)
        self.pid_vars = {}
        for r, axis in enumerate(["Roll", "Pitch", "Yaw"], start=1):
            ttk.Label(grid, text=axis, width=6).grid(row=r, column=0, sticky="w")
            row_vars = []
            for c in range(1, 4):
                v = tk.IntVar(value=0)
                ttk.Spinbox(grid, from_=0, to=255, width=6, textvariable=v).grid(
                    row=r, column=c, padx=3, pady=3)
                row_vars.append(v)
            self.pid_vars[axis] = row_vars
        btns = ttk.Frame(tab)
        btns.pack(anchor="w", pady=10)
        ttk.Button(btns, text="Read", command=self.read_pids).pack(side="left")
        ttk.Button(btns, text="Save", command=self.write_pids).pack(side="left", padx=6)
        ttk.Button(btns, text="💾 Save to flash",
                   command=self.save_eeprom).pack(side="left")

    # ---- Rates tab ------------------------------------------------------- #
    def _build_rates_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Rates / Sensitivity")
        ttk.Label(tab, text="Stick feel. RC Rate scales overall response; Super Rate "
                            "adds rotation rate near full stick; Expo softens the "
                            "centre for finer control.",
                  wraplength=560, foreground="#555").pack(anchor="w", pady=(0, 8))
        grid = ttk.Frame(tab)
        grid.pack(anchor="w")
        for c, h in enumerate(["", "RC Rate", "Super Rate", "Expo"]):
            ttk.Label(grid, text=h, width=10, anchor="center").grid(row=0, column=c)
        self.rate_vars = {}
        for r, axis in enumerate(["Roll", "Pitch", "Yaw"], start=1):
            ttk.Label(grid, text=axis, width=6).grid(row=r, column=0, sticky="w")
            row_vars = []
            for c in range(1, 4):
                v = tk.IntVar(value=0)
                ttk.Spinbox(grid, from_=0, to=255, width=8, textvariable=v).grid(
                    row=r, column=c, padx=3, pady=3)
                row_vars.append(v)
            self.rate_vars[axis] = row_vars
        self._rc_tuning_raw = None
        btns = ttk.Frame(tab)
        btns.pack(anchor="w", pady=10)
        ttk.Button(btns, text="Read", command=self.read_rates).pack(side="left")
        ttk.Button(btns, text="Save", command=self.write_rates).pack(side="left", padx=6)
        ttk.Button(btns, text="💾 Save to flash",
                   command=self.save_eeprom).pack(side="left")

    # ---- Motor tab ------------------------------------------------------- #
    def _build_motor_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Motors")
        warn = ttk.Label(tab, text="⚠  REMOVE ALL PROPELLERS before spinning motors.",
                         foreground="#b00", font=("TkDefaultFont", 11, "bold"))
        warn.pack(anchor="w")
        ttk.Checkbutton(tab, variable=self.motor_arm,
                        text="I understand — enable motor output",
                        command=self._on_arm_toggle).pack(anchor="w", pady=6)
        self.motor_vars = []
        for i in range(MOTOR_COUNT):
            row = ttk.Frame(tab)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"Motor {i + 1}", width=8).pack(side="left")
            v = tk.IntVar(value=MOTOR_MIN)
            scale = tk.Scale(row, from_=MOTOR_MIN, to=MOTOR_TEST_LIMIT,
                             orient="horizontal", length=320, variable=v,
                             command=lambda _v, idx=i: self._send_motors())
            scale.pack(side="left", padx=6)
            lbl = ttk.Label(row, textvariable=v, width=6)
            lbl.pack(side="left")
            self.motor_vars.append(v)
        ttk.Button(tab, text="■  STOP ALL", command=self.stop_motors).pack(
            anchor="w", pady=8)
        ttk.Label(tab, text="Spin each motor briefly and confirm direction & order. "
                            "Output is forced to minimum whenever the box above is "
                            "unchecked.", wraplength=520, foreground="#555").pack(anchor="w")

    def _on_arm_toggle(self):
        if not self.motor_arm.get():
            self.stop_motors()

    # -- status bar -------------------------------------------------------- #
    def _build_statusbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(6, 0))
        self.batt_lbl = ttk.Label(bar, text="Battery: --.- V")
        self.batt_lbl.pack(side="left")
        self.status_lbl = ttk.Label(bar, text="", foreground="#888")
        self.status_lbl.pack(side="right")

    def _flash(self, text, ok=True):
        self.status_lbl.config(text=text, foreground="#080" if ok else "#b00")

    # ===================================================================== #
    # MSP actions
    # ===================================================================== #
    # ---- PID ---- #
    def read_pids(self):
        p = self.msp.request(MSP_PID)
        if not p or len(p) < 9:
            return
        self._pid_raw = bytearray(p)
        for i, axis in enumerate(["Roll", "Pitch", "Yaw"]):
            for j in range(3):
                self.pid_vars[axis][j].set(p[i * 3 + j])
        self._flash("PIDs read")

    def write_pids(self):
        raw = bytearray(getattr(self, "_pid_raw", b"\x00" * (PID_ITEM_COUNT * 3)))
        if len(raw) < PID_ITEM_COUNT * 3:
            raw = bytearray(PID_ITEM_COUNT * 3)
        for i, axis in enumerate(["Roll", "Pitch", "Yaw"]):
            for j in range(3):
                raw[i * 3 + j] = self.pid_vars[axis][j].get() & 0xFF
        self.msp.request(MSP_SET_PID, bytes(raw))
        self._flash("PIDs sent")

    # ---- Rates ---- #
    def read_rates(self):
        p = self.msp.request(MSP_RC_TUNING)
        if not p or len(p) < 14:
            return
        self._rc_tuning_raw = bytearray(p)
        # offsets: 0 rcRate(roll) 1 expo(roll) 2/3/4 superRate r/p/y
        #          10 yawExpo 11 yawRate 12 pitchRate 13 pitchExpo
        self.rate_vars["Roll"][0].set(p[0])
        self.rate_vars["Roll"][1].set(p[2])
        self.rate_vars["Roll"][2].set(p[1])
        self.rate_vars["Pitch"][0].set(p[12])
        self.rate_vars["Pitch"][1].set(p[3])
        self.rate_vars["Pitch"][2].set(p[13])
        self.rate_vars["Yaw"][0].set(p[11])
        self.rate_vars["Yaw"][1].set(p[4])
        self.rate_vars["Yaw"][2].set(p[10])
        self._flash("Rates read")

    def write_rates(self):
        if self._rc_tuning_raw is None:
            p = self.msp.request(MSP_RC_TUNING)
            if not p:
                self._flash("read rates first", ok=False)
                return
            self._rc_tuning_raw = bytearray(p)
        raw = self._rc_tuning_raw
        raw[0] = self.rate_vars["Roll"][0].get() & 0xFF
        raw[2] = self.rate_vars["Roll"][1].get() & 0xFF
        raw[1] = self.rate_vars["Roll"][2].get() & 0xFF
        raw[12] = self.rate_vars["Pitch"][0].get() & 0xFF
        raw[3] = self.rate_vars["Pitch"][1].get() & 0xFF
        raw[13] = self.rate_vars["Pitch"][2].get() & 0xFF
        raw[11] = self.rate_vars["Yaw"][0].get() & 0xFF
        raw[4] = self.rate_vars["Yaw"][1].get() & 0xFF
        raw[10] = self.rate_vars["Yaw"][2].get() & 0xFF
        self.msp.request(MSP_SET_RC_TUNING, bytes(raw))
        self._flash("Rates sent")

    # ---- Calibration & alignment ---- #
    def calibrate_acc(self):
        if not self.msp.connected:
            return
        self.msp.send(MSP_ACC_CALIBRATION)
        self._flash("Calibrating — keep the drone still")

    def calibrate_mag(self):
        if not self.msp.connected:
            return
        self.msp.send(MSP_MAG_CALIBRATION)
        self._flash("Rotate the drone on all axes")

    def read_trim(self):
        p = self.msp.request(MSP_ACC_TRIM)
        if not p or len(p) < 4:
            return
        self.trim_pitch.set(s16(p, 0))
        self.trim_roll.set(s16(p, 2))
        self._flash("Trim read")

    def write_trim(self):
        data = struct.pack("<hh", self.trim_pitch.get(), self.trim_roll.get())
        self.msp.request(MSP_SET_ACC_TRIM, data)
        self._flash("Trim applied")

    def read_alignment(self):
        p = self.msp.request(MSP_BOARD_ALIGNMENT_CONFIG)
        if not p or len(p) < 6:
            return
        self.align_roll.set(s16(p, 0))
        self.align_pitch.set(s16(p, 2))
        self.align_yaw.set(s16(p, 4))
        self._flash("Alignment read")

    def autofill_alignment(self):
        roll, pitch, _ = self._last_att
        self.align_roll.set(round(roll))
        self.align_pitch.set(round(pitch))
        self._flash("Filled from tilt — Save, then verify readout ~0")

    def write_alignment(self):
        data = struct.pack("<hhh", self.align_roll.get(),
                           self.align_pitch.get(), self.align_yaw.get())
        self.msp.request(MSP_SET_BOARD_ALIGNMENT_CONFIG, data)
        self._flash("Alignment applied")

    def save_eeprom(self):
        if not self.msp.connected:
            return
        self.msp.request(MSP_EEPROM_WRITE, timeout=1.5)
        self._flash("Saved to flash ✓")

    # ---- Motors ---- #
    def _send_motors(self):
        if not self.msp.connected:
            return
        armed = self.motor_arm.get()
        vals = []
        for v in self.motor_vars:
            vals.append(v.get() if armed else MOTOR_MIN)
        # firmware reads OUTPUT_CHANNELS values; pad to 8 to match BF configurator
        while len(vals) < 8:
            vals.append(MOTOR_MIN)
        self.msp.send(MSP_SET_MOTOR, struct.pack("<8H", *vals))

    def stop_motors(self):
        for v in self.motor_vars:
            v.set(MOTOR_MIN)
        self._send_motors()
        self._flash("Motors stopped")

    # ===================================================================== #
    # live polling
    # ===================================================================== #
    def _poll(self):
        if self.msp.connected:
            att = self.msp.request(MSP_ATTITUDE, timeout=0.15)
            if att and len(att) >= 6:
                roll, pitch, yaw = s16(att, 0) / 10, s16(att, 2) / 10, s16(att, 4)
                self._last_att = (roll, pitch, yaw)
                self.roll_lbl.config(text=f"{roll:.1f}°")
                self.pitch_lbl.config(text=f"{pitch:.1f}°")
                self.yaw_lbl.config(text=f"{yaw}°")
            imu = self.msp.request(MSP_RAW_IMU, timeout=0.15)
            if imu and len(imu) >= 12:
                gx, gy, gz = s16(imu, 6), s16(imu, 8), s16(imu, 10)
                self.gyro_hist[0].append(gx)
                self.gyro_hist[1].append(gy)
                self.gyro_hist[2].append(gz)
                self.gyro_val_lbl.config(text=f"R: {gx}   P: {gy}   Y: {gz}  °/s")
                self._draw_gyro()
            ana = self.msp.request(MSP_ANALOG, timeout=0.15)
            if ana and len(ana) >= 9:
                self.batt_lbl.config(text=f"Battery: {u16(ana, 7) / 100:.2f} V")
        self.root.after(self.POLL_MS, self._poll)

    def _on_close(self):
        try:
            if self.msp.connected:
                self.stop_motors()
                self.msp.disconnect()
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    root.title("ESP-FC Configurator")
    root.minsize(620, 560)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
