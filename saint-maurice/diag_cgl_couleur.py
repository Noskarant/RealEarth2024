"""Diagnostic hors simulateur : que stocke reellement le compilateur CGL ?

Compile un mini-package de tuiles synthetiques de couleurs pures, puis analyse
les octets du .cgl produit pour retrouver la conversion RGB565 (BC1/BC3) et
verifier l'ordre des canaux et la gestion de l'alpha.

Usage :
    python diag_cgl_couleur.py --build      # cree les tuiles et compile
    python diag_cgl_couleur.py --analyse    # analyse un CGL deja compile
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_ortho import quadkey  # noqa: E402

WORK = Path(r"D:\RSM24S\DIAG_COULEUR")
SLUG = "diag-cgl-couleur"
CENTER = (537777, 374785)  # tuile LOD20 de Saint-Maurice

# nom, couleur RGBA 16 bits
CAS = [
    ("rouge",      (65535, 0, 0, 65535)),
    ("vert",       (0, 65535, 0, 65535)),
    ("bleu",       (0, 0, 65535, 65535)),
    ("blanc",      (65535, 65535, 65535, 65535)),
    ("gris_moyen", (32768, 32768, 32768, 65535)),
    ("rouge_alpha0", (65535, 0, 0, 0)),
    ("blanc_alpha50", (65535, 65535, 65535, 32768)),
    ("noir",       (0, 0, 0, 65535)),
]


def rgb565(r: int, g: int, b: int) -> int:
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def build_tiles() -> Path:
    import cv2

    dst = WORK / "PackageSources" / "CGL" / "aerial_images"
    dst.mkdir(parents=True, exist_ok=True)
    cx, cy = CENTER
    for i, (nom, (r, g, b, a)) in enumerate(CAS):
        rgba = np.zeros((256, 256, 4), dtype=np.uint16)
        rgba[..., 0] = r
        rgba[..., 1] = g
        rgba[..., 2] = b
        rgba[..., 3] = a
        bgra = np.dstack((rgba[..., 2], rgba[..., 1], rgba[..., 0], rgba[..., 3]))
        target = dst / f"{quadkey(cx + i, cy)}.png"
        if not cv2.imwrite(str(target), bgra):
            raise OSError(target)
        print(f"  tuile {nom:14s} {target.name} RGBA16={r},{g},{b},{a}")
    # configuration CGL identique au projet reel
    (WORK / "PackageSources" / "CGL" / "CGLBuilderConfig.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<CGLBuilder>\n"
        '  <CGL type="SecondaryAerialImage" input="Tiles" directory="aerial_images"/>\n'
        "</CGLBuilder>\n", encoding="utf-8")
    return dst


def build_package() -> Path:
    import compiler_fiable as C

    build_tiles()
    project = C.make_project(WORK, SLUG,
                             [("sm_cgl", "CGL", 0, "PackageSources\\CGL\\", "CGL\\")])
    sdk = C.get_sdk()
    C.clean_build_helpers()
    pkg, code, secs = C.sdk_compile(sdk, project, SLUG, 900, WORK, "diag")
    print(f"compilation : {secs:.0f}s, exit {code}")
    print(f"package     : {pkg}")
    return pkg


def find_cgl(root: Path) -> Path:
    files = list(root.rglob("*.cgl"))
    if not files:
        raise SystemExit(f"aucun .cgl sous {root}")
    return max(files, key=lambda p: p.stat().st_size)


def analyse(root: Path) -> None:
    f = find_cgl(root)
    data = f.read_bytes()
    print(f"\nCGL : {f}")
    print(f"taille : {len(data)} octets")
    print("entete:", data[:64].hex(" "))
    print("ascii :", "".join(chr(b) if 32 <= b <= 126 else "." for b in data[:64]))

    print("\n--- recherche des codes RGB565 des couleurs pures (BC1/BC3) ---")
    for nom, (r, g, b, a) in CAS:
        c8 = (r >> 8, g >> 8, b >> 8)
        code = rgb565(*c8)
        motif = struct.pack("<H", code) * 2
        n = data.count(motif)
        print(f"  {nom:14s} RGB8={c8} RGB565=0x{code:04X} motif {motif.hex()} -> {n} occurrences")

    print("\n--- recherche brute des octets de couleur (non compresse) ---")
    for nom, (r, g, b, a) in CAS:
        c8 = bytes((r >> 8, g >> 8, b >> 8))
        print(f"  {nom:14s} {c8.hex()} -> {data.count(c8)} occurrences")

    # statistiques sur la zone de donnees (apres l'entete)
    body = data[128:]
    print("\n--- entropie / structure ---")
    print("taille corps:", len(body))
    print("premiers octets du corps:", body[:48].hex(" "))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--dossier", default="")
    args = ap.parse_args()
    root = Path(args.dossier) if args.dossier else WORK
    if args.build:
        pkg = build_package()
        analyse(pkg)
    elif args.analyse:
        analyse(root)
    else:
        analyse(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
