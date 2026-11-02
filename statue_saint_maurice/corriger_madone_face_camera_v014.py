"""Madone du Peu (MSFS 2024): rotate the whole installed monument +90 degrees,
and move its GPS base 2 m south, preserving model, statue yaw, scale and height.

This is a one-time, guarded local patch. No change to Valmorel.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_BASE = Path(r"D:\RealEarth2024")
MARKER = "camera_alignment_v014"
ROTATION_DEG = 90.0
SHIFT_M = 2.0
SHIFT_BEARING_DEG = 180.0  # south: last requested viewpoint is south of monument


def source_complete(root: Path) -> bool:
    source = root / "source"
    return (all((root / name).is_file() for name in
                ("placement.json", "compile_statue.py", "prepare_statue.py", "install_statue.py"))
            and all((source / name).is_file() for name in
                    ("monument_vierge.gltf", "monument_vierge.bin"))
            and any((source / name).is_file() for name in
                    ("texture/monument_vierge_albedo.png", "mesh_Model_4_u1_v1_diffuse.png")))


def find_project(explicit: str | None) -> Path:
    if explicit:
        selected = Path(explicit).expanduser()
        if not source_complete(selected):
            raise ValueError(f"Source 3D / scripts incomplets dans : {selected}")
        return selected
    base = DEFAULT_BASE
    preferred = base / "vierge_saint_maurice_4K_GPS_installation" / "statue_saint_maurice"
    if source_complete(preferred):
        return preferred
    candidates = [p.parent for p in base.rglob("placement.json")
                  if source_complete(p.parent)] if base.is_dir() else []
    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError("Projet Madone complet introuvable dans D:\\RealEarth2024. "
                         "Extrais/installe d'abord l'archive Madone, ou utilise --project CHEMIN.")
    raise ValueError("Plusieurs projets complets, aucun choix automatique :\n" +
                     "\n".join("- " + str(p) for p in candidates) +
                     "\nRelance avec --project CHEMIN pour eviter de modifier le mauvais projet.")


def moved_gps(lat: float, lon: float, bearing_deg: float = SHIFT_BEARING_DEG,
              distance_m: float = SHIFT_M) -> tuple[float, float]:
    """Short-distance north/east displacement using WGS84 meridional radius."""
    phi = math.radians(lat)
    sin2 = math.sin(phi) ** 2
    a = 6378137.0
    ecc_sq = 0.00669437999014
    meridional_radius = a * (1 - ecc_sq) / ((1 - ecc_sq * sin2) ** 1.5)
    prime_vertical_radius = a / math.sqrt(1 - ecc_sq * sin2)
    angle = math.radians(bearing_deg)
    dlat = math.cos(angle) * distance_m / meridional_radius
    dlon = math.sin(angle) * distance_m / (prime_vertical_radius * math.cos(phi))
    return lat + math.degrees(dlat), lon + math.degrees(dlon)


def simulator_running() -> bool:
    if os.name != "nt":
        return False
    proc = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                          capture_output=True, text=True, check=False)
    out = proc.stdout.lower()
    return "flightsimulator2024.exe" in out or "flightsimulator.exe" in out


def edit_placement(data: dict) -> dict:
    if MARKER in data:
        raise ValueError("Le correctif v0.1.4 est deja applique. "
                         "Ne pas repivoter ou redeplacer une deuxieme fois.")
    for key in ("latitude", "longitude", "heading_degrees"):
        if key not in data or data[key] is None:
            raise ValueError(f"Placement incomplet : {key}")
    lat, lon, heading = (float(data[k]) for k in
                         ("latitude", "longitude", "heading_degrees"))
    if not all(map(math.isfinite, (lat, lon, heading))):
        raise ValueError("GPS ou orientation invalide")
    if not (45.54 <= lat <= 45.61 and 4.57 <= lon <= 4.68):
        raise ValueError("GPS hors du secteur de Saint-Maurice")
    lat2, lon2 = moved_gps(lat, lon)
    result = dict(data)
    result["heading_degrees"] = round((heading + ROTATION_DEG) % 360, 6)
    result["latitude"] = round(lat2, 9)
    result["longitude"] = round(lon2, 9)
    result[MARKER] = {
        "previous_heading_degrees": heading,
        "rotation_clockwise_degrees": ROTATION_DEG,
        "previous_latitude": lat,
        "previous_longitude": lon,
        "shift_m": SHIFT_M,
        "shift_bearing_degrees": SHIFT_BEARING_DEG,
    }
    return result


def run(args: argparse.Namespace) -> int:
    root = find_project(args.project)
    placement_path = root / "placement.json"
    original = placement_path.read_bytes()
    old = json.loads(original.decode("utf-8-sig"))
    updated = edit_placement(old)
    print("Projet :", root)
    print("Cap actuel -> nouveau :", old["heading_degrees"], "->", updated["heading_degrees"])
    print("GPS actuel -> nouveau :", (old["latitude"], old["longitude"]),
          "->", (updated["latitude"], updated["longitude"]))
    print("Deplacement : 2 m vers le sud (supposition tiree de la demande precedente)")
    print("Statue yaw, hauteur, echelle, modele, textures et Valmorel : inchanges")
    if args.dry_run:
        print("TEST A BLANC : aucune modification ni compilation")
        return 0
    if simulator_running():
        raise ValueError("FS2024 est ouvert. Ferme-le et relance le correctif.")
    sdk = DEFAULT_BASE / "build" / "tools" / "fspackagetool.exe"
    if os.name == "nt" and not sdk.is_file():
        raise ValueError("Outil SDK absent : " + str(sdk))
    if os.name != "nt":
        raise ValueError("Installation reservee a Windows / SDK MSFS 2024")
    backup_dir = root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / ("placement_avant_camera_v014_" +
                           datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json")
    backup.write_bytes(original)
    try:
        temp = placement_path.with_suffix(".v014.tmp")
        temp.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(placement_path)
        subprocess.run([sys.executable, str(root / "compile_statue.py")],
                       cwd=str(root), check=True)
        subprocess.run([sys.executable, str(root / "install_statue.py")],
                       cwd=str(root), check=True)
    except Exception:
        placement_path.write_bytes(original)
        print("ECHEC : placement.json restaure depuis la sauvegarde", backup)
        print("Installation non finalisee ; consulte les messages de l'installateur.")
        raise
    print("OK : monument corrige et installe. Sauvegarde GPS :", backup)
    print("Ouvre FS2024 et verifie depuis exactement le meme point de vue.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Madone du Peu : +90 degres et 2 m sud")
    ap.add_argument("--project", help="Chemin du dossier statue_saint_maurice actif")
    ap.add_argument("--dry-run", action="store_true", help="Simuler sans ecrire")
    args = ap.parse_args()
    try:
        sys.exit(run(args))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("CORRECTIF NON TERMINE :", exc)
        sys.exit(1)
