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
- **Log out** – stops polling and returns to the login screen.
