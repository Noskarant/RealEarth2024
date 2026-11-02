"""Publish the compiled package and add pre-encoded runtime textures."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(r"D:\RealEarth2024")
BUILT = ROOT / "project" / "Packages" / "realearth-valmorel-hd"
DIST = ROOT / "dist" / "realearth-valmorel-hd"


def filetime(path: Path) -> int:
    return int(path.stat().st_mtime_ns // 100 + 116444736000000000)


def main() -> None:
    if not (BUILT / "manifest.json").is_file():
        raise FileNotFoundError("compiled package is missing")
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(BUILT, DIST)

    manifest_path = DIST / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["total_package_size"] = str(sum(
        p.stat().st_size for p in DIST.rglob("*")
        if p.is_file() and p.name.lower() not in {"layout.json", "manifest.json"}
    ))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    content = []
    for path in sorted(DIST.rglob("*")):
        if not path.is_file() or path.name.lower() in {"layout.json", "manifest.json"}:
            continue
        content.append({
            "path": path.relative_to(DIST).as_posix().lower(),
            "size": path.stat().st_size,
            "date": filetime(path),
        })
    (DIST / "layout.json").write_text(
        json.dumps({"content": content}, indent=2), encoding="utf-8")
    print(f"published {DIST}: texture-free, {len(content)} entries")


if __name__ == "__main__":
    main()
