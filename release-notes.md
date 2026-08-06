## PCS Realtime Monitor v1.0.0

First stable release of the desktop dashboard for the PCS (Power Conversion System) inverter/battery system. A Python + CustomTkinter app that replicates the `pcs-control` Chrome extension with a live, always-on dashboard.

### Features

- **Login-first flow** – server URL, username and password (defaults `http://192.168.0.123`, `admin` / `aiWatt+0`); dashboard appears only after a successful login.
- **Photovoltaic monitoring (PV1–PV5)** – subscribes to the realtime SSE stream `GET /v1/sse/photovoltaic` every second and shows one card per device with live `alternating_current_output_power` (kW). Robust SSE reader handles CRLF, idle streams and timeouts without erroring.
- **Battery (BMS) SOC monitoring** – polls `POST /v1/history-data` every 5s for every BMS device (default IDs 2, 3), showing SOC % with a progress bar and status (Standby / Running / Charging / Discharging).
- **Run PCS sequence** – stop → fault reset → system operate reset → device startup, in one click for **both batteries** or **per battery** (BMS 2 / BMS 3), with live per-step status and error reporting.
- **PV power control** – set `run_power` (kW) via `PATCH /v1/photovoltaic-charge/2`, with success/failure feedback.
- **Clean dark UI** – scrollable dashboard, auto-rendered device cards, log out returns to login.
- **Packaged executables** – PyInstaller single-file build for macOS (`.app`) and Windows (`.exe`) with app icon via `build.py`.

### Install / run

```bash
pip install -r requirements.txt
python3 main.py
```

Full build instructions for packaged executables are in the README.

### Notes

- Requires network access to the PCS server (default `http://192.168.0.123`).
- Devices auto-detected from the live SSE stream; BMS device IDs configurable in `main.py`.
