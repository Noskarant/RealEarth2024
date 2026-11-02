"""Install the validated Madone du Peu package without touching Valmorel."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "realearth-saint-maurice-vierge"
SRC = ROOT / "dist" / NAME
BACKUPS = ROOT / "backups"


def sim_running() -> bool:
    if os.name != "nt":
        return False
    cmd = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True, check=False)
    return any(name in cmd.stdout.lower() for name in
               ("flightsimulator2024.exe", "flightsimulator.exe"))


def find_community() -> Path:
    appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    localapp = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    cfgs = [
        localapp / "Packages" / "Microsoft.Limitless_8wekyb3d8bbwe" / "LocalCache" / "UserCfg.opt",
        appdata / "Microsoft Flight Simulator 2024" / "UserCfg.opt",
    ]
    candidates: list[Path] = []
    for cfg in cfgs:
        if cfg.is_file():
            m = re.search(r'^\s*InstalledPackagesPath\s+"([^"]+)"',
                          cfg.read_text(encoding="utf-8", errors="replace"), re.M)
            if m:
                base = Path(os.path.expandvars(m.group(1)))
                candidates.extend((base / "Community", base / "Community2024"))
    candidates.extend([
        localapp / "Packages" / "Microsoft.Limitless_8wekyb3d8bbwe" /
        "LocalCache" / "Packages" / "Community",
        appdata / "Microsoft Flight Simulator 2024" / "Packages" / "Community",
    ])
    existing = list(dict.fromkeys(p for p in candidates if p.is_dir()))
    with_old = [p for p in existing if (p / NAME).is_dir()]
    if len(with_old) == 1:
        return with_old[0]
    if len(existing) == 1:
        return existing[0]
    print("Community location is ambiguous; candidates:", *existing, sep="\n - ")
    supplied = input("Paste the EXACT Community folder path (Enter cancels): ").strip().strip('"')
    if not supplied:
        raise ValueError("No Community folder supplied")
    path = Path(supplied)
    if not path.is_dir() or path.name.lower() not in ("community", "community2024"):
        raise ValueError(f"Invalid Community path: {path}")
    return path


def validate() -> None:
    placement = json.loads((ROOT / "placement.json").read_text(encoding="utf-8"))
    if placement.get("latitude") is None or placement.get("longitude") is None:
        raise ValueError("No confirmed monument GPS; refusing installation")
    manifest = json.loads((SRC / "manifest.json").read_text(encoding="utf-8-sig"))
    layout = json.loads((SRC / "layout.json").read_text(encoding="utf-8-sig"))
    if manifest.get("package_version") != "0.1.0" or not layout.get("content"):
        raise ValueError("Incorrect package manifest or layout")
    if len(list(SRC.rglob("*.BGL"))) < 2:
        raise ValueError("Scenery placement BGL was not compiled")
    textures = list(SRC.rglob("*.KTX2"))
    expected = next((p for p in textures if
                     p.name.upper() == "MONUMENT_VIERGE_ALBEDO.PNG.KTX2"), None)
    if expected is None or expected.read_bytes()[:12] != bytes.fromhex(
            "ab4b5458203230bb0d0a1a0a"):
        raise ValueError("Missing or invalid official SDK KTX2 texture")
    for ent in layout["content"]:
        file = SRC / ent["path"]
        if not file.is_file() or file.stat().st_size != ent["size"]:
            raise ValueError("Layout mismatch: " + ent["path"])
    print("VALIDATED:", len(textures), "KTX2, GPS", placement["latitude"],
          placement["longitude"])


def main() -> None:
    if sim_running():
        print("FS2024 is still running: installation has NOT started.")
        print("Close the simulator normally, then press Enter to retry.")
        while sim_running():
            answer = input("Press Enter after closing FS2024, or Q to cancel: ").strip().lower()
            if answer in ("q", "quit", "n", "no"):
                raise ValueError("Cancelled; existing Community package unchanged")
        print("FS2024 is closed; continuing installation.")
    validate()
    community = find_community()
    target = community / NAME
    uid = uuid.uuid4().hex[:8]
    stage = community / ("." + NAME + "_stage_" + uid)
    old = community / ("." + NAME + "_old_" + uid)
    moved = False
    installed = False
    try:
        shutil.copytree(SRC, stage)
        if len(list(stage.rglob("*.KTX2"))) != len(list(SRC.rglob("*.KTX2"))):
            raise ValueError("Staged Community copy has missing textures")
        if sim_running():
            raise ValueError("FS2024 was started during the build")
        if target.exists():
            BACKUPS.mkdir(parents=True, exist_ok=True)
            backup = BACKUPS / (NAME + "_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uid)
            shutil.copytree(target, backup)
            if not (backup / "manifest.json").exists():
                raise ValueError("Existing add-on backup incomplete")
            print("Previous statue backed up:", backup)
            target.rename(old)
            moved = True
        stage.rename(target)
        installed = True
        if old.exists():
            shutil.rmtree(old)
        print("SUCCESS: installed statue to", target)
        print("You can now open MSFS 2024 and inspect the monument.")
    except Exception:
        if moved and not installed and old.exists():
            if target.exists():
                shutil.rmtree(target)
            old.rename(target)
            print("Previous version restored")
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("INSTALLATION STOPPED:", error)
        sys.exit(1)
