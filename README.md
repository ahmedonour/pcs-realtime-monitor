# PCS Realtime Monitor

A Python / [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) desktop app that replicates the `pcs-control` Chrome extension and adds a realtime dashboard that polls every endpoint every 1 second and shows the results on screen.

## Install

```bash
cd pcs-realtime-monitor
pip install -r requirements.txt
```

On macOS the system Python usually ships with `tkinter`; if you use a Homebrew/managed Python, install tkinter too (`brew install python-tk@3.13` or similar).

## Run

```bash
python3 main.py
```

## Build executable with icon (PyInstaller)

`build.py` builds a single-file, windowed executable and applies the `pcs-control/icon128.png` logo both as the runtime window icon and as the OS app/executable icon.

### Step-by-step

```bash
cd pcs-realtime-monitor

# 1. (recommended) create + activate a conda env
conda create --name PCS python=3.13 -y
conda activate PCS

# 2. install runtime + build deps (pyinstaller, pillow)
pip install -r requirements.txt

# 3. build the executable
python build.py
```

### Output

| Platform | Executable |
|----------|------------|
| macOS    | `dist/PCS-Realtime-Monitor.app` |
| Windows  | `dist/PCS-Realtime-Monitor.exe` |

### How the icon is handled

- **Runtime window icon** – `build.py` copies `../pcs-control/icon128.png` to `icon.png`, and `main.py` loads it via `tk.PhotoImage` (through `resource_path()`, which also resolves inside the PyInstaller bundle). It is bundled into the app with `--add-data`.
- **App/executable icon**:
  - macOS: `build.py` generates an `.icns` from `icon.png` (resizes with Pillow, then `iconutil`) and passes it via `--icon`.
  - Windows: generates a multi-size `.ico` with Pillow and passes it via `--icon`.

### Rebuilding after changes

```bash
python build.py   # always wipes the previous build (--noconfirm --clean)
```

### If you hit a permission error launching the .app (macOS)

```bash
xattr -dr com.apple.quarantine dist/PCS-Realtime-Monitor.app
```

## What it does

- **Login screen first** – enter server URL, username and password (defaults: `http://192.168.0.123`, `admin` / `aiWatt+0`) and press **Login**. Only after a successful login does the dashboard appear.
- **Photovoltaic devices (PV1..PV5)** – subscribes to the realtime SSE stream `GET /v1/sse/photovoltaic?purpose=2&pageSize=12&page=1` every 1 second and shows **one card per device** with its name and `alternating_current_output_power` in kW. The `list` of devices is parsed automatically (falls back to single-device events).
- **Battery (BMS) SOC** – polls the extension's history request `POST /v1/history-data?page=1&page-size=1` (`device_type: 2`, fields `bms_soc` + `bms_running_status`) every 5 seconds for **every BMS device** (default IDs `2, 3`), showing SOC% with a progress bar and status (Standby / Running / Charging / Discharging).
- **Active faults** – polls `GET /v1/alarm?page=1&page-size=50&handle-status=1` every second and shows a scrollable **FAULTS** panel beside the battery cards: each row shows the device name, alarm content and occurrence time (critical alarms in red, warnings in orange).
- **Log out** – stops polling and returns to the login screen.

## Automation

The **CONTROL** section evaluates rule-based PV power adjustments every 30 seconds and applies them automatically. **Start Automation** / **Download Log** buttons sit in the CONTROL section; every decision is written to a daily CSV log.

### Rules (evaluated in priority order)

1. **Rule 3 – Battery SOC** (highest priority)
   - Any BMS SOC ≥ 95% → decrease PV power in 5 kW steps until ESS1/ESS2 PCS active power is inside **−25 … −15 kW** (discharging); if it drops below −25 kW, raise PV instead.
   - Any BMS SOC ≤ 85% → increase PV power in 5 kW steps while the ESS is charging (negative power), until ESS power becomes positive.
2. **Rule 2 – Hot window** – between 10:00 and 18:00 with outside temperature ≥ 35 °C: set PV power = **|GateMeter| − 20 kW**, nudging up/down in 5 kW steps to keep ESS1/ESS2 PCS power inside **10–20 kW**.
3. **Rule 1 – Gate meter negative** – GateMeter ≤ 0: set PV power = **|GateMeter| + 20 kW**.

PV power is applied through the same request the **Apply** button uses (`PATCH /v1/photovoltaic-charge/2`). Gate power comes from `GateMeter.total_active` and ESS power from `pcs_total_active_power`, both read from the `/v1/sse/power-group` stream.

### Weather

Outside temperature comes from [Open-Meteo](https://open-meteo.com) — no API key — using the machine's location, auto-detected via IP geolocation (ipify + ipapi.co, fallback ipwho.is). Readings are cached for 10 minutes and shown on the bottom status bar with the location and a live clock.

### Daily logs

Every automation tick appends a CSV row to `~/.pcs-realtime-monitor/logs/automation_YYYY-MM-DD.csv`:

| Column | Meaning |
|--------|---------|
| `timestamp` | When the rule ran |
| `rule` | Rule id (`rule1-gate-negative`, `rule2-hot`, `rule3-soc-high`, `rule3-soc-recover`, `idle`) |
| `action` | What the rule decided |
| `gate_kw` / `ess1_kw` / `ess2_kw` | Current GateMeter / ESS1 / ESS2 power (kW) |
| `pv_current_kw` / `pv_target_kw` | PV power before / after the decision (kW) |
| `temp_c` / `soc` | Temperature (°C) / highest SOC (%) at decision time |
| `applied` | `yes` if the PV setpoint was changed |

**Download Log** opens a picker of the available days and saves the chosen CSV to any location.

### Running automation

- Press **Start Automation** (green). The button turns red (**Stop Automation**) while active. The automation worker is registered alongside the realtime workers, so no manual polling setup is needed.
- Logging out or pressing the button stops automation and resets it to **Start Automation**.
- The whole feature needs no extra Python packages — only the standard library plus `requests` (already a dependency).

## Bottom status bar and themes

The bottom bar shows the current weather, location and live clock. It also has two icon buttons:

- **⚙ Settings** – opens a dialog to adjust the automation parameters (interval, PV step, PV min/max, hot-temp threshold, SOC high/recover).
- **🌙 / ☀ Theme** – switches between dark and light mode and rebuilds the dashboard with the matching palette.
