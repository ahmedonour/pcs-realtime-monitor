#!/usr/bin/env python3
"""PCS Realtime Monitor.

A clean CustomTkinter dashboard:
  - Login screen first; after login the dashboard appears.
  - Photovoltaic SSE stream -> one card per device (PV1..PV5) with output power.
  - Battery SOC for every BMS device (extension's /v1/history-data poll).
"""

import json
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
import requests
import tkinter as tk

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
RECONNECT_MAX_BACKOFF = 30.0  # seconds between retries while disconnected

SEQUENCE_STEPS = [
    ("pcs_device_stop", "Stop device"),
    ("pcs_fault_reset", "Fault reset"),
    ("pcs_system_operate_reset", "System operate reset"),
    ("pcs_device_startup", "Device startup"),
]
PV_CHARGE_DEVICE_IDS = [1, 2, 3, 4, 6]

COLOR_GREEN = "#4cc38a"
COLOR_RED = "#e65454"
COLOR_GRAY = "#8a8aa3"
COLOR_INFO = "#54a0e8"

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
        self.geometry("920x660")
        self.minsize(760, 560)
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
        self.stop_event = threading.Event()
        self.workers = []
        self.login_lock = threading.Lock()
        self.conn = {"status": "idle", "error": None}
        self.tray_icon = None
        self.run_in_background = tk.BooleanVar(value=True)

        self.sequence_running = False
        self.sequence_status = {}

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
                                        fg_color="#3a3a52", hover_color="#4a4a66", command=self.logout)
        self.btn_logout.pack(side="right")

        self.content = ctk.CTkScrollableFrame(self.dashboard_view, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(2, 0))
        self.content.grid_columnconfigure(0, weight=1)

        self.build_control_section()

        # Power group section (GateMeter, ESS1 meter, ESS2 meter)
        pg_head = ctk.CTkFrame(self.content, fg_color="transparent")
        pg_head.grid(row=1, column=0, sticky="ew")
        pg_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pg_head, text="POWER GROUP", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(side="left")
        self.lbl_pg_ts = ctk.CTkLabel(pg_head, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_pg_ts.pack(side="right")

        self.power_group_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.power_group_container.grid(row=2, column=0, sticky="ew", pady=(4, 2))

        # Photovoltaic section
        pv_head = ctk.CTkFrame(self.content, fg_color="transparent")
        pv_head.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        pv_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pv_head, text="PHOTOVOLTAIC DEVICES", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(side="left")
        self.lbl_pv_ts = ctk.CTkLabel(pv_head, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_pv_ts.pack(side="right")

        self.pv_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.pv_container.grid(row=4, column=0, sticky="ew", pady=(4, 2))

        # Battery section
        bms_head = ctk.CTkFrame(self.content, fg_color="transparent")
        bms_head.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        bms_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(bms_head, text="BATTERY (BMS)", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(side="left")
        self.lbl_bms_ts = ctk.CTkLabel(bms_head, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_bms_ts.pack(side="right")

        self.bms_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.bms_container.grid(row=6, column=0, sticky="ew", pady=(4, 2))

    def build_control_section(self):
        ctl = ctk.CTkFrame(self.content, corner_radius=12, fg_color="#1c1d30")
        ctl.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(ctl, text="CONTROL", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(anchor="w", padx=16, pady=(8, 2))

        seq_row = ctk.CTkFrame(ctl, fg_color="transparent")
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

        self.lbl_seq_status = ctk.CTkLabel(ctl, text="idle", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_seq_status.pack(anchor="w", padx=16, pady=(0, 2))

        ctk.CTkFrame(ctl, height=1, fg_color="#2c2d45").pack(fill="x", padx=16, pady=(0, 4))

        pv_row = ctk.CTkFrame(ctl, fg_color="transparent")
        pv_row.pack(fill="x", padx=16, pady=(0, 2))
        ctk.CTkLabel(pv_row, text="PV power (run_power)", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 12))
        self.ent_pv_power = ctk.CTkEntry(pv_row, width=100, height=26, corner_radius=8)
        self.ent_pv_power.insert(0, "100")
        self.ent_pv_power.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(pv_row, text="kW", font=ctk.CTkFont(size=11), text_color=COLOR_GRAY).pack(side="left", padx=(0, 12))
        self.btn_pv_power = ctk.CTkButton(pv_row, text="Apply", width=80, height=26, corner_radius=8,
                                          command=self.apply_pv_power)
        self.btn_pv_power.pack(side="left")

        self.lbl_pv_power_status = ctk.CTkLabel(ctl, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        self.lbl_pv_power_status.pack(anchor="w", padx=16, pady=(0, 2))

        self.chk_background = ctk.CTkCheckBox(
            ctl, text="Run in background when the window is closed",
            variable=self.run_in_background, text_color=COLOR_GRAY,
            font=ctk.CTkFont(size=10), fg_color=COLOR_GREEN, hover_color="#3aa372",
        )
        self.chk_background.pack(anchor="w", padx=16, pady=(0, 6))

    def show_dashboard(self):
        self.current_view = "dashboard"
        self.login_view.grid_remove()
        self.dashboard_view.grid()

    def logout(self):
        self.token = None
        self.sequence_running = False
        self.sequence_status = {}
        self.show_login()
        with self.lock:
            self.pv = {"devices": {}, "ts": None, "error": None}
            self.bms = {"devices": {}, "ts": None, "error": None}
            self.power_group = {"devices": {}, "ts": None, "error": None}
            self.conn = {"status": "idle", "error": None}

    # ------------------------------------------------------------ cards
    def render_power_group_cards(self, names):
        for w in self.power_group_container.winfo_children():
            w.destroy()
        self.power_group_cards = {}
        for i, name in enumerate(names):
            card = ctk.CTkFrame(self.power_group_container, corner_radius=12, fg_color="#1f2035")
            card.grid(row=0, column=i, sticky="ew", padx=6, pady=4)
            self.power_group_container.grid_columnconfigure(i, weight=1, uniform="pg")
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_INFO).pack(anchor="w", padx=14, pady=(8, 2))
            value = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_GREEN)
            value.pack(anchor="w", padx=14)
            caption = ctk.CTkLabel(card, text="total active power (kW)", font=ctk.CTkFont(size=10),
                                   text_color=COLOR_GRAY)
            caption.pack(anchor="w", padx=14, pady=(2, 8))
            self.power_group_cards[name] = {"value": value, "caption": caption}
        self.power_group_rendered = list(names)

    def render_pv_cards(self, names):
        for w in self.pv_container.winfo_children():
            w.destroy()
        self.pv_cards = {}
        cols = 3
        for i, name in enumerate(names):
            card = ctk.CTkFrame(self.pv_container, corner_radius=12, fg_color="#1f2035")
            r, c = divmod(i, cols)
            card.grid(row=r, column=c, sticky="ew", padx=6, pady=4)
            self.pv_container.grid_columnconfigure(c, weight=1, uniform="pv")
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_INFO).pack(anchor="w", padx=14, pady=(8, 2))
            value = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_GREEN)
            value.pack(anchor="w", padx=14)
            ctk.CTkLabel(card, text="kilowatts (kW)", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY).pack(anchor="w", padx=14, pady=(2, 8))
            self.pv_cards[name] = value
        self.pv_rendered = list(names)

    def render_bms_cards(self, names):
        for w in self.bms_container.winfo_children():
            w.destroy()
        self.bms_cards = {}
        cols = 2
        for i, name in enumerate(names):
            card = ctk.CTkFrame(self.bms_container, corner_radius=12, fg_color="#1f2035")
            r, c = divmod(i, cols)
            card.grid(row=r, column=c, sticky="ew", padx=6, pady=4)
            self.bms_container.grid_columnconfigure(c, weight=1, uniform="bms")
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_INFO).pack(anchor="w", padx=14, pady=(8, 2))
            value = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_GREEN)
            value.pack(anchor="w", padx=14)
            progress = ctk.CTkProgressBar(card, height=6, corner_radius=3, progress_color=COLOR_GREEN)
            progress.set(0)
            progress.pack(fill="x", padx=14, pady=(6, 2))
            status = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
            status.pack(anchor="w", padx=14, pady=(0, 8))
            self.bms_cards[name] = {"value": value, "progress": progress, "status": status}
        self.bms_rendered = list(names)

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

    def _pv_power_worker(self, run_power):
        try:
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
            self.after(0, lambda: self.lbl_pv_power_status.configure(
                text=f"PV power set to {run_power} kW", text_color=COLOR_GREEN))
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
        for target in (self.power_group_worker, self.pv_worker, self.bms_worker):
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

    # ------------------------------------------------------------ ui refresh
    def refresh_ui(self):
        if self.current_view == "dashboard":
            with self.lock:
                pv = dict(self.pv)
                bms = dict(self.bms)
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
            for name, value in self.pv_cards.items():
                power = pv["devices"].get(name)
                if power is not None:
                    value.configure(text=f"{power} kW", text_color=COLOR_GREEN)
                else:
                    value.configure(text="--", text_color=COLOR_GREEN)

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
        self.after(200, self.refresh_ui)


if __name__ == "__main__":
    app = PcsRealtimeMonitor()
    app.mainloop()
