#!/usr/bin/env python3
"""PCS Realtime Monitor - Python/CTk replica of the pcs-control extension.

Polls every realtime endpoint every N seconds (default 1s) and shows results
on screen, plus the original PCS control functions (start sequence, charge
power, BMS history).
"""

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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
DEFAULT_DEVICE_ID = "1"
DEFAULT_DEVICE_IDS = [2, 3]
POLL_INTERVAL = 1.0

PCS_SEQUENCE = [
    {"path": lambda d: f"/v1/pcs-control/{d}", "method": "PATCH", "body": {"pcs_device_stop": 1}, "label": "Stop device"},
    {"path": lambda d: f"/v1/pcs-control/{d}", "method": "PATCH", "body": {"pcs_fault_reset": 1}, "label": "Fault reset"},
    {"path": lambda d: f"/v1/pcs-control/{d}", "method": "PATCH", "body": {"pcs_system_operate_reset": 1}, "label": "System operate reset"},
    {"path": lambda d: f"/v1/pcs-control/{d}", "method": "PATCH", "body": {"pcs_device_startup": 1}, "label": "Device startup"},
]

REALTIME_REQUESTS = [
    {"id": "bmsClusters", "label": "BMS Clusters Actual Time", "transport": "json", "method": "GET", "path": "/v1/actual-time/bms-clusters/{deviceId}"},
    {"id": "total", "label": "Actual Time Total", "transport": "sse", "method": "GET", "path": "/v1/actual-time/total/{deviceId}"},
    {"id": "chargePail", "label": "Charge Pail", "transport": "sse", "method": "GET", "path": "/v1/sse/charge-pail"},
    {"id": "photovoltaic", "label": "Photovoltaic", "transport": "sse", "method": "GET", "path": "/v1/sse/photovoltaic"},
    {"id": "relayProtection", "label": "Relay Protection", "transport": "sse", "method": "GET", "path": "/v1/sse/relay-protection"},
    {"id": "transformerTemp", "label": "Transformer Temperature Controller", "transport": "sse", "method": "GET", "path": "/v1/sse/transformer-temperature-controller"},
    {"id": "dido", "label": "DIDO", "transport": "sse", "method": "GET", "path": "/v1/sse/dido"},
    {"id": "tempHumidity", "label": "Temperature / Humidity Controller", "transport": "sse", "method": "GET", "path": "/v1/sse/temperature-humidity-controller"},
    {"id": "realtimeDataColGet", "label": "Realtime Data Collection (get)", "transport": "json", "method": "GET", "path": "/v1/system-setting/realtime-data-col"},
    {"id": "realtimeDataColSet", "label": "Realtime Data Collection (set)", "transport": "json", "method": "PUT", "path": "/v1/system-setting/realtime-data-col"},
]

COLOR_GREEN = "#4cc38a"
COLOR_RED = "#e65454"
COLOR_GRAY = "#9090b0"
COLOR_INFO = "#54a0e8"


class PcsRealtimeMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PCS Realtime Monitor")
        self.geometry("1180x780")
        self.minsize(1000, 680)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        if ICON_FILE.exists():
            try:
                self._icon_image = tk.PhotoImage(file=str(ICON_FILE))
                self.iconphoto(True, self._icon_image)
            except Exception:
                pass

        self.session = requests.Session()
        self.token = None
        self.settings = {
            "base_url": DEFAULT_BASE_URL,
            "username": DEFAULT_USERNAME,
            "password": DEFAULT_PASSWORD,
            "device_id": DEFAULT_DEVICE_ID,
            "device_ids": DEFAULT_DEVICE_IDS,
            "query": "",
            "body": "{}",
            "interval": POLL_INTERVAL,
        }
        self.lock = threading.Lock()
        self.results = {}
        self.row_widgets = {}
        self.stop_event = threading.Event()
        self.workers = []
        self.pcs_worker = None
        self.bms_worker = None
        self.bms_soc = None
        self.bms_status = None
        self.last_error = None

        self.build_sidebar()
        self.build_monitor()
        self.after(250, self.update_display)

    # ---------------------------------------------------------------- UI
    def build_sidebar(self):
        side = ctk.CTkScrollableFrame(self, width=340, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsw", padx=0, pady=0)

        # Connection
        conn = ctk.CTkFrame(side)
        conn.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(conn, text="CONNECTION", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=(6, 0))

        self.ent_url = self._entry(conn, "Server URL", self.settings["base_url"])
        self.ent_user = self._entry(conn, "Username", self.settings["username"])
        self.ent_pass = self._entry(conn, "Password", self.settings["password"], show="*")
        self.ent_device_id = self._entry(conn, "Device ID", self.settings["device_id"])
        self.ent_device_ids = self._entry(conn, "Device IDs (comma)", ", ".join(map(str, self.settings["device_ids"])))

        ctk.CTkButton(conn, text="Login", command=self.login_threaded).pack(fill="x", padx=8, pady=6)
        self.lbl_login = ctk.CTkLabel(conn, text="Not logged in", text_color=COLOR_GRAY, font=ctk.CTkFont(size=11))
        self.lbl_login.pack(anchor="w", padx=8, pady=(0, 6))

        # Realtime monitor controls
        mon = ctk.CTkFrame(side)
        mon.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(mon, text="REALTIME MONITOR", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=(6, 0))

        self.ent_interval = self._entry(mon, "Interval (seconds)", str(self.settings["interval"]))
        self.ent_query = self._entry(mon, "Query Params (SSE)", self.settings["query"], placeholder="device_id=1&page=1")
        self.ent_body = self._entry(mon, "JSON Body (set)", self.settings["body"], placeholder="{}")

        row = ctk.CTkFrame(mon, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        self.btn_start = ctk.CTkButton(row, text="Start (1s)", command=self.start_polling)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self.btn_stop = ctk.CTkButton(row, text="Stop", command=self.stop_polling, state="disabled", fg_color="#444", hover_color="#555")
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=(3, 0))
        self.btn_once = ctk.CTkButton(mon, text="Run Once (all)", command=self.run_once)
        self.btn_once.pack(fill="x", padx=8, pady=(0, 8))

        # PCS control
        pcs = ctk.CTkFrame(side)
        pcs.pack(fill="x", padx=10, pady=(6, 10))
        ctk.CTkLabel(pcs, text="PCS CONTROL (extension replica)", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=(6, 0))

        self.ent_power = self._entry(pcs, "Charge Run Power", "135")
        self.btn_charge = ctk.CTkButton(pcs, text="Save Charge Power", command=self.save_charge_threaded)
        self.btn_charge.pack(fill="x", padx=8, pady=(0, 6))
        self.btn_sequence = ctk.CTkButton(pcs, text="Run PCS Sequence (all devices)", command=self.pcs_sequence_threaded)
        self.btn_sequence.pack(fill="x", padx=8, pady=(0, 6))
        self.btn_retry = ctk.CTkButton(pcs, text="Retry Last Sequence", command=self.retry_sequence_threaded)
        self.btn_retry.pack(fill="x", padx=8, pady=(0, 8))

        self.lbl_bms = ctk.CTkLabel(pcs, text="BMS: -", font=ctk.CTkFont(size=11), text_color=COLOR_INFO)
        self.lbl_bms.pack(anchor="w", padx=8, pady=(0, 8))

    def _entry(self, parent, label, value, show=None, placeholder=None):
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=10)).pack(anchor="w", padx=8, pady=(4, 0))
        ent = ctk.CTkEntry(parent, show=show or "", placeholder_text=placeholder)
        ent.insert(0, value)
        ent.pack(fill="x", padx=8, pady=(2, 0))
        return ent

    def build_monitor(self):
        main = ctk.CTkFrame(self)
        main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=3)
        main.grid_rowconfigure(1, weight=2)

        # Table header
        head = ctk.CTkFrame(main)
        head.grid(row=0, column=0, sticky="new")
        self._grid_header(head, "REQUEST", 0)
        self._grid_header(head, "STATUS", 1)
        self._grid_header(head, "LATEST RESULT", 2)
        self._grid_header(head, "TIME", 3)

        self.table = ctk.CTkScrollableFrame(main, label_text="Realtime Requests (1s)")
        self.table.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        self.table.grid_columnconfigure(0, weight=1)
        self.table.grid_columnconfigure(2, weight=2)

        for i, req in enumerate(REALTIME_REQUESTS):
            self._add_row(i, req)

        # Details
        det = ctk.CTkFrame(main)
        det.grid(row=1, column=0, sticky="nsew")
        det.grid_columnconfigure(0, weight=1)
        det.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(det, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
        ctk.CTkLabel(top, text="DETAILS", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        self.detail_select = ctk.CTkOptionMenu(
            top,
            values=[req["label"] for req in REALTIME_REQUESTS],
            command=self.show_detail,
            width=320,
            font=ctk.CTkFont(size=11),
        )
        self.detail_select.pack(side="right")
        self.txt_detail = ctk.CTkTextbox(det, font=ctk.CTkFont(size=11), state="disabled")
        self.txt_detail.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)

    def _grid_header(self, parent, text, col):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_GRAY)
        lbl.grid(row=0, column=col, sticky="ew", padx=6, pady=4)

    def _add_row(self, i, req):
        name = ctk.CTkLabel(self.table, text=req["label"], anchor="w", font=ctk.CTkFont(size=11))
        name.grid(row=i, column=0, sticky="w", padx=6, pady=2)
        status = ctk.CTkLabel(self.table, text="pending", anchor="w", width=90, font=ctk.CTkFont(size=11))
        status.grid(row=i, column=1, sticky="w", padx=6, pady=2)
        data = ctk.CTkLabel(self.table, text="-", anchor="w", font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        data.grid(row=i, column=2, sticky="ew", padx=6, pady=2)
        ts = ctk.CTkLabel(self.table, text="-", anchor="w", width=80, font=ctk.CTkFont(size=10), text_color=COLOR_GRAY)
        ts.grid(row=i, column=3, sticky="w", padx=6, pady=2)
        self.row_widgets[req["id"]] = {"name": name, "status": status, "data": data, "ts": ts, "label": req["label"]}

    # ---------------------------------------------------------------- login
    def read_settings(self):
        try:
            device_ids = [int(x.strip()) for x in self.ent_device_ids.get().split(",") if x.strip()]
        except ValueError:
            device_ids = DEFAULT_DEVICE_IDS
        interval = float(self.ent_interval.get() or POLL_INTERVAL)
        self.settings.update({
            "base_url": self.ent_url.get().strip().rstrip("/"),
            "username": self.ent_user.get().strip(),
            "password": self.ent_pass.get(),
            "device_id": self.ent_device_id.get().strip() or "1",
            "device_ids": device_ids,
            "query": self.ent_query.get(),
            "body": self.ent_body.get(),
            "interval": interval,
        })

    def api_request(self, method, path, body=None, timeout=(5, 10)):
        if not self.token:
            self.login()
        url = f"{self.settings['base_url']}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json;charset=utf-8",
        }
        if method in ("GET", "HEAD"):
            resp = self.session.request(method, url, headers=headers, timeout=timeout)
        else:
            resp = self.session.request(method, url, headers=headers, json=body, timeout=timeout)
        return resp

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
            raise RuntimeError(f"Login failed: code={data.get('code')} message={data.get('message')}")
        self.token = data["data"]["token"]

    def login_threaded(self):
        threading.Thread(target=self._login_worker, daemon=True).start()

    def _login_worker(self):
        self.read_settings()
        try:
            self.login()
            self.lbl_login.configure(text=f"Logged in (token ok)", text_color=COLOR_GREEN)
            self.log("Login successful - starting realtime polling")
            self.after(0, self.start_polling)
        except Exception as e:
            self.last_error = str(e)
            self.lbl_login.configure(text=f"Login failed: {e}", text_color=COLOR_RED)
            self.log(f"Login FAILED: {e}")

    # ---------------------------------------------------------------- realtime
    def build_url(self, req, inputs):
        path = req["path"].replace("{deviceId}", requests.utils.quote(str(inputs.get("deviceId", "1"))))
        if req["transport"] == "sse" and "{" not in path:
            query = str(inputs.get("query", "")).strip()
            if query:
                sep = "&" if "?" in path else "?"
                path = f"{path}{sep}{query}"
        return f"{self.settings['base_url']}{path}"

    def fetch_sse(self, url, headers, max_events=5, window=3.0):
        events = []
        try:
            with self.session.get(url, headers=headers, stream=True, timeout=(3, 3)) as resp:
                if not resp.ok:
                    return {"ok": False, "status": resp.status_code, "method": "GET", "url": url, "data": resp.text[:500]}
                buffer = ""
                start = time.time()
                for raw in resp.iter_lines(decode_unicode=True):
                    if time.time() - start > window:
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
                                    events.append(payload)
                        if len(events) >= max_events:
                            break
                return {"ok": True, "status": resp.status_code, "method": "GET", "url": url, "events": events}
        except requests.exceptions.Timeout:
            return {"ok": False, "status": None, "method": "GET", "url": url, "events": events, "error": "timeout"}
        except Exception as e:
            return {"ok": False, "status": None, "method": "GET", "url": url, "events": events, "error": str(e)}

    def realtime_fetch(self, req, inputs):
        url = self.build_url(req, inputs)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json;charset=utf-8",
        }
        if req["transport"] == "sse":
            return self.fetch_sse(url, headers)
        if req["method"] in ("GET", "HEAD"):
            resp = self.session.request(req["method"], url, headers=headers, timeout=(5, 10))
        else:
            body = {}
            raw = str(inputs.get("body", "")).strip()
            if raw:
                body = json.loads(raw)
            resp = self.session.request(req["method"], url, headers=headers, json=body, timeout=(5, 10))
        text = resp.text
        try:
            data = json.loads(text)
        except Exception:
            data = text
        return {"ok": resp.ok, "status": resp.status_code, "method": req["method"], "url": url, "data": data}

    def start_polling(self):
        self.read_settings()
        self.stop_event.clear()
        if not self.token:
            try:
                self.login()
                self.lbl_login.configure(text="Logged in", text_color=COLOR_GREEN)
            except Exception as e:
                self.lbl_login.configure(text=f"Login failed: {e}", text_color=COLOR_RED)
                return
        if self.workers:
            return
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log(f"Polling started every {self.settings['interval']}s")
        for req in REALTIME_REQUESTS:
            t = threading.Thread(target=self.worker, args=(req,), daemon=True)
            t.start()
            self.workers.append(t)
        # BMS polling (every 5s, like the extension)
        b = threading.Thread(target=self.bms_worker, daemon=True)
        b.start()
        self.bms_worker = b

    def stop_polling(self):
        self.stop_event.set()
        self.workers = []
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.log("Polling stopped")

    def worker(self, req):
        interval = max(self.settings.get("interval", 1.0), 0.2)
        while not self.stop_event.is_set():
            try:
                result = self.realtime_fetch(req, self.current_inputs())
                with self.lock:
                    self.results[req["id"]] = {"label": req["label"], "result": result, "ts": time.time(), "error": None}
            except Exception as e:
                with self.lock:
                    self.results[req["id"]] = {"label": req["label"], "result": None, "ts": time.time(), "error": str(e)}
            self.stop_event.wait(interval)

    def current_inputs(self):
        return {
            "deviceId": self.settings.get("device_id", "1"),
            "query": self.settings.get("query", ""),
            "body": self.settings.get("body", "{}"),
        }

    def run_once(self):
        self.read_settings()
        if not self.token:
            try:
                self.login()
            except Exception as e:
                self.log(f"Login failed: {e}")
                return
        inputs = self.current_inputs()
        for req in REALTIME_REQUESTS:
            try:
                result = self.realtime_fetch(req, inputs)
                with self.lock:
                    self.results[req["id"]] = {"label": req["label"], "result": result, "ts": time.time(), "error": None}
            except Exception as e:
                with self.lock:
                    self.results[req["id"]] = {"label": req["label"], "result": None, "ts": time.time(), "error": str(e)}
        self.log("Run once complete")

    def show_detail(self, label):
        req_id = next((r["id"] for r in REALTIME_REQUESTS if r["label"] == label), None)
        if not req_id:
            return
        with self.lock:
            info = self.results.get(req_id)
        if not info:
            self._set_detail("No data yet for this request.\n")
            return
        self._render_detail(req_id, info)

    def _render_detail(self, req_id, info):
        if info.get("error"):
            self._set_detail(f"ERROR: {info['error']}\n")
            return
        result = info.get("result")
        if not result:
            self._set_detail("No response yet.\n")
            return
        req = next((r for r in REALTIME_REQUESTS if r["id"] == req_id), None)
        label = req["label"] if req else req_id
        lines = [f"{label}", f"Method : {result.get('method', '?')}  Status: {result.get('status', '?')}  OK: {result.get('ok')}",
                 f"URL    : {result.get('url', '')}"]
        if "events" in result:
            events = result.get("events") or []
            lines.append(f"SSE events ({len(events)}):")
            for i, ev in enumerate(events):
                try:
                    parsed = json.loads(ev)
                except Exception:
                    parsed = ev
                lines.append(f"  event #{i + 1}: {json.dumps(parsed, ensure_ascii=False, indent=2)}")
        else:
            data = result.get("data")
            lines.append("Body:")
            lines.append(json.dumps(data, ensure_ascii=False, indent=2) if not isinstance(data, str) else data)
        ts = info.get("ts")
        if ts:
            lines.append(f"\nFetched at {datetime.fromtimestamp(ts).strftime('%H:%M:%S')}")
        self._set_detail("\n".join(lines) + "\n")

    def _set_detail(self, text):
        self.txt_detail.configure(state="normal")
        self.txt_detail.delete("1.0", "end")
        self.txt_detail.insert("1.0", text)
        self.txt_detail.configure(state="disabled")

    # ---------------------------------------------------------------- BMS
    def bms_worker(self):
        while not self.stop_event.is_set():
            try:
                if self.token:
                    for did in self.settings.get("device_ids", []):
                        resp = self.api_request(
                            "POST",
                            "/v1/history-data?page=1&page-size=1",
                            {"device_id": did, "device_type": 2, "fields": ["bms_running_status", "bms_soc"]},
                        )
                        data = resp.json()
                        items = (data.get("data") or {}).get("list") or []
                        if items:
                            latest = items[0]
                            self.bms_soc = latest.get("bms_soc")
                            self.bms_status = latest.get("bms_running_status")
                            self.lbl_bms.configure(
                                text=f"BMS dev {did}: SOC {self.bms_soc}%  running_status={self.bms_status}",
                                text_color=COLOR_GREEN,
                            )
                            break
            except Exception as e:
                self.lbl_bms.configure(text=f"BMS error: {e}", text_color=COLOR_RED)
            self.stop_event.wait(5)

    # ---------------------------------------------------------------- PCS
    def run_pcs_sequence(self, device_id):
        logs = []
        for step in PCS_SEQUENCE:
            try:
                resp = self.api_request(step["method"], step["path"](device_id), step["body"])
                data = resp.json()
                code = data.get("code")
                if not resp.ok or (code not in (0, None)):
                    raise RuntimeError(f"{step['label']} failed: status={resp.status_code} code={code} message={data.get('message')}")
                logs.append(f"  [OK] {step['label']} dev {device_id}")
            except Exception as e:
                logs.append(f"  [FAIL] {step['label']} dev {device_id}: {e}")
                raise
        return logs

    def pcs_sequence_threaded(self):
        self.read_settings()
        if not self.token:
            try:
                self.login()
            except Exception as e:
                self.log(f"Login failed: {e}")
                return
        threading.Thread(target=self._pcs_seq_worker, daemon=True).start()

    def _pcs_seq_worker(self):
        self.log("PCS sequence started")
        for did in self.settings.get("device_ids", []):
            try:
                logs = self.run_pcs_sequence(did)
                for l in logs:
                    self.log(l)
            except Exception as e:
                self.log(f"Sequence FAILED for dev {did}: {e}")
        self.log("PCS sequence finished")

    def save_charge_threaded(self):
        self.read_settings()
        try:
            power = int(self.ent_power.get())
        except ValueError:
            self.log("Invalid charge power")
            return
        threading.Thread(target=self._save_charge_worker, args=(power,), daemon=True).start()

    def _save_charge_worker(self, run_power):
        try:
            if not self.token:
                self.login()
            body = {
                "status": 1,
                "month": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                "week_day": [0, 1, 2, 3, 4, 5, 6],
                "device_ids": [1, 2, 3, 4, 6],
                "settings": [{"start_hour": 0, "start_minute": 0, "end_hour": 23, "end_minute": 59, "cdc_enable_mode": 2, "run_power": run_power}],
                "charge_type": 1,
                "mode": 2,
            }
            resp = self.api_request("PATCH", "/v1/photovoltaic-charge/2", body)
            data = resp.json()
            code = data.get("code")
            if not resp.ok or (code not in (0, None)):
                raise RuntimeError(f"code={code} message={data.get('message')}")
            self.log(f"Charge power saved: {run_power}")
        except Exception as e:
            self.log(f"Save charge FAILED: {e}")

    def retry_sequence_threaded(self):
        self.log("Retry last sequence")
        self.pcs_sequence_threaded()

    # ---------------------------------------------------------------- display
    def update_display(self):
        with self.lock:
            snapshot = {k: dict(v) for k, v in self.results.items()}
        for req_id, info in snapshot.items():
            w = self.row_widgets.get(req_id)
            if not w:
                continue
            ts = info.get("ts")
            w["ts"].configure(text=datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "-")
            if info.get("error"):
                w["status"].configure(text="ERROR", text_color=COLOR_RED)
                w["data"].configure(text=info["error"], text_color=COLOR_RED)
            elif info.get("result"):
                result = info["result"]
                ok = result.get("ok")
                status_text = f"{result.get('method', '?')} {result.get('status', '?')}"
                w["status"].configure(text=status_text, text_color=COLOR_GREEN if ok else COLOR_RED)
                w["data"].configure(text=self._short(result), text_color=COLOR_INFO if ok else COLOR_RED)
            else:
                w["status"].configure(text="pending", text_color=COLOR_GRAY)
                w["data"].configure(text="-", text_color=COLOR_GRAY)
        selected = self.detail_select.get()
        req_id = next((r["id"] for r in REALTIME_REQUESTS if r["label"] == selected), None)
        if req_id and req_id in snapshot:
            self._render_detail(req_id, snapshot[req_id])
        self.after(500, self.update_display)

    def _short(self, result):
        if "events" in result:
            events = result.get("events") or []
            if events:
                return json.dumps(events[-1], ensure_ascii=False)[:100]
            return "no events"
        data = result.get("data")
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        return text[:100]

    def log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_detail.configure(state="normal")
        self.txt_detail.insert("end", f"[{ts}] {message}\n")
        self.txt_detail.see("end")
        self.txt_detail.configure(state="disabled")


if __name__ == "__main__":
    app = PcsRealtimeMonitor()
    app.mainloop()
