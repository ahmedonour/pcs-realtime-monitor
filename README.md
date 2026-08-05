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

- **Login** – `POST /v1/user/login` (defaults: `http://192.168.0.123`, `admin` / `aiWatt+0`). Edit the fields and press **Login**.
- **Realtime Monitor** – polls all 10 endpoints from the extension's `realTime-Cs21J90M.js` every interval (default **1s**), each request in its own thread:
  - `GET /v1/actual-time/bms-clusters/{deviceId}`
  - `GET /v1/actual-time/total/{deviceId}` (SSE)
  - `GET /v1/sse/charge-pail` (SSE)
  - `GET /v1/sse/photovoltaic` (SSE)
  - `GET /v1/sse/relay-protection` (SSE)
  - `GET /v1/sse/transformer-temperature-controller` (SSE)
  - `GET /v1/sse/dido` (SSE)
  - `GET /v1/sse/temperature-humidity-controller` (SSE)
  - `GET /v1/system-setting/realtime-data-col`
  - `PUT /v1/system-setting/realtime-data-col` (body from the JSON Body field)
- **Table** – one row per request showing method/status, latest result (truncated) and timestamp. Pick a request in the **Details** dropdown to see its full JSON.
- **PCS Control** (extension replica) – Run PCS sequence (Stop → Fault reset → System operate reset → Device startup, `PATCH /v1/pcs-control/{id}`), Save Charge Power (`PATCH /v1/photovoltaic-charge/2`), and BMS polling (`POST /v1/history-data`, every 5s).

## Controls

- **Start (1s)** – begins polling all requests + BMS every interval.
- **Stop** – stops all polling threads.
- **Run Once (all)** – single pass over all requests.
- SSE endpoints are read as streams for ~3s per poll (up to 5 events) since the server keeps the connection open; a plain GET would block forever.
