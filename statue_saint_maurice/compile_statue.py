"""Compile and verify Saint-Maurice statue's KTX2; never install automatically."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "realearth-saint-maurice-vierge"
SDK = Path(r"D:\RealEarth2024\build\tools\fspackagetool.exe")
subprocess.run([sys.executable, str(ROOT / "prepare_statue.py")], check=True)
if sys.platform != "win32":
    print("SOURCE QA OK (no SDK available on this OS).")
    raise SystemExit(0)
if not SDK.is_file():
    raise SystemExit("MSFS SDK package tool missing: " + str(SDK))
project = ROOT / "project"
output = project / "Packages" / NAME
if output.exists():
    shutil.rmtree(output)  # prevent a stale build being considered successful
print("OFFICIAL SDK BUILD:", project / (NAME + ".xml"), flush=True)
result = subprocess.run([str(SDK), str(project / (NAME + ".xml"))], cwd=project)
if result.returncode:
    raise SystemExit("SDK compile failed: exit " + str(result.returncode))

start = time.monotonic()
stable = 0
previous = None
while time.monotonic() - start < 900:
    try:
        mf = output / "manifest.json"
        ly = output / "layout.json"
        manifest = json.loads(mf.read_text(encoding="utf-8-sig"))
        layout = json.loads(ly.read_text(encoding="utf-8-sig"))
        ktx = [p for p in output.rglob("*.KTX2")
               if p.name.lower() == "monument_vierge_albedo.png.ktx2"]
        bgl = list(output.rglob("*.BGL"))
        pos = json.loads((ROOT / "placement.json").read_text())
        required_bgls = 2 if pos.get("latitude") is not None else 1
        valid = (manifest.get("package_version") == "0.1.1" and
                 len(ktx) == 1 and len(bgl) >= required_bgls and
                 any(p.name.lower() == "modellib.bgl" and p.stat().st_size > 10000 for p in bgl) and
                 len(layout.get("content", [])) >= 2)
        if valid:
            valid = ktx[0].read_bytes()[:12] == bytes.fromhex("ab4b5458203230bb0d0a1a0a")
            valid = valid and all(
                (output / ent["path"]).is_file() and
                (output / ent["path"]).stat().st_size == ent["size"]
                for ent in layout["content"]
            )
        if valid:
            items = ktx + bgl + [ly]
            signature = tuple((p.name, p.stat().st_size, p.stat().st_mtime_ns)
                              for p in items)
            stable = stable + 1 if signature == previous else 0
            previous = signature
            if stable >= 4:
                break
        else:
            stable, previous = 0, None
    except (OSError, ValueError, KeyError, TypeError):
        stable, previous = 0, None
    time.sleep(3)
else:
    raise SystemExit("SDK failed to produce valid KTX2/BGL/layout output. Community unchanged.")

dest = ROOT / "dist" / NAME
if dest.exists():
    shutil.rmtree(dest)
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(output, dest)
print("SDK TEXTURE AND LOD QA: OK v0.1.1 - 1 KTX2, " + str(len(bgl)) + " BGL")
print("Package ready:", dest)
print("Nothing was installed to Community. Verify GPS first.")
