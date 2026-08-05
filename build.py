#!/usr/bin/env python3
"""Build a standalone executable app with PyInstaller.

Usage:
    conda activate PCS
    pip install -r requirements.txt
    python build.py

Outputs:
    macOS   -> dist/PCS-Realtime-Monitor.app
    Windows -> dist/PCS-Realtime-Monitor.exe
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON_SRC = ROOT.parent / "pcs-control" / "icon128.png"
ICON_PNG = ROOT / "icon.png"
APP_NAME = "PCS-Realtime-Monitor"
MAIN = ROOT / "main.py"


def ensure_icon():
    if not ICON_PNG.exists():
        if ICON_SRC.exists():
            shutil.copy(ICON_SRC, ICON_PNG)
            print(f"Copied icon from {ICON_SRC}")
        else:
            print("WARNING: icon source not found, building without custom icon")
            return None
    return ICON_PNG


def make_ico(png):
    ico = ROOT / "icon.ico"
    try:
        from PIL import Image

        img = Image.open(png).convert("RGBA")
        img.save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return ico
    except Exception as e:
        print(f"WARNING: could not build icon.ico ({e})")
        return None


def make_icns(png):
    if sys.platform != "darwin":
        return None
    icns = ROOT / "icon.icns"
    iconset = ROOT / "icon.iconset"
    iconset.mkdir(exist_ok=True)
    try:
        from PIL import Image

        img = Image.open(png).convert("RGBA")
        for size in (16, 32, 128, 256, 512):
            img.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
            if size * 2 <= 1024:
                img.resize((size * 2, size * 2), Image.LANCZOS).save(iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)], check=True)
        return icns
    except Exception as e:
        print(f"WARNING: could not build icon.icns ({e})")
        return None


def main():
    icon = ensure_icon()

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
    ]

    if icon:
        cmd += ["--add-data", f"{icon}{os.pathsep}."]
        if sys.platform == "darwin":
            icns = make_icns(icon)
            if icns:
                cmd += ["--icon", str(icns)]
        else:
            ico = make_ico(icon)
            if ico:
                cmd += ["--icon", str(ico)]

    cmd.append(str(MAIN))

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    if sys.platform == "darwin":
        out = ROOT / "dist" / f"{APP_NAME}.app"
    else:
        out = ROOT / "dist" / f"{APP_NAME}.exe"
    print(f"\nDone. Executable at: {out}")


if __name__ == "__main__":
    main()
