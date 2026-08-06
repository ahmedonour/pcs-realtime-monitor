#!/usr/bin/env python3
"""PCS Realtime Monitor.

A clean CustomTkinter dashboard:
  - Login screen first; after login the dashboard appears.
  - Photovoltaic SSE stream -> shows device name + alternating_current_output_power.
  - BMS SOC (extension's /v1/history-data poll).
"""

import json
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
BMS_INTERVAL = 5.0  # seconds (matches the extension)

COLOR_GREEN = "#4cc38a"
COLOR_RED = "#e65454"
COLOR_GRAY = "#8a8aa3"
COLOR_INFO = "#54a0e8"


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
        self.geometry("760x540")
        self.minsize(680, 480)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.session = requests.Session()
        self.token = None
        self.settings = {
            "base_url": DEFAULT_BASE_URL,
            "username": DEFAULT_USERNAME,
            "password": DEFAULT_PASSWORD,
        }
        self.current_view = "login"

        self.lock = threading.Lock()
        self.pv = {"name": None, "power": None, "ts": None, "error": None}
        self.bms = {"soc": None, "status": None, "ts": None, "error": None}
        self.stop_event = threading.Event()
        self.workers = []

        self._window_icon()
        self.build_login()
        self.build_dashboard()
        self.show_login()

        self.after(200, self.refresh_ui)

    # ------------------------------------------------------------ window icon
    def _window_icon(self):
        try:
            if ICON_FILE.exists():
                self._icon_image = tk.PhotoImage(file=str(ICON_FILE))
                self.iconphoto(True, self._icon_image)
        except Exception:
            pass

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
        self.lbl_logo = ctk.CTkLabel(card, text="", image=logo)
        self.lbl_logo.grid(row=0, column=0, pady=(28, 4))

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
        self.lbl_login_msg.configure(text="", text_color=COLOR_GREEN)
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
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="PCS Realtime Monitor", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.lbl_conn = ctk.CTkLabel(header, text="connected", font=ctk.CTkFont(size=11), text_color=COLOR_GREEN)
        self.lbl_conn.pack(side="left", padx=12)
        self.btn_logout = ctk.CTkButton(header, text="Log out", width=80, height=28, corner_radius=8,
                                        fg_color="#3a3a52", hover_color="#4a4a66", command=self.logout)
        self.btn_logout.pack(side="right")

        content = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Photovoltaic card
        pv_card = ctk.CTkFrame(content, corner_radius=16, fg_color="#1f2035")
        pv_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(pv_card, text="PHOTOVOLTAIC OUTPUT POWER", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(anchor="w", padx=20, pady=(18, 2))
        self.lbl_pv_name = ctk.CTkLabel(pv_card, text="-", font=ctk.CTkFont(size=13), text_color=COLOR_INFO)
        self.lbl_pv_name.pack(anchor="w", padx=20, pady=(0, 4))
        self.lbl_pv_value = ctk.CTkLabel(pv_card, text="--", font=ctk.CTkFont(size=52, weight="bold"),
                                         text_color=COLOR_GREEN)
        self.lbl_pv_value.pack(anchor="w", padx=20, pady=(4, 0))
        ctk.CTkLabel(pv_card, text="kilowatts (kW)", font=ctk.CTkFont(size=12), text_color=COLOR_GRAY).pack(anchor="w", padx=20)
        self.lbl_pv_ts = ctk.CTkLabel(pv_card, text="waiting for data...", font=ctk.CTkFont(size=11), text_color=COLOR_GRAY)
        self.lbl_pv_ts.pack(anchor="w", padx=20, pady=(14, 18))

        # Battery / BMS card
        bms_card = ctk.CTkFrame(content, corner_radius=16, fg_color="#1f2035")
        bms_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(bms_card, text="BATTERY (BMS)", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_GRAY).pack(anchor="w", padx=20, pady=(18, 2))
        self.lbl_bms_status = ctk.CTkLabel(bms_card, text="-", font=ctk.CTkFont(size=13), text_color=COLOR_INFO)
        self.lbl_bms_status.pack(anchor="w", padx=20, pady=(0, 4))
        self.lbl_bms_value = ctk.CTkLabel(bms_card, text="--", font=ctk.CTkFont(size=52, weight="bold"),
                                          text_color=COLOR_GREEN)
        self.lbl_bms_value.pack(anchor="w", padx=20, pady=(4, 0))
        self.progress = ctk.CTkProgressBar(bms_card, height=10, corner_radius=5, progress_color=COLOR_GREEN)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=20, pady=(12, 6))
        self.lbl_bms_ts = ctk.CTkLabel(bms_card, text="waiting for data...", font=ctk.CTkFont(size=11), text_color=COLOR_GRAY)
        self.lbl_bms_ts.pack(anchor="w", padx=20, pady=(8, 18))

    def show_dashboard(self):
        self.current_view = "dashboard"
        self.login_view.grid_remove()
        self.dashboard_view.grid()

    def logout(self):
        self.token = None
        self.show_login()
        with self.lock:
            self.pv = {"name": None, "power": None, "ts": None, "error": None}
            self.bms = {"soc": None, "status": None, "ts": None, "error": None}

    # ------------------------------------------------------------ api
    def read_settings(self):
        self.settings.update({
            "base_url": self.ent_url.get().strip().rstrip("/"),
            "username": self.ent_user.get().strip(),
            "password": self.ent_pass.get(),
        })

    def login(self):
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

    # ------------------------------------------------------------ polling
    def start_polling(self):
        self.stop_event.clear()
        if self.workers:
            return
        for target in (self.pv_worker, self.bms_worker):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            self.workers.append(t)

    def stop_polling(self):
        self.stop_event.set()
        self.workers = []

    def pv_worker(self):
        while not self.stop_event.is_set():
            try:
                if not self.token:
                    self.login()
                url = f"{self.settings['base_url']}/v1/sse/photovoltaic?{PV_QUERY}"
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json;charset=utf-8",
                }
                event = self.read_sse_event(url, headers)
                if event is not None:
                    name, power = self.extract_pv(event)
                    with self.lock:
                        self.pv = {"name": name, "power": power, "ts": datetime.now().strftime("%H:%M:%S"), "error": None}
            except Exception as e:
                with self.lock:
                    self.pv = {"name": None, "power": None, "ts": None, "error": str(e)}
            self.stop_event.wait(1.0)

    def read_sse_event(self, url, headers, timeout=3.0):
        with self.session.get(url, headers=headers, stream=True, timeout=(3, 3)) as resp:
            if not resp.ok:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            buffer = ""
            start = time.time()
            for raw in resp.iter_lines(decode_unicode=True):
                if time.time() - start > timeout:
                    break
                if raw is None:
                    continue
                buffer += raw + "\n"
                if "\n\n" in buffer:
                    block, _, buffer = buffer.partition("\n\n")
                    for line in block.splitlines():
                        if line.startswith("data:"):
                            payload = line[5:].strip()
                            if payload:
                                try:
                                    return json.loads(payload)
                                except Exception:
                                    continue
        raise RuntimeError("no SSE data received")

    @staticmethod
    def extract_pv(event):
        if not isinstance(event, dict):
            return None, None
        name = event.get("name")
        power = None
        data = event.get("data")
        if isinstance(data, dict):
            power = data.get("alternating_current_output_power", data.get("alternatingCurrentOutputPower"))
        if power is None:
            power = deep_find(event, "alternating_current_output_power")
        if power is None:
            power = deep_find(event, "alternatingCurrentOutputPower")
        return name, power

    def bms_worker(self):
        while not self.stop_event.is_set():
            try:
                if not self.token:
                    self.login()
                for did in self.settings.get("device_ids", [2, 3]):
                    url = f"{self.settings['base_url']}/v1/history-data?page=1&page-size=1"
                    headers = {
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json;charset=utf-8",
                    }
                    resp = self.session.post(
                        url,
                        headers=headers,
                        json={"device_id": did, "device_type": 2, "fields": ["bms_running_status", "bms_soc"]},
                        timeout=(5, 10),
                    )
                    data = resp.json()
                    items = (data.get("data") or {}).get("list") or []
                    if items:
                        latest = items[0]
                        with self.lock:
                            self.bms = {
                                "soc": latest.get("bms_soc"),
                                "status": latest.get("bms_running_status"),
                                "ts": datetime.now().strftime("%H:%M:%S"),
                                "error": None,
                            }
                        break
            except Exception as e:
                with self.lock:
                    self.bms = {"soc": None, "status": None, "ts": None, "error": str(e)}
            self.stop_event.wait(BMS_INTERVAL)

    # ------------------------------------------------------------ ui refresh
    def refresh_ui(self):
        if self.current_view == "dashboard":
            with self.lock:
                pv = dict(self.pv)
                bms = dict(self.bms)

            if pv.get("error"):
                self.lbl_pv_value.configure(text="--", text_color=COLOR_RED)
                self.lbl_pv_name.configure(text="error")
                self.lbl_pv_ts.configure(text=f"connection error: {pv['error'][:60]}", text_color=COLOR_RED)
            else:
                power = pv.get("power")
                if power is not None:
                    self.lbl_pv_value.configure(text=f"{power} kW", text_color=COLOR_GREEN)
                else:
                    self.lbl_pv_value.configure(text="--", text_color=COLOR_GREEN)
                self.lbl_pv_name.configure(text=pv.get("name") or "PV system")
                self.lbl_pv_ts.configure(text=("updated " + pv["ts"]) if pv.get("ts") else "waiting for data...",
                                         text_color=COLOR_GRAY)

            if bms.get("error"):
                self.lbl_bms_value.configure(text="--", text_color=COLOR_RED)
                self.lbl_bms_status.configure(text="error")
                self.lbl_bms_ts.configure(text=f"connection error: {bms['error'][:60]}", text_color=COLOR_RED)
                self.progress.set(0)
            else:
                soc = bms.get("soc")
                if soc is not None:
                    try:
                        self.lbl_bms_value.configure(text=f"{float(soc):.1f}%", text_color=COLOR_GREEN)
                        self.progress.set(max(0.0, min(float(soc) / 100.0, 1.0)))
                    except Exception:
                        self.lbl_bms_value.configure(text="--")
                else:
                    self.lbl_bms_value.configure(text="--", text_color=COLOR_GREEN)
                self.lbl_bms_status.configure(text=f"BMS status: {bms.get('status')}" if bms.get("status") is not None else "BMS status: -")
                self.lbl_bms_ts.configure(text=("updated " + bms["ts"]) if bms.get("ts") else "waiting for data...",
                                          text_color=COLOR_GRAY)
        self.after(200, self.refresh_ui)


if __name__ == "__main__":
    app = PcsRealtimeMonitor()
    app.mainloop()
