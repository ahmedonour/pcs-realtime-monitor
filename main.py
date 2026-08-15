#!/usr/bin/env python3
"""PCS Realtime Monitor.

A clean CustomTkinter dashboard:
  - Login screen first; after login the dashboard appears.
  - Photovoltaic SSE stream -> one card per device (PV1..PV5) with output power.
  - Battery SOC for every BMS device (extension's /v1/history-data poll).
"""

import csv
import json
import shutil
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
import requests
import tkinter as tk
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def resource_path(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


ICON_FILE = resource_path("icon.png")

DEFAULT_BASE_URL = "http://192.168.0.123"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "aiWatt+0"
PV_QUERY = "purpose=2&pageSize=12&page=1"
BMS_DEVICE_IDS = [2, 3]
BMS_INTERVAL = 5.0  # seconds (matches the extension)
POWER_GROUP_INTERVAL = 1.0  # seconds (power group is requested every 1s)
POWER_GROUP_DEVICES = ["GateMeter", "ESS1 master", "ESS2 slave"]
FAULT_INTERVAL = 1.0  # seconds (active faults are polled every 1s)
FAULT_PAGE_SIZE = 50
RECONNECT_MAX_BACKOFF = 30.0  # seconds between retries while disconnected

# --- automation ---
AUTOMATION_INTERVAL = 30.0  # seconds between rule evaluations
AUTOMATION_STEP = 5.0  # kW step when nudging the PV power
PV_POWER_MIN = 0.0
PV_POWER_MAX = 500.0
HOT_START_HOUR = 10  # rule 2 window 10:00..18:00
HOT_END_HOUR = 18
HOT_TEMP = 35.0  # degrees Celsius
SOC_HIGH = 95.0  # any BMS >= 95% triggers rule 3 discharge
SOC_RECOVER = 85.0  # any BMS <= 85% triggers recovery (charge)
ESS_DISCHARGE_RANGE = (-25.0, -15.0)  # target ESS PCS power when SOC high
ESS_CHARGE_RANGE = (10.0, 20.0)  # target ESS PCS power during hot window
LOG_DIR = Path.home() / ".pcs-realtime-monitor" / "logs"
WEATHER_CACHE_SECONDS = 600  # refetch temperature at most every 10 min
LOG_FIELDS = ["timestamp", "rule", "action", "gate_kw", "ess1_kw", "ess2_kw",
              "pv_current_kw", "pv_target_kw", "temp_c", "soc", "applied"]

SEQUENCE_STEPS = [
    ("pcs_device_stop", "Stop device"),
    ("pcs_fault_reset", "Fault reset"),
    ("pcs_system_operate_reset", "System operate reset"),
    ("pcs_device_startup", "Device startup"),
]
PV_CHARGE_DEVICE_IDS = [1, 2, 3, 4, 6]

COLOR_GREEN = "#4cc38a"
COLOR_RED = "#e65454"
COLOR_ORANGE = "#e6a33c"
COLOR_GRAY = "#8a8aa3"
COLOR_LIGHT_GREEN = "#a8f0c0"
COLOR_INFO = "#54a0e8"

THEMES = {
    "dark": {
        "panel": "#1c1d30",
        "card": "#1f2035",
        "separator": "#2c2d45",
        "button": "#3a3a52",
        "button_hover": "#4a4a66",
        "text": "#c6c6dd",
        "accent_hover": "#3aa372",
        "danger_hover": "#c24444",
    },
    "light": {
        "panel": "#eef1f8",
        "card": "#ffffff",
        "separator": "#d5dae6",
        "button": "#dfe4f0",
        "button_hover": "#ccd3e6",
        "text": "#232a3a",
        "accent_hover": "#3aa372",
        "danger_hover": "#c24444",
    },
}

BMS_STATUS_MAP = {1: "Standby", 2: "Shutdown", 3: "Charging", 4: "Discharging"}


def deep_find(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = deep_find(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = deep_find(value, key)
            if found is not None:
                return found
    return None


class PcsRealtimeMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PCS Realtime Monitor")
        self.geometry("1180x660")
        self.minsize(1000, 560)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.session = requests.Session()
        self.token = None
        self.settings = {
            "base_url": DEFAULT_BASE_URL,
            "username": DEFAULT_USERNAME,
            "password": DEFAULT_PASSWORD,
            "device_ids": BMS_DEVICE_IDS,
        }
        self.current_view = "login"

        self.lock = threading.Lock()
        self.pv = {"devices": {}, "ts": None, "error": None}
        self.bms = {"devices": {}, "ts": None, "error": None}
        self.power_group = {"devices": {}, "ts": None, "error": None}
        self.faults = {"items": [], "ts": None, "error": None}
        self._faults_rendered = None
        self.stop_event = threading.Event()
        self.workers = []
        self.login_lock = threading.Lock()
        self.conn = {"status": "idle", "error": None}
        self.tray_icon = None
        self.run_in_background = tk.BooleanVar(value=True)

        self.sequence_running = False
        self.sequence_status = {}

        self.automation = {"enabled": False, "pv_power": None, "last_action": None}
        self.auto_settings = {
            "interval": AUTOMATION_INTERVAL,
            "step": AUTOMATION_STEP,
            "pv_min": PV_POWER_MIN,
            "pv_max": PV_POWER_MAX,
            "hot_temp": HOT_TEMP,
            "soc_high": SOC_HIGH,
            "soc_recover": SOC_RECOVER,
        }
        self._automation_ticking = False
        self.log_dir = LOG_DIR
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.log_dir = Path.cwd()
        self.weather_cache = None
        self.location_cache = None

        self.pv_cards = {}
        self.bms_cards = {}
        self.power_group_cards = {}
        self.pv_rendered = []
        self.bms_rendered = []
        self.power_group_rendered = []

        self.btn_seq_both = None
        self.btn_seq_bms = {}
        self.lbl_seq_status = None
        self.ent_pv_power = None
        self.btn_pv_power = None
        self.lbl_pv_power_status = None
        self.lbl_pg_ts = None
        self.console = None
        self.btn_automation = None
        self.btn_download_log = None
        self.lbl_weather = None
        self.lbl_clock = None
        self.lbl_bottom_weather = None
        self.lbl_bottom_location = None
        self.lbl_bottom_clock = None
        self.btn_settings = None
        self.btn_theme = None
        self.fault_scroll = None
        self.lbl_fault_ts = None

        self.theme = "dark"
        self.colors = THEMES["dark"]

        self._window_icon()
        self.build_login()
        self.build_dashboard()
        self.show_login()

        self.after(200, self.refresh_ui)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        if sys.platform == "darwin":
            try:
                self.createcommand("tk::mac::Quit", self.on_quit_command)
                self.createcommand("tk::mac::ReopenApplication", self.show_window)
            except Exception:
                pass
        self._setup_tray()

    # ------------------------------------------------------------ window icon
    def _window_icon(self):
        try:
            if ICON_FILE.exists():
                self._icon_image = tk.PhotoImage(file=str(ICON_FILE))
                self.iconphoto(True, self._icon_image)
        except Exception:
            pass

    # ------------------------------------------------------------ system tray / background
    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image as PILImage
        except Exception:
            self.tray_icon = None
            return
        try:
            image = PILImage.open(str(ICON_FILE)) if ICON_FILE.exists() else None
        except Exception:
            image = None
        if image is None:
            image = PILImage.new("RGB", (64, 64), (76, 195, 138))
        menu = pystray.Menu(
            pystray.MenuItem("Show dashboard", self._tray_show, default=True),
            pystray.MenuItem("Quit PCS Monitor", self._tray_quit),
        )
        self.tray_icon = pystray.Icon("pcs_realtime_monitor", image, "PCS Realtime Monitor", menu)
        try:
            self.tray_icon.run_detached()
        except Exception:
            self.tray_icon = None

    def _tray_show(self, icon, item):
        self.after(0, self.show_window)

    def _tray_quit(self, icon, item):
        self.after(0, self._quit)

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_close(self):
        self._handle_quit_or_background()

    def on_quit_command(self):
        self._handle_quit_or_background()

    def _handle_quit_or_background(self):
        if not self.winfo_viewable():
            self._quit()
        elif self.run_in_background.get() and self.tray_icon is not None:
            self.withdraw()
            try:
                self.tray_icon.notify(
                    "PCS Monitor is still running in the background. Use the menu bar icon to open it again.",
                    "PCS Realtime Monitor",
                )
            except Exception:
                pass
        else:
            self._quit()

    def _quit(self):
        self.stop_polling()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    # ------------------------------------------------------------ login view
    def build_login(self):
        self.login_view = ctk.CTkFrame(self, fg_color="transparent")
        self.login_view.grid(row=0, column=0, sticky="nsew")
        self.login_view.grid_columnconfigure(0, weight=1)
        self.login_view.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(self.login_view, corner_radius=16, width=400, height=470)
        card.grid(row=0, column=0, padx=30, pady=30)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        logo = None
        try:
            from PIL import Image as PILImage
            logo = ctk.CTkImage(PILImage.open(str(ICON_FILE)), size=(64, 64))
        except Exception:
            pass
        ctk.CTkLabel(card, text="", image=logo).grid(row=0, column=0, pady=(28, 4))

        ctk.CTkLabel(card, text="PCS Realtime Monitor", font=ctk.CTkFont(size=20, weight="bold")).grid(row=1, column=0, pady=(0, 2))
        ctk.CTkLabel(card, text="Sign in to view the live dashboard", font=ctk.CTkFont(size=12), text_color=COLOR_GRAY).grid(row=2, column=0, pady=(0, 18))

        self.ent_url = self._field(card, 3, "Server URL", self.settings["base_url"])
        self.ent_user = self._field(card, 5, "Username", self.settings["username"])
        self.ent_pass = self._field(card, 7, "Password", self.settings["password"], show="*")

        self.lbl_login_msg = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color=COLOR_RED)
        self.lbl_login_msg.grid(row=9, column=0, pady=(6, 0))

        self.btn_login = ctk.CTkButton(card, text="Login", height=38, corner_radius=8, command=self.login_action)
        self.btn_login.grid(row=10, column=0, padx=30, pady=(10, 28), sticky="ew")

    def _field(self, parent, row, label, value, show=None):
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=10), text_color=COLOR_GRAY).grid(
            row=row, column=0, sticky="w", padx=30, pady=(6, 0))
        ent = ctk.CTkEntry(parent, show=show or "", height=34, corner_radius=8)
        ent.insert(0, value)
        ent.grid(row=row + 1, column=0, sticky="ew", padx=30, pady=(2, 0))
        return ent

    def show_login(self):
        self.current_view = "login"
        self.stop_polling()
        self.dashboard_view.grid_remove()
        self.login_view.grid()

    def login_action(self):
        self.read_settings()
        self.btn_login.configure(state="disabled", text="Logging in...")
        self.lbl_login_msg.configure(text="")
        threading.Thread(target=self._login_worker, daemon=True).start()

    def _login_worker(self):
        try:
            self.login()
            self.after(0, self._login_ok)
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self._login_fail(msg))

    def _login_ok(self):
        self.btn_login.configure(state="normal", text="Login")
        self.lbl_login_msg.configure(text="")
        self.show_dashboard()
        self.start_polling()

    def _login_fail(self, msg):
        self.btn_login.configure(state="normal", text="Login")
        self.lbl_login_msg.configure(text=f"Login failed: {msg}", text_color=COLOR_RED)

    # ------------------------------------------------------------ dashboard view
    def build_dashboard(self):
        self.dashboard_view = ctk.CTkFrame(self, fg_color="transparent")
        self.dashboard_view.grid(row=0, column=0, sticky="nsew")
        self.dashboard_view.grid_columnconfigure(0, weight=1)
        self.dashboard_view.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(8, 4))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="PCS Realtime Monitor", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.lbl_conn = ctk.CTkLabel(header, text="connected", font=ctk.CTkFont(size=11), text_color=COLOR_GREEN)
        self.lbl_conn.pack(side="left", padx=12)
        self.btn_logout = ctk.CTkButton(header, text="Log out", width=80, height=28, corner_radius=8,
                                        fg_color=self.colors["button"], hover_color=self.colors["button_hover"],
                                        command=self.logout)
        self.btn_logout.pack(side="right")

        self.content = ctk.CTkScrollableFrame(self.dashboard_view, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(2, 0))
        self.content.grid_columnconfigure(0, weight=1)

        self.build_control_section()

        # --- bottom status bar ---
        c = self.colors
        bar = ctk.CTkFrame(self.dashboard_view, fg_color=c["panel"], corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self.lbl_bottom_weather = ctk.CTkLabel(bar, text="⛅ Weather: --", font=ctk.CTkFont(size=11), text_color=c["text"])
        self.lbl_bottom_weather.pack(side="left", padx=(16, 8), pady=6)
        self.lbl_bottom_location = ctk.CTkLabel(bar, text="📍 Location: --", font=ctk.CTkFont(size=11), text_color=c["text"])
        self.lbl_bottom_location.pack(side="left", padx=8, pady=6)
        self.btn_settings = ctk.CTkButton(bar, text="⚙", width=34, height=24, corner_radius=6,
                                          fg_color=c["button"], hover_color=c["button_hover"],
                                          command=self.open_settings)
        self.btn_settings.pack(side="right", padx=(0, 8), pady=6)
        self.btn_theme = ctk.CTkButton(bar, text="☀" if self.theme == "light" else "🌙", width=34, height=24,
                                       corner_radius=6, fg_color=c["button"], hover_color=c["button_hover"],
                                       command=self.toggle_theme)
        self.btn_theme.pack(side="right", padx=(0, 8), pady=6)
        self.lbl_bottom_clock = ctk.CTkLabel(bar, text="", font=ctk.CTkFont(size=11), text_color=c["text"])
        self.lbl_bottom_clock.pack(side="right", padx=16, pady=6)

        # Power group (left) + Photovoltaic (right) side by side
        middle = ctk.CTkFrame(self.content, fg_color="transparent")
        middle.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        middle.grid_columnconfigure(0, weight=1)
        middle.grid_columnconfigure(1, weight=1)

        # Power group section (GateMeter, ESS1 master, ESS2 slave)
        pg_col = ctk.CTkFrame(middle, fg_color="transparent")
        pg_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        pg_head = ctk.CTkFrame(pg_col, fg_color="transparent")
        pg_head.pack(fill="x")
        pg_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pg_head, text="POWER GROUP", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(side="left")
        self.lbl_pg_ts = ctk.CTkLabel(pg_head, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_pg_ts.pack(side="right")

        self.power_group_container = ctk.CTkFrame(pg_col, fg_color="transparent")
        self.power_group_container.pack(fill="x", pady=(4, 0))
        self.power_group_container.bind(
            "<Configure>", lambda e: self._flow_cards(self.power_group_container,
                                                      [c["card"] for c in self.power_group_cards.values()]))

        # Photovoltaic section
        pv_col = ctk.CTkFrame(middle, fg_color="transparent")
        pv_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        pv_head = ctk.CTkFrame(pv_col, fg_color="transparent")
        pv_head.pack(fill="x")
        pv_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pv_head, text="PHOTOVOLTAIC DEVICES", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(side="left")
        self.lbl_pv_ts = ctk.CTkLabel(pv_head, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_pv_ts.pack(side="right")

        self.pv_container = ctk.CTkFrame(pv_col, fg_color="transparent")
        self.pv_container.pack(fill="x", pady=(4, 0))
        self.pv_container.bind(
            "<Configure>", lambda e: self._flow_cards(self.pv_container,
                                                      [c["card"] for c in self.pv_cards.values()]))

        # Battery + Faults section
        bms_head = ctk.CTkFrame(self.content, fg_color="transparent")
        bms_head.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        bms_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(bms_head, text="BATTERY (BMS)", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(side="left")
        self.lbl_bms_ts = ctk.CTkLabel(bms_head, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_bms_ts.pack(side="right")

        bms_row = ctk.CTkFrame(self.content, fg_color="transparent")
        bms_row.grid(row=3, column=0, sticky="ew", pady=(4, 2))
        bms_row.grid_columnconfigure(1, weight=1)

        self.bms_container = ctk.CTkFrame(bms_row, fg_color="transparent")
        self.bms_container.grid(row=0, column=0, sticky="nw", padx=(0, 12))
        self.bms_container.bind(
            "<Configure>", lambda e: self._flow_cards(self.bms_container,
                                                      [c["card"] for c in self.bms_cards.values()]))

        fault_col = ctk.CTkFrame(bms_row, fg_color="transparent")
        fault_col.grid(row=0, column=1, sticky="nsew")
        fault_head = ctk.CTkFrame(fault_col, fg_color="transparent")
        fault_head.pack(fill="x")
        fault_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(fault_head, text="FAULTS", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_RED).pack(side="left")
        self.lbl_fault_ts = ctk.CTkLabel(fault_head, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_fault_ts.pack(side="right")

        self.fault_scroll = ctk.CTkScrollableFrame(fault_col, height=230, corner_radius=12,
                                                   fg_color=self.colors["panel"])
        self.fault_scroll.pack(fill="both", expand=True, pady=(4, 0))

    def build_control_section(self):
        c = self.colors
        ctl = ctk.CTkFrame(self.content, corner_radius=12, fg_color=c["panel"])
        ctl.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctl.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(ctl, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(left, text="CONTROL", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(anchor="w", padx=16, pady=(8, 2))

        seq_row = ctk.CTkFrame(left, fg_color="transparent")
        seq_row.pack(fill="x", padx=16, pady=(0, 2))
        ctk.CTkLabel(seq_row, text="Run sequence", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 12))
        self.btn_seq_both = ctk.CTkButton(seq_row, text="Both batteries", width=110, height=26, corner_radius=8,
                                          command=lambda: self.start_sequence(list(self.settings["device_ids"])))
        self.btn_seq_both.pack(side="left", padx=(0, 8))
        self.btn_seq_bms = {}
        for did in self.settings["device_ids"]:
            btn = ctk.CTkButton(seq_row, text=f"BMS {did}", width=80, height=26, corner_radius=8,
                                command=lambda d=did: self.start_sequence([d]))
            btn.pack(side="left", padx=(0, 8))
            self.btn_seq_bms[did] = btn

        self.lbl_seq_status = ctk.CTkLabel(left, text="idle", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_seq_status.pack(anchor="w", padx=16, pady=(0, 2))

        ctk.CTkFrame(left, height=1, fg_color=c["separator"]).pack(fill="x", padx=16, pady=(0, 4))

        pv_row = ctk.CTkFrame(left, fg_color="transparent")
        pv_row.pack(fill="x", padx=16, pady=(0, 2))
        ctk.CTkLabel(pv_row, text="PV power (run_power)", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 12))
        self.ent_pv_power = ctk.CTkEntry(pv_row, width=100, height=26, corner_radius=8)
        self.ent_pv_power.insert(0, "100")
        self.ent_pv_power.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(pv_row, text="kW", font=ctk.CTkFont(size=11), text_color=COLOR_GRAY).pack(side="left", padx=(0, 12))
        self.btn_pv_power = ctk.CTkButton(pv_row, text="Apply", width=80, height=26, corner_radius=8,
                                          command=self.apply_pv_power)
        self.btn_pv_power.pack(side="left")

        self.lbl_pv_power_status = ctk.CTkLabel(left, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_pv_power_status.pack(anchor="w", padx=16, pady=(0, 2))

        ctk.CTkFrame(left, height=1, fg_color=c["separator"]).pack(fill="x", padx=16, pady=(0, 4))

        auto_row = ctk.CTkFrame(left, fg_color="transparent")
        auto_row.pack(fill="x", padx=16, pady=(0, 2))
        ctk.CTkLabel(auto_row, text="Automation", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 12))
        self.btn_automation = ctk.CTkButton(auto_row, text="Start Automation", width=150, height=28, corner_radius=8,
                                            fg_color=COLOR_GREEN, hover_color=c["accent_hover"],
                                            command=self.toggle_automation)
        self.btn_automation.pack(side="left", padx=(0, 8))
        self.btn_download_log = ctk.CTkButton(auto_row, text="Download Log", width=120, height=28, corner_radius=8,
                                              fg_color=c["button"], hover_color=c["button_hover"],
                                              command=self.download_log)
        self.btn_download_log.pack(side="left")

        self.chk_background = ctk.CTkCheckBox(
            left, text="Run in background when the window is closed",
            variable=self.run_in_background, text_color=COLOR_GRAY,
            font=ctk.CTkFont(size=10), fg_color=COLOR_GREEN, hover_color=c["accent_hover"],
        )
        self.chk_background.pack(anchor="w", padx=16, pady=(6, 6))

    def show_dashboard(self):
        self.current_view = "dashboard"
        self.login_view.grid_remove()
        self.dashboard_view.grid()

    def logout(self):
        self.token = None
        self.sequence_running = False
        self.sequence_status = {}
        self.automation["enabled"] = False
        if self.btn_automation is not None:
            self.btn_automation.configure(
                text="Start Automation", fg_color=COLOR_GREEN, hover_color=self.colors["accent_hover"])
        self.show_login()
        with self.lock:
            self.pv = {"devices": {}, "ts": None, "error": None}
            self.bms = {"devices": {}, "ts": None, "error": None}
            self.power_group = {"devices": {}, "ts": None, "error": None}
            self.faults = {"items": [], "ts": None, "error": None}
            self.conn = {"status": "idle", "error": None}

    # ------------------------------------------------------------ cards
    def _flow_cards(self, parent, card_widgets, gap=12):
        if getattr(self, "_flowing", False):
            return
        self._flowing = True
        try:
            parent.update_idletasks()
            available = parent.winfo_width()
            if available < 40:
                available = 640
            rows = []
            row = []
            row_w = 0
            for w in card_widgets:
                try:
                    req = w.winfo_reqwidth()
                except Exception:
                    req = 200
                if row and row_w + gap + req > available:
                    rows.append(row)
                    row = [w]
                    row_w = req
                else:
                    row.append(w)
                    row_w += (gap if len(row) > 1 else 0) + req
            if row:
                rows.append(row)
            for r, row_items in enumerate(rows):
                for c, w in enumerate(row_items):
                    w.grid(row=r, column=c, sticky="w", padx=gap // 2, pady=4)
        finally:
            self._flowing = False

    def render_power_group_cards(self, names):
        for w in self.power_group_container.winfo_children():
            w.destroy()
        self.power_group_cards = {}
        for name in names:
            card = ctk.CTkFrame(self.power_group_container, corner_radius=12, fg_color=self.colors["card"])
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_INFO).pack(anchor="w", padx=14, pady=(8, 2))
            value = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_GREEN)
            value.pack(anchor="w", padx=14)
            caption = ctk.CTkLabel(card, text="total active power (kW)", font=ctk.CTkFont(size=10),
                                   text_color=COLOR_GRAY)
            caption.pack(anchor="w", padx=14, pady=(2, 8))
            self.power_group_cards[name] = {"card": card, "value": value, "caption": caption}
        self.power_group_rendered = list(names)
        self._flow_cards(self.power_group_container, [c["card"] for c in self.power_group_cards.values()])

    def render_pv_cards(self, names):
        for w in self.pv_container.winfo_children():
            w.destroy()
        self.pv_cards = {}
        for name in names:
            card = ctk.CTkFrame(self.pv_container, corner_radius=12, fg_color=self.colors["card"])
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_INFO).pack(anchor="w", padx=14, pady=(8, 2))
            value = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_GREEN)
            value.pack(anchor="w", padx=14)
            ctk.CTkLabel(card, text="kilowatts (kW)", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY).pack(anchor="w", padx=14, pady=(2, 8))
            self.pv_cards[name] = {"card": card, "value": value}
        self.pv_rendered = list(names)
        self._flow_cards(self.pv_container, [c["card"] for c in self.pv_cards.values()])

    def render_bms_cards(self, names):
        for w in self.bms_container.winfo_children():
            w.destroy()
        self.bms_cards = {}
        for name in names:
            card = ctk.CTkFrame(self.bms_container, corner_radius=12, fg_color=self.colors["card"])
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_INFO).pack(anchor="w", padx=14, pady=(8, 2))
            value = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_GREEN)
            value.pack(anchor="w", padx=14)
            progress = ctk.CTkProgressBar(card, height=6, corner_radius=3, progress_color=COLOR_GREEN)
            progress.set(0)
            progress.pack(fill="x", padx=14, pady=(6, 2))
            status = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
            status.pack(anchor="w", padx=14, pady=(0, 8))
            self.bms_cards[name] = {"card": card, "value": value, "progress": progress, "status": status}
        self.bms_rendered = list(names)
        self._flow_cards(self.bms_container, [c["card"] for c in self.bms_cards.values()])

    # ------------------------------------------------------------ api
    def read_settings(self):
        self.settings.update({
            "base_url": self.ent_url.get().strip().rstrip("/"),
            "username": self.ent_user.get().strip(),
            "password": self.ent_pass.get(),
        })

    def login(self):
        with self.login_lock:
            if self.token:
                return self.token
            url = f"{self.settings['base_url']}/v1/user/login"
            resp = self.session.post(
                url,
                json={"username": self.settings["username"], "password": self.settings["password"]},
                timeout=(5, 10),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") not in (0, None):
                raise RuntimeError(f"code={data.get('code')} message={data.get('message')}")
            self.token = data["data"]["token"]
            return self.token

    def _headers(self, sse=False):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json;charset=utf-8",
        }
        if sse:
            headers["Accept"] = "text/event-stream"
            headers["Cache-Control"] = "no-cache"
        return headers

    def _set_conn(self, status, error=None):
        with self.lock:
            self.conn = {"status": status, "error": error}

    @staticmethod
    def _is_auth_error(exc):
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            if exc.response.status_code in (401, 403):
                return True
        msg = str(exc).lower()
        return any(k in msg for k in ("401", "403", "unauthorized", "token expired"))

    # ------------------------------------------------------------ control
    def _api_patch(self, path, body):
        if not self.token:
            self.login()
        url = f"{self.settings['base_url']}{path}"
        resp = self.session.patch(url, headers=self._headers(), json=body, timeout=(5, 10))
        if resp.status_code in (401, 403):
            self.token = None
            self.login()
            resp = self.session.patch(url, headers=self._headers(), json=body, timeout=(5, 10))
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") not in (0, None):
            raise RuntimeError(f"code={data.get('code')} message={data.get('message')}")
        return data

    def start_sequence(self, device_ids):
        if self.sequence_running or not device_ids:
            return
        self.sequence_running = True
        with self.lock:
            self.sequence_status = {did: {"step": "queued", "error": None, "done": False} for did in device_ids}
        threading.Thread(target=self._sequence_worker, args=(list(device_ids),), daemon=True).start()

    def _sequence_worker(self, device_ids):
        try:
            if not self.token:
                self.login()
            for did in device_ids:
                for field, label in SEQUENCE_STEPS:
                    if not self.sequence_running:
                        return
                    with self.lock:
                        self.sequence_status[did] = {"step": label, "error": None, "done": False}
                    try:
                        self._api_patch(f"/v1/pcs-control/{did}", {field: 1})
                    except Exception as e:
                        with self.lock:
                            self.sequence_status[did] = {"step": label, "error": str(e), "done": False}
                        return
                with self.lock:
                    self.sequence_status[did] = {"step": "complete", "error": None, "done": True}
        except Exception as e:
            with self.lock:
                for did in device_ids:
                    if not self.sequence_status.get(did, {}).get("done"):
                        self.sequence_status[did] = {"step": "error", "error": str(e), "done": False}
        finally:
            self.sequence_running = False

    def apply_pv_power(self):
        raw = self.ent_pv_power.get().strip()
        try:
            run_power = float(raw)
        except ValueError:
            self.lbl_pv_power_status.configure(text="Invalid number", text_color=COLOR_RED)
            return
        self.btn_pv_power.configure(state="disabled", text="Applying...")
        threading.Thread(target=self._pv_power_worker, args=(run_power,), daemon=True).start()

    def _apply_pv_power_sync(self, run_power):
        if not self.token:
            self.login()
        body = {
            "status": 1,
            "month": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "week_day": [0, 1, 2, 3, 4, 5, 6],
            "device_ids": PV_CHARGE_DEVICE_IDS,
            "settings": [{
                "start_hour": 0,
                "start_minute": 0,
                "end_hour": 23,
                "end_minute": 59,
                "cdc_enable_mode": 2,
                "run_power": run_power,
            }],
            "charge_type": 1,
            "mode": 2,
        }
        self._api_patch("/v1/photovoltaic-charge/2", body)

    def _pv_power_worker(self, run_power):
        try:
            self._apply_pv_power_sync(run_power)
            self.after(0, lambda: self.lbl_pv_power_status.configure(
                text=f"PV power set to {run_power} kW", text_color=COLOR_GREEN))
            self.after(0, lambda: self._set_pv_entry(run_power))
        except Exception as e:
            self.after(0, lambda: self.lbl_pv_power_status.configure(
                text=f"Failed: {str(e)[:60]}", text_color=COLOR_RED))
        finally:
            self.after(0, lambda: self.btn_pv_power.configure(state="normal", text="Apply"))

    # ------------------------------------------------------------ polling
    def start_polling(self):
        self.stop_event.clear()
        if self.workers:
            return
        for target in (self.power_group_worker, self.pv_worker, self.bms_worker, self.fault_worker, self.automation_worker):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            self.workers.append(t)

    def stop_polling(self):
        self.stop_event.set()
        self.workers = []

    def power_group_worker(self):
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                if not self.token:
                    self.login()
                url = f"{self.settings['base_url']}/v1/sse/power-group"
                headers = self._headers(sse=True)
                meters = {}
                pcs = {}
                for event in self.read_sse_events(url, headers, timeout=POWER_GROUP_INTERVAL):
                    self.collect_power_group_event(event, meters, pcs)
                devices = self.merge_power_group(meters, pcs)
                if devices:
                    with self.lock:
                        self.power_group = {"devices": devices, "ts": datetime.now().strftime("%H:%M:%S"), "error": None}
                    self._set_conn("connected")
                    backoff = 1.0
            except Exception as e:
                with self.lock:
                    self.power_group["error"] = str(e)
                self._set_conn("error", str(e))
                if self._is_auth_error(e):
                    self.token = None
                backoff = min(backoff * 2, RECONNECT_MAX_BACKOFF)
            self.stop_event.wait(backoff if backoff != 1.0 else POWER_GROUP_INTERVAL)

    @staticmethod
    def collect_power_group_event(event, meters, pcs):
        items = event.get("list") if isinstance(event, dict) else event
        if not isinstance(items, list):
            items = [event]
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            device = item.get("device") or {}
            if item.get("type") == 2:
                pcs_val = (device.get("pcs") or {}).get("pcs_total_active_power")
                pcs[name] = pcs_val
            elif item.get("type") == 1:
                meters[name] = device.get("total_active")

    @staticmethod
    def merge_power_group(meters, pcs):
        devices = {name: {"apparent_power": value, "pcs_apparent_power": None} for name, value in meters.items()}
        for name, value in pcs.items():
            if name in devices:
                devices[name]["pcs_apparent_power"] = value
            else:
                devices[name] = {"apparent_power": None, "pcs_apparent_power": value}
        return devices

    def pv_worker(self):
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                if not self.token:
                    self.login()
                url = f"{self.settings['base_url']}/v1/sse/photovoltaic?{PV_QUERY}"
                headers = self._headers(sse=True)
                devices = {}
                for event in self.read_sse_events(url, headers):
                    devices.update(self.parse_pv_event(event))
                if devices:
                    with self.lock:
                        self.pv = {"devices": devices, "ts": datetime.now().strftime("%H:%M:%S"), "error": None}
                    self._set_conn("connected")
                    backoff = 1.0
            except Exception as e:
                with self.lock:
                    self.pv["error"] = str(e)
                self._set_conn("error", str(e))
                if self._is_auth_error(e):
                    self.token = None
                backoff = min(backoff * 2, RECONNECT_MAX_BACKOFF)
            self.stop_event.wait(backoff)

    def read_sse_events(self, url, headers, timeout=8.0, max_events=100):
        resp = self.session.get(url, headers=headers, stream=True, timeout=(10, None))
        try:
            if not resp.ok:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            try:
                resp.raw.connection.sock.settimeout(timeout)
            except Exception:
                pass
            events = []
            buffer = ""
            deadline = time.time() + timeout
            try:
                for raw in resp.iter_lines(decode_unicode=True):
                    if time.time() > deadline:
                        break
                    if raw is None:
                        continue
                    buffer += raw.rstrip("\r") + "\n"
                    while "\n\n" in buffer:
                        block, _, buffer = buffer.partition("\n\n")
                        for line in block.split("\n"):
                            if line.startswith("data:"):
                                payload = line[5:].strip()
                                if payload:
                                    try:
                                        events.append(json.loads(payload))
                                    except Exception:
                                        pass
                        if len(events) >= max_events:
                            return events
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, socket.timeout):
                pass
            return events
        finally:
            resp.close()

    @staticmethod
    def parse_pv_event(event):
        devices = {}
        if not isinstance(event, dict):
            return devices
        lst = event.get("list")
        if isinstance(lst, list):
            for idx, item in enumerate(lst):
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or f"PV {item.get('photovoltaicId', idx + 1)}"
                power = deep_find(item, "alternating_current_output_power")
                if power is None:
                    power = deep_find(item, "alternatingCurrentOutputPower")
                devices[name] = power
            return devices
        name = event.get("name")
        power = None
        data = event.get("data")
        if isinstance(data, dict):
            power = data.get("alternating_current_output_power", data.get("alternatingCurrentOutputPower"))
        if power is None:
            power = deep_find(event, "alternating_current_output_power")
        if power is None:
            power = deep_find(event, "alternatingCurrentOutputPower")
        if name:
            devices[name] = power
        return devices

    def bms_worker(self):
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                if not self.token:
                    self.login()
                devices = {}
                for did in self.settings.get("device_ids", BMS_DEVICE_IDS):
                    url = f"{self.settings['base_url']}/v1/history-data?page=1&page-size=1"
                    resp = self.session.post(
                        url,
                        headers=self._headers(),
                        json={"device_id": did, "device_type": 2, "fields": ["bms_running_status", "bms_soc"]},
                        timeout=(5, 10),
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    items = (data.get("data") or {}).get("list") or []
                    if items:
                        latest = items[0]
                        devices[f"BMS {did}"] = {
                            "soc": latest.get("bms_soc"),
                            "status": latest.get("bms_running_status"),
                        }
                if devices:
                    with self.lock:
                        self.bms = {"devices": devices, "ts": datetime.now().strftime("%H:%M:%S"), "error": None}
                    self._set_conn("connected")
                    backoff = 1.0
            except Exception as e:
                with self.lock:
                    self.bms = {"devices": {}, "ts": None, "error": str(e)}
                self._set_conn("error", str(e))
                if self._is_auth_error(e):
                    self.token = None
                backoff = min(backoff * 2, RECONNECT_MAX_BACKOFF)
            self.stop_event.wait(backoff if backoff != 1.0 else BMS_INTERVAL)

    @staticmethod
    def _fmt_fault_time(t):
        try:
            dt = datetime.fromisoformat((t or "").replace("Z", "+00:00"))
            return dt.strftime("%m-%d %H:%M")
        except Exception:
            return (t or "")[:16]

    def fault_worker(self):
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                if not self.token:
                    self.login()
                url = (f"{self.settings['base_url']}/v1/alarm?search=&level=0&alarm-type="
                       f"&page=1&page-size={FAULT_PAGE_SIZE}&handle-status=1")
                resp = self.session.get(url, headers=self._headers(), timeout=(5, 10))
                resp.raise_for_status()
                data = resp.json()
                items = (data.get("data") or {}).get("list") or []
                faults = []
                for it in items:
                    faults.append({
                        "device": it.get("device_name") or f"device {it.get('device_id')}",
                        "content": it.get("content") or "",
                        "level": it.get("level") or 0,
                        "time": self._fmt_fault_time(it.get("occur_time")),
                    })
                with self.lock:
                    self.faults = {"items": faults, "ts": datetime.now().strftime("%H:%M:%S"), "error": None}
                self._set_conn("connected")
                backoff = 1.0
            except Exception as e:
                with self.lock:
                    self.faults = {"items": [], "ts": None, "error": str(e)}
                self._set_conn("error", str(e))
                if self._is_auth_error(e):
                    self.token = None
                backoff = min(backoff * 2, RECONNECT_MAX_BACKOFF)
            self.stop_event.wait(backoff if backoff != 1.0 else FAULT_INTERVAL)

    # ------------------------------------------------------------ automation
    def _ui(self, fn, *args):
        try:
            self.after(0, lambda: fn(*args))
        except Exception:
            pass

    def _log_console(self, msg, color=COLOR_LIGHT_GREEN):
        if self.console is None:
            return
        try:
            self.console.configure(state="normal")
            self.console.tag_configure(color, foreground=color)
            self.console.insert(
                "end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", (color,))
            self.console.see("end")
            self.console.configure(state="disabled")
        except Exception:
            pass

    def toggle_automation(self):
        if self.automation["enabled"]:
            self.automation["enabled"] = False
            if self.btn_automation is not None:
                self.btn_automation.configure(
                    text="Start Automation", fg_color=COLOR_GREEN, hover_color=self.colors["accent_hover"])
            self._log_console("Automation stopped", COLOR_RED)
        else:
            self.automation["enabled"] = True
            self.automation["pv_power"] = self._read_pv_setting()
            if self.btn_automation is not None:
                self.btn_automation.configure(
                    text="Stop Automation", fg_color=COLOR_RED, hover_color=self.colors["danger_hover"])
            self._log_console("Automation started", COLOR_GREEN)
            threading.Thread(target=self.automation_tick, daemon=True).start()

    def _read_pv_setting(self):
        if self.ent_pv_power is not None:
            try:
                return float(self.ent_pv_power.get().strip())
            except Exception:
                pass
        return 100.0

    def _set_pv_entry(self, value):
        if self.ent_pv_power is not None:
            self.ent_pv_power.delete(0, "end")
            self.ent_pv_power.insert(0, f"{float(value):.1f}")

    def automation_worker(self):
        while not self.stop_event.is_set():
            self.stop_event.wait(self.auto_settings["interval"])
            if self.stop_event.is_set():
                break
            if not self.automation["enabled"]:
                continue
            try:
                self.automation_tick()
            except Exception as e:
                self._ui(self._log_console, f"automation error: {e}", COLOR_RED)

    def automation_tick(self):
        if self._automation_ticking:
            return
        self._automation_ticking = True
        try:
            with self.lock:
                pg = dict(self.power_group)
                bms = dict(self.bms)
            devices = pg.get("devices") or {}
            gate_raw = devices.get("GateMeter", {}).get("apparent_power")
            ess1 = devices.get("ESS1 master", {}).get("pcs_apparent_power")
            ess2 = devices.get("ESS2 slave", {}).get("pcs_apparent_power")
            socs = [d.get("soc") for d in (bms.get("devices") or {}).values() if d.get("soc") is not None]
            if gate_raw is None:
                self._ui(self._log_console, "no gate data yet, skipping", COLOR_GRAY)
                return
            gate = abs(gate_raw)
            now = datetime.now()
            temp = self._get_temperature()
            s = self.auto_settings
            hot = HOT_START_HOUR <= now.hour <= HOT_END_HOUR and temp is not None and temp >= s["hot_temp"]
            high_soc = any(x >= s["soc_high"] for x in socs)
            recover_soc = any(x <= s["soc_recover"] for x in socs)
            soc = max(socs) if socs else None
            current_pv = self.automation.get("pv_power") or self._read_pv_setting()
            target = current_pv
            rule = "idle"
            action = "no action"

            if high_soc:
                rule = "rule3-soc-high"
                if ess1 is not None and ess2 is not None:
                    if ess1 > ESS_DISCHARGE_RANGE[1] or ess2 > ESS_DISCHARGE_RANGE[1]:
                        target = current_pv - s["step"]
                        action = "SOC>=95, decrease PV to discharge ESS"
                    elif ess1 < ESS_DISCHARGE_RANGE[0] or ess2 < ESS_DISCHARGE_RANGE[0]:
                        target = current_pv + s["step"]
                        action = "SOC>=95, ESS below target, raise PV"
                    else:
                        action = "SOC>=95, ESS in -25..-15, hold"
                else:
                    action = "SOC>=95, waiting for ESS data"
            elif recover_soc:
                rule = "rule3-soc-recover"
                if ess1 is not None and ess2 is not None and (ess1 < 0 or ess2 < 0):
                    target = current_pv + s["step"]
                    action = "SOC<=85, increase PV to charge ESS"
                else:
                    action = "SOC<=85, ESS positive, hold"
            elif hot:
                rule = "rule2-hot"
                target = max(s["pv_min"], gate - 20.0)
                if ess1 is not None and ess2 is not None:
                    if ess1 < ESS_CHARGE_RANGE[0] or ess2 < ESS_CHARGE_RANGE[0]:
                        target += s["step"]
                        action = "hot, PV=gate-20, raise to keep ESS>=10"
                    elif ess1 > ESS_CHARGE_RANGE[1] or ess2 > ESS_CHARGE_RANGE[1]:
                        target -= s["step"]
                        action = "hot, PV=gate-20, lower to keep ESS<=20"
                    else:
                        action = "hot, PV=gate-20, ESS in 10..20"
                else:
                    action = "hot, PV=gate-20"
            elif gate_raw <= 0.0:
                rule = "rule1-gate-negative"
                target = max(s["pv_min"], gate + 20.0)
                action = "gate<=0, PV=abs(gate)+20"
            else:
                action = "gate>0, hold"

            target = max(s["pv_min"], min(s["pv_max"], target))
            applied = False
            if abs(target - current_pv) > 0.01:
                try:
                    self._apply_pv_power_sync(round(target, 1))
                    applied = True
                    self.automation["pv_power"] = target
                    self._ui(self._set_pv_entry, target)
                    self._ui(self._log_console,
                             f"{action} -> PV {current_pv:.1f} -> {target:.1f} kW",
                             COLOR_GREEN)
                except Exception as e:
                    self._ui(self._log_console, f"{action} failed: {e}", COLOR_RED)
            else:
                self.automation["pv_power"] = target
                self._ui(self._log_console, action, COLOR_GRAY)

            self._append_log({
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "rule": rule,
                "action": action,
                "gate_kw": f"{gate_raw:.1f}",
                "ess1_kw": f"{ess1:.1f}" if ess1 is not None else "",
                "ess2_kw": f"{ess2:.1f}" if ess2 is not None else "",
                "pv_current_kw": f"{current_pv:.1f}",
                "pv_target_kw": f"{target:.1f}",
                "temp_c": f"{temp:.1f}" if temp is not None else "",
                "soc": f"{soc:.1f}" if soc is not None else "",
                "applied": "yes" if applied else "no",
            })
        finally:
            self._automation_ticking = False

    def _append_log(self, record):
        try:
            path = self.log_dir / f"automation_{datetime.now().strftime('%Y-%m-%d')}.csv"
            new = not path.exists()
            with open(path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
                if new:
                    writer.writeheader()
                writer.writerow({k: record.get(k, "") for k in LOG_FIELDS})
        except Exception as e:
            self._ui(self._log_console, f"log write error: {e}", COLOR_RED)

    def _available_log_days(self):
        days = []
        try:
            for p in self.log_dir.glob("automation_*.csv"):
                days.append(p.stem.split("_", 1)[1])
        except Exception:
            pass
        return sorted(days, reverse=True)

    def download_log(self):
        days = self._available_log_days()
        if not days:
            self._log_console("No logs available yet", COLOR_RED)
            return
        top = ctk.CTkToplevel(self)
        top.title("Download Log")
        top.geometry("340x200")
        top.resizable(False, False)
        ctk.CTkLabel(top, text="Select a day to download:", font=ctk.CTkFont(size=12)).pack(pady=(16, 6))
        menu = ctk.CTkOptionMenu(top, values=days, width=200, height=30)
        menu.pack(pady=(0, 12))
        menu.set(days[0])

        def save():
            day = menu.get()
            src = self.log_dir / f"automation_{day}.csv"
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=f"automation_{day}.csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
            if path:
                try:
                    shutil.copy(str(src), path)
                    self._log_console(f"Log saved: {path}", COLOR_GREEN)
                    top.destroy()
                except Exception as e:
                    self._log_console(f"save failed: {e}", COLOR_RED)

        ctk.CTkButton(top, text="Save", width=120, height=30, corner_radius=8, command=save).pack(pady=(4, 12))

    def _get_location(self):
        if self.location_cache is not None:
            return self.location_cache or None
        loc = None
        try:
            ip = requests.get("https://api.ipify.org?format=json", timeout=5).json().get("ip")
            data = requests.get(f"https://ipapi.co/{ip}/json/", timeout=6).json()
            if data.get("latitude") is not None and data.get("longitude") is not None:
                loc = {"lat": data["latitude"], "lon": data["longitude"], "city": data.get("city") or data.get("region") or ""}
        except Exception:
            pass
        if loc is None:
            try:
                data = requests.get("https://ipwho.is/", timeout=6).json()
                if data.get("latitude") is not None and data.get("longitude") is not None:
                    loc = {"lat": data["latitude"], "lon": data["longitude"], "city": data.get("city") or ""}
            except Exception:
                pass
        self.location_cache = loc
        city = (loc.get("city") or "").strip()
        if loc is None:
            self._ui(self._set_location_label, "unknown")
            self._ui(self._set_weather_label, "Weather: unavailable")
        else:
            self._ui(self._set_location_label,
                     city or f"{loc['lat']:.2f}, {loc['lon']:.2f}")
        return loc

    def _get_temperature(self):
        now = time.time()
        if self.weather_cache and now - self.weather_cache.get("ts", 0) < WEATHER_CACHE_SECONDS:
            return self.weather_cache["temp"]
        loc = self._get_location()
        if not loc:
            return None
        try:
            data = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": loc["lat"], "longitude": loc["lon"], "current": "temperature_2m"},
                timeout=8).json()
            temp = data["current"]["temperature_2m"]
            self.weather_cache = {"ts": now, "temp": temp}
            city = (loc.get("city") or "").strip()
            self._ui(self._set_weather_label,
                     f"Weather: {temp:.1f}°C {city}".strip())
            self._ui(self._set_bottom_weather, f"Weather: {temp:.1f}°C")
            return temp
        except Exception:
            return None

    def _set_weather_label(self, text):
        if self.lbl_weather is not None:
            self.lbl_weather.configure(text=text)

    def _set_bottom_weather(self, text):
        if self.lbl_bottom_weather is not None:
            self.lbl_bottom_weather.configure(text=f"⛅ {text}")

    def _set_location_label(self, city):
        if self.lbl_bottom_location is not None:
            self.lbl_bottom_location.configure(text=f"📍 Location: {city}")

    def open_settings(self):
        fields = [
            ("interval", "Interval (seconds)"),
            ("step", "PV step (kW)"),
            ("pv_min", "PV min (kW)"),
            ("pv_max", "PV max (kW)"),
            ("hot_temp", "Hot temp threshold (°C)"),
            ("soc_high", "SOC high (%)"),
            ("soc_recover", "SOC recover (%)"),
        ]
        top = ctk.CTkToplevel(self)
        top.title("Automation Settings")
        top.geometry("360x360")
        top.resizable(False, False)
        entries = {}
        for row, (key, label) in enumerate(fields):
            ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=12)).grid(
                row=row, column=0, sticky="w", padx=16, pady=(8, 0))
            ent = ctk.CTkEntry(top, width=130, height=28, corner_radius=8)
            ent.insert(0, str(self.auto_settings.get(key, "")))
            ent.grid(row=row, column=1, sticky="e", padx=16, pady=(8, 0))
            entries[key] = ent

        def save():
            try:
                for key, ent in entries.items():
                    self.auto_settings[key] = float(ent.get().strip())
                self._log_console(
                    f"Settings saved (interval {self.auto_settings['interval']}s, "
                    f"step {self.auto_settings['step']} kW, hot temp {self.auto_settings['hot_temp']}°C)",
                    COLOR_LIGHT_GREEN)
                top.destroy()
            except ValueError:
                self._log_console("Settings: invalid number", COLOR_RED)

        ctk.CTkButton(top, text="Save", width=140, height=30, corner_radius=8,
                      command=save).grid(row=len(fields), column=0, columnspan=2, pady=18)

    def rebuild_dashboard(self):
        try:
            self.dashboard_view.destroy()
        except Exception:
            pass
        self.build_dashboard()
        if self.current_view == "dashboard":
            self.show_dashboard()
        else:
            self.dashboard_view.grid_remove()

    def toggle_theme(self):
        mode = "light" if self.theme == "dark" else "dark"
        ctk.set_appearance_mode(mode)
        self.theme = mode
        self.colors = THEMES[mode]
        self.rebuild_dashboard()
        if self.btn_theme is not None:
            self.btn_theme.configure(text="☀" if mode == "light" else "🌙")

    # ------------------------------------------------------------ ui refresh
    def refresh_ui(self):
        if self.current_view == "dashboard":
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if self.lbl_clock is not None:
                self.lbl_clock.configure(text=now)
            if self.lbl_bottom_clock is not None:
                self.lbl_bottom_clock.configure(text=now)
            with self.lock:
                pv = dict(self.pv)
                bms = dict(self.bms)
                faults = dict(self.faults)
                seq = dict(self.sequence_status)
                conn = dict(self.conn)

            # --- header connection status ---
            if conn["status"] == "error":
                self.lbl_conn.configure(text="reconnecting...", text_color=COLOR_RED)
            elif conn["status"] == "connected":
                self.lbl_conn.configure(text="connected", text_color=COLOR_GREEN)
            else:
                self.lbl_conn.configure(text="connecting...", text_color=COLOR_INFO)

            # --- control: sequence status ---
            state = "disabled" if self.sequence_running else "normal"
            self.btn_seq_both.configure(state=state)
            for btn in self.btn_seq_bms.values():
                btn.configure(state=state)
            if self.sequence_running or seq:
                parts = []
                failed = False
                for did, st in seq.items():
                    if st.get("error"):
                        parts.append(f"BMS {did}: error ({st['error'][:40]})")
                        failed = True
                    elif st.get("done"):
                        parts.append(f"BMS {did}: done")
                    else:
                        parts.append(f"BMS {did}: {st.get('step', '...')}")
                self.lbl_seq_status.configure(text="  |  ".join(parts),
                                              text_color=COLOR_RED if failed else COLOR_INFO)
            else:
                self.lbl_seq_status.configure(text="idle", text_color=COLOR_GRAY)

            # --- power group ---
            pg = dict(self.power_group)
            pg_names = [n for n in POWER_GROUP_DEVICES if n in pg["devices"]]
            if pg_names and pg_names != self.power_group_rendered:
                self.render_power_group_cards(pg_names)
            if pg.get("error"):
                self.lbl_pg_ts.configure(text=f"connection error: {pg['error'][:50]}", text_color=COLOR_RED)
            else:
                self.lbl_pg_ts.configure(text="updated " + pg["ts"] if pg.get("ts") else "waiting for data...",
                                         text_color=COLOR_GRAY)
            for name, widgets in self.power_group_cards.items():
                info = pg["devices"].get(name) or {}
                pcs_power = info.get("pcs_apparent_power")
                if pcs_power is not None:
                    widgets["value"].configure(text=f"{pcs_power} kW", text_color=COLOR_GREEN)
                    widgets["caption"].configure(text="PCS total active power (kW)")
                else:
                    apparent = info.get("apparent_power")
                    widgets["caption"].configure(text="total active power (kW)")
                    if apparent is not None:
                        widgets["value"].configure(text=f"{apparent} kW", text_color=COLOR_GREEN)
                    else:
                        widgets["value"].configure(text="--", text_color=COLOR_GREEN)

            # --- photovoltaic ---
            pv_names = sorted(pv["devices"].keys())
            if pv_names and pv_names != self.pv_rendered:
                self.render_pv_cards(pv_names)
            if pv.get("error"):
                self.lbl_pv_ts.configure(text=f"connection error: {pv['error'][:50]}", text_color=COLOR_RED)
            else:
                self.lbl_pv_ts.configure(text="updated " + pv["ts"] if pv.get("ts") else "waiting for data...",
                                         text_color=COLOR_GRAY)
            for name, widgets in self.pv_cards.items():
                power = pv["devices"].get(name)
                if power is not None:
                    widgets["value"].configure(text=f"{power} kW", text_color=COLOR_GREEN)
                else:
                    widgets["value"].configure(text="--", text_color=COLOR_GREEN)

            # --- battery ---
            bms_names = list(bms["devices"].keys())
            if bms_names and bms_names != self.bms_rendered:
                self.render_bms_cards(bms_names)
            if bms.get("error"):
                self.lbl_bms_ts.configure(text=f"connection error: {bms['error'][:50]}", text_color=COLOR_RED)
            else:
                self.lbl_bms_ts.configure(text="updated " + bms["ts"] if bms.get("ts") else "waiting for data...",
                                          text_color=COLOR_GRAY)
            for name, card in self.bms_cards.items():
                    info = bms["devices"].get(name) or {}
                    soc = info.get("soc")
                    if soc is not None:
                        try:
                            card["value"].configure(text=f"{float(soc):.1f}%", text_color=COLOR_GREEN)
                            card["progress"].set(max(0.0, min(float(soc) / 100.0, 1.0)))
                        except Exception:
                            card["value"].configure(text="--")
                    else:
                        card["value"].configure(text="--", text_color=COLOR_GREEN)
                        card["progress"].set(0)
                    status = BMS_STATUS_MAP.get(info.get("status"), "-")
                    card["status"].configure(text=f"status: {status}")

            # --- faults ---
            fault_items = faults.get("items") or []
            if self.fault_scroll is not None:
                if faults.get("error"):
                    self.lbl_fault_ts.configure(text=f"connection error: {faults['error'][:50]}", text_color=COLOR_RED)
                else:
                    self.lbl_fault_ts.configure(text=("updated " + faults["ts"] if faults.get("ts") else "waiting for data..."),
                                                text_color=COLOR_GRAY)
                key = (faults.get("ts"), tuple((f["device"], f["content"], f["level"], f["time"]) for f in fault_items))
                if key != self._faults_rendered:
                    self._faults_rendered = key
                    for w in getattr(self.fault_scroll, "winfo_children", lambda: [])():
                        w.destroy()
                    if not fault_items:
                        ctk.CTkLabel(self.fault_scroll, text="no active faults", font=ctk.CTkFont(size=12),
                                     text_color=COLOR_GRAY).pack(pady=10)
                    for f in fault_items:
                        level = int(f.get("level") or 0)
                        row = ctk.CTkFrame(self.fault_scroll, fg_color="transparent")
                        row.pack(fill="x", padx=6, pady=(0, 5))
                        color = COLOR_RED if level >= 1 else COLOR_ORANGE
                        top = ctk.CTkFrame(row, fg_color="transparent")
                        top.pack(fill="x")
                        ctk.CTkLabel(top, text=f.get("device", "device"), font=ctk.CTkFont(size=11, weight="bold"),
                                     text_color=color).pack(side="left")
                        ctk.CTkLabel(top, text=f.get("time", ""), font=ctk.CTkFont(size=10),
                                     text_color=COLOR_GRAY).pack(side="right")
                        ctk.CTkLabel(row, text=f.get("content", ""), font=ctk.CTkFont(size=11),
                                     text_color=self.colors["text"], wraplength=420, justify="left").pack(fill="x", anchor="w")
        self.after(200, self.refresh_ui)


if __name__ == "__main__":
    app = PcsRealtimeMonitor()
    app.mainloop()
