"""Structural validation of the built Community package.

Checks that what will be copied into Community is self-consistent: required
files, layout/disk size match, BGL magic, no dangling texture references.
This does NOT replace an in-simulator test.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PKG = Path(r"D:\RealEarth2024\dist\realearth-valmorel-hd")
REQUIRED = ["manifest.json", "layout.json"]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for name in REQUIRED:
        if not (PKG / name).is_file():
            errors.append(f"missing {name}")

    manifest = {}
    if (PKG / "manifest.json").is_file():
        manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
        for key in ("content_type", "title", "manufacturer", "creator",
                    "package_version", "minimum_game_version"):
            if key not in manifest:
                errors.append(f"manifest missing key: {key}")

    layout = {"content": []}
    if (PKG / "layout.json").is_file():
        layout = json.loads((PKG / "layout.json").read_text(encoding="utf-8"))
        if not layout.get("content"):
            errors.append("layout.json has no content entries")

    declared = set()
    for entry in layout.get("content", []):
        p = PKG / entry["path"]
        declared.add(entry["path"].lower())
        if not p.is_file():
            errors.append(f"layout references missing file: {entry['path']}")
            continue
        if p.stat().st_size != entry["size"]:
            errors.append(
                f"size mismatch {entry['path']}: layout={entry['size']} "
                f"disk={p.stat().st_size}")

    for p in PKG.rglob("*"):
        if p.is_file():
            rel = p.relative_to(PKG).as_posix().lower()
            if rel in ("manifest.json", "layout.json"):
                continue
            if rel not in declared:
                warnings.append(f"file not declared in layout.json: {rel}")

    # MSFS/FSX BGL signature is the little-endian 0x19920201 marker.
    BGL_MAGIC = b"\x01\x02\x92\x19"
    for bgl in PKG.rglob("*.BGL"):
        head = bgl.read_bytes()[:4]
        if head != BGL_MAGIC:
            errors.append(f"{bgl.name}: unexpected header {head!r}")

    total = sum(p.stat().st_size for p in PKG.rglob("*") if p.is_file())
    bgls = sorted(p.name for p in PKG.rglob("*.BGL"))
    bout = sorted(p.name for p in PKG.rglob("*.bout"))
    textures = sorted(PKG.rglob("*.KTX2"))
    if not textures:
        errors.append("no SDK-generated KTX2 runtime textures")
    for texture in textures:
        if texture.read_bytes()[:12] != bytes.fromhex("ab4b5458203230bb0d0a1a0a"):
            errors.append(f"{texture.name}: invalid KTX2 signature")

    print(f"package : {PKG}")
    print(f"size    : {total/1024/1024:.2f} MiB")
    print(f"BGL     : {bgls}")
    print(f"bglIndex: {bout}")
    print(f"KTX2    : {len(textures)}")
    print(f"entries : {len(layout.get('content', []))}")
    print(f"manifest: {manifest.get('title')} v{manifest.get('package_version')} "
          f"(min sim {manifest.get('minimum_game_version')})")
    for w in warnings:
        print("WARN   :", w)
    for e in errors:
        print("ERROR  :", e)
    print("RESULT  :", "OK" if not errors else f"{len(errors)} error(s)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
