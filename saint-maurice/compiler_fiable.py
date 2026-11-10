#!/usr/bin/env python3
"""RealEarth Saint-Maurice - orchestrateur de compilation FS2024 fiable.

Corrige la cause racine des echecs 0x87E5002B :
  - fspackagetool lance FlightSimulator2024.exe via GameLaunchHelper ;
  - apres un build, GameLaunchHelper/GamingServicesUI peuvent rester bloques ;
  - tout lancement suivant echoue alors avec 0x87E5002B.

Ce script nettoie ces processus avant/apres chaque build, attend les artefacts
sur disque (et non le code retour), verifie chaque package et reprend via
checkpoints. Aucune source IGN/modele n'est supprimee.

Usage :
  python compiler_fiable.py --preparer-seulement
  python compiler_fiable.py --only 10
  python compiler_fiable.py --sans-installation
  python compiler_fiable.py --community "C:\\...\\Community"
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BUILDINGS_SLUG = "realearth-sm-hd-batiments"
ORTHO_BASE = "realearth-sm-hd-ortho-"
LEGACY_SLUG = "realearth-saint-maurice-hd"
CFG_XML = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<CGLBuilder>\n'
           '  <CGL type="SecondaryAerialImage" input="Tiles" directory="aerial_images"/>\n'
           '</CGLBuilder>\n')
BUILD_HELPER_NAMES = ("fspackagetool", "FlightSimulator2024",
                      "gamelaunchhelper", "gamingservicesui")


def say(*args):
    print(*args, flush=True)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".writing")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- processus
def _ps_json(script: str):
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, errors="replace")
    text = out.stdout.strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else [value]


def running_sim_with_window() -> bool:
    """True si un simulateur interactif (fenetre) est deja ouvert par l'utilisateur."""
    items = _ps_json(
        "Get-Process FlightSimulator2024 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowHandle -ne 0 } | "
        "Select-Object Id,MainWindowTitle | ConvertTo-Json -Compress")
    return bool(items)


def builder_sim_running() -> bool:
    """True si une instance du simulateur compile encore (mode BuildAssetPackages).

    fspackagetool peut rendre la main avec un code d'erreur alors qu'une seconde
    instance, relancee apres un crash a l'initialisation, poursuit la compilation.
    Il ne faut donc jamais conclure a l'echec tant que cette instance vit.
    """
    items = _ps_json(
        "Get-CimInstance Win32_Process -Filter \"Name='FlightSimulator2024.exe'\" | "
        "Where-Object { $_.CommandLine -like '*BuildAssetPackages*' } | "
        "Select-Object ProcessId | ConvertTo-Json -Compress")
    return bool(items)


def clean_build_helpers(verbose: bool = True) -> None:
    """Termine uniquement les processus de build bloques, jamais un vol en cours."""
    if running_sim_with_window():
        raise RuntimeError(
            "Microsoft Flight Simulator 2024 est ouvert avec une fenetre. "
            "Fermer le simulateur avant de compiler (le compilateur le relance).")
    items = _ps_json(
        "Get-Process fspackagetool,FlightSimulator2024,gamelaunchhelper,gamingservicesui "
        "-ErrorAction SilentlyContinue | Select-Object Id,ProcessName | ConvertTo-Json -Compress")
    if not items:
        return
    ids = [str(item["Id"]) for item in items if "Id" in item]
    if not ids:
        return
    if verbose:
        say(f"   Nettoyage processus de build bloques : {', '.join(ids)}")
    subprocess.run(["taskkill", "/T", "/F", *sum((["/PID", i] for i in ids), [])],
                   capture_output=True)
    for _ in range(30):
        time.sleep(0.5)
        left = _ps_json(
            "Get-Process fspackagetool,FlightSimulator2024,gamelaunchhelper,gamingservicesui "
            "-ErrorAction SilentlyContinue | Select-Object Id | ConvertTo-Json -Compress")
        if not left:
            return
    raise RuntimeError("Impossible de liberer les processus de build du simulateur")


# ---------------------------------------------------------------- XML projet
def project_xml(slug: str) -> ET.Element:
    root = ET.Element("Project", {
        "Version": "2", "Name": slug, "FolderName": "Packages",
        "MetadataFolderName": "PackagesMetadata"})
    ET.SubElement(root, "OutputDirectory").text = "."
    ET.SubElement(root, "TemporaryOutputDirectory").text = "_PackageInt"
    packages = ET.SubElement(root, "Packages")
    ET.SubElement(packages, "Package").text = f"PackageDefinitions\\{slug}.xml"
    ET.SubElement(root, "PublishingGroups")
    return root


def asset_package(slug: str, groups) -> ET.Element:
    pkg = ET.Element("AssetPackage", Version="0.1.3")
    item = ET.SubElement(pkg, "ItemSettings")
    for key, value in {
        "ContentType": "SCENERY", "Title": slug, "Manufacturer": "RealEarth",
        "Creator": "RealEarth2024"}.items():
        ET.SubElement(item, key).text = value
    flags = ET.SubElement(pkg, "Flags")
    ET.SubElement(flags, "VisibleInStore").text = "false"
    ET.SubElement(flags, "CanBeReferenced").text = "true"
    ET.SubElement(pkg, "PackageOrderHint").text = "CUSTOM_SCENERY_PATCH"
    a = ET.SubElement(pkg, "AssetGroups")
    for name, typ, version, source, dest in groups:
        group = ET.SubElement(a, "AssetGroup", Name=name)
        ET.SubElement(group, "Type", Version=str(version)).text = typ
        fg = ET.SubElement(group, "Flags")
        ET.SubElement(fg, "FSXCompatibility").text = "false"
        ET.SubElement(group, "AssetDir").text = source
        ET.SubElement(group, "OutputDir").text = dest
    return pkg


def make_project(work: Path, slug: str, groups) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    definition = work / "PackageDefinitions" / f"{slug}.xml"
    definition.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(project_xml(slug)).write(
        work / f"{slug}.xml", encoding="utf-8", xml_declaration=True)
    ET.ElementTree(asset_package(slug, groups)).write(
        definition, encoding="utf-8", xml_declaration=True)
    return work / f"{slug}.xml"


# ---------------------------------------------------------------- sources
def list_tiles(tiles_dir: Path) -> list[Path]:
    """Liste rapide (metadonnees seulement) : ne relit pas 40k PNG a chaque lot."""
    names = []
    with os.scandir(tiles_dir) as it:
        for entry in it:
            if entry.is_file() and entry.name.lower().endswith(".png"):
                names.append(entry.name)
    names.sort()
    return [tiles_dir / n for n in names]


def load_lots(workspace: Path, tiles_dir: Path) -> list[tuple[int, str, list[Path]]]:
    lots_file = workspace / "lots_cgl.json"
    if not lots_file.is_file():
        raise RuntimeError(f"lots_cgl.json absent : {lots_file}")
    lots = json.loads(lots_file.read_text(encoding="utf-8"))
    all_tiles = list_tiles(tiles_dir)
    names = [p.name[:-4] for p in all_tiles]
    result = []
    used = set()
    for lot in lots:
        prefix = lot["prefix"]
        paths = [tiles_dir / f"{n}.png" for n in names if n.startswith(prefix)]
        if len(paths) != lot["tuiles"]:
            raise RuntimeError(
                f"Lot {lot['numero']} ({prefix}) : {len(paths)} tuiles, "
                f"{lot['tuiles']} attendues")
        for p in paths:
            if p.name in used:
                raise RuntimeError(f"Tuile presente dans deux lots : {p.name}")
            used.add(p.name)
        result.append((lot["numero"], prefix, paths))
    if len(used) != len(names):
        raise RuntimeError(f"{len(names) - len(used)} tuiles hors lots")
    return result


def fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for p in sorted(paths, key=lambda x: str(x)):
        st = p.stat()
        digest.update(f"{p.name}|{st.st_size}|{st.st_mtime_ns}\n".encode())
    return digest.hexdigest()[:24]


def prepare_building(root: Path, workspace: Path) -> tuple[Path, int]:
    src = root / "output" / "PackageSources"
    models = src / "Scenery" / "saintmaurice" / "modellib"
    scenes = src / "Scenery" / "saintmaurice" / "scenery"
    folder = workspace / "B"
    destmodels = folder / "PackageSources" / "Scenery" / "saintmaurice" / "modellib"
    destscenes = folder / "PackageSources" / "Scenery" / "saintmaurice" / "scenery"
    for directory in (models, scenes):
        if not directory.is_dir():
            raise RuntimeError(f"Dossier source absent : {directory}")
    if not list(scenes.glob("*.xml")):
        raise RuntimeError(f"Aucun XML de scene : {scenes}")
    shutil.copytree(models, destmodels, dirs_exist_ok=True)
    shutil.copytree(scenes, destscenes, dirs_exist_ok=True)
    for xml in destscenes.glob("*.xml"):
        content = xml.read_text(encoding="utf-8-sig")
        if " GUID=" in content:
            xml.write_text(content.replace(" GUID=", " guid="), encoding="utf-8")
    groups = [
        ("sm_modellib", "ModelLib", 1,
         "PackageSources\\Scenery\\saintmaurice\\modellib\\",
         "Scenery\\saintmaurice\\modellib\\"),
        ("sm_scenery", "BGL", 0,
         "PackageSources\\Scenery\\saintmaurice\\scenery\\",
         "Scenery\\saintmaurice\\scenery\\"),
    ]
    return make_project(folder, BUILDINGS_SLUG, groups), len(list(models.glob("*.gltf")))


def prepare_cgl(workspace: Path, prefix: str, paths: list[Path], idx: int):
    slug = ORTHO_BASE + str(idx).zfill(3)
    folder = workspace / ("O" + str(idx).zfill(3))
    src = folder / "PackageSources" / "CGL"
    images = src / "aerial_images"
    images.mkdir(parents=True, exist_ok=True)
    (src / "CGLBuilderConfig.xml").write_text(CFG_XML, encoding="utf-8")
    ET.parse(src / "CGLBuilderConfig.xml")
    for path in paths:
        dest = images / path.name
        if dest.is_file():
            if dest.stat().st_size != path.stat().st_size:
                raise RuntimeError(f"Tuile staging differente : {dest}")
            continue
        try:
            os.link(path, dest)
        except OSError:
            shutil.copy2(path, dest)
    groups = [("sm_ortho_" + str(idx), "CGL", 0, "PackageSources\\CGL\\", "CGL\\")]
    return make_project(folder, slug, groups), slug


def prepare_cgl_all(workspace: Path, paths: list[Path]):
    """Un seul package CGL : toutes les tuiles partagent le prefixe quadkey 120,
    donc un seul fichier CGL\\120\\sai220.cgl. Des packages separes produiraient
    le meme chemin VFS et seraient concatenes de facon peu fiable."""
    slug = ORTHO_BASE.rstrip("-")
    folder = workspace / "O_ALL"
    src = folder / "PackageSources" / "CGL"
    images = src / "aerial_images"
    images.mkdir(parents=True, exist_ok=True)
    (src / "CGLBuilderConfig.xml").write_text(CFG_XML, encoding="utf-8")
    ET.parse(src / "CGLBuilderConfig.xml")
    for path in paths:
        dest = images / path.name
        if dest.is_file():
            if dest.stat().st_size != path.stat().st_size:
                raise RuntimeError(f"Tuile staging differente : {dest}")
            continue
        try:
            os.link(path, dest)
        except OSError:
            shutil.copy2(path, dest)
    groups = [("sm_ortho", "CGL", 0, "PackageSources\\CGL\\", "CGL\\")]
    return make_project(folder, slug, groups), slug


def quadkey_x(name: str) -> int:
    x = 0
    for d in name[:20]:
        x <<= 1
        if d in "13":
            x |= 1
    return x


def split_tiles(paths: list[Path], parts: int) -> list[list[Path]]:
    """Decoupe spatialement (colonnes quadkey) pour rester sous 4 Go par CGL."""
    if parts < 1:
        raise ValueError("parts >= 1")
    ordered = sorted(paths, key=lambda p: (quadkey_x(p.stem), p.stem))
    size = len(ordered) // parts
    result = []
    start = 0
    for i in range(parts):
        end = len(ordered) if i == parts - 1 else start + size
        result.append(ordered[start:end])
        start = end
    return result


def prepare_cgl_part(workspace: Path, paths: list[Path], suffix: str):
    slug = "realearth-sm-hd-ortho" + suffix
    folder = workspace / ("O_" + suffix.strip("-").upper())
    src = folder / "PackageSources" / "CGL"
    images = src / "aerial_images"
    images.mkdir(parents=True, exist_ok=True)
    (src / "CGLBuilderConfig.xml").write_text(CFG_XML, encoding="utf-8")
    ET.parse(src / "CGLBuilderConfig.xml")
    for path in paths:
        dest = images / path.name
        if dest.is_file():
            if dest.stat().st_size != path.stat().st_size:
                raise RuntimeError(f"Tuile staging differente : {dest}")
            continue
        try:
            os.link(path, dest)
        except OSError:
            shutil.copy2(path, dest)
    groups = [("sm_ortho" + suffix.replace("-", "_"), "CGL", 0,
               "PackageSources\\CGL\\", "CGL\\")]
    return make_project(folder, slug, groups), slug


# ---------------------------------------------------------------- SDK
def get_sdk(explicit: str = "") -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    root = os.environ.get("MSFS_SDK_ROOT")
    if root:
        candidates.append(Path(root) / "Tools" / "bin" / "fspackagetool.exe")
    candidates += [Path(r"C:\MSFS 2024 SDK\Tools\bin\fspackagetool.exe"),
                   Path(r"D:\MSFS 2024 SDK\Tools\bin\fspackagetool.exe")]
    for p in candidates:
        if p.is_file():
            return p
    raise RuntimeError("fspackagetool.exe introuvable (utiliser --sdk CHEMIN)")


def verify_package(folder: Path, require_bgl: bool, require_cgl: bool,
                   require_ktx: bool) -> dict:
    layout = folder / "layout.json"
    manifest = folder / "manifest.json"
    if not layout.is_file() or not manifest.is_file():
        raise RuntimeError(f"layout/manifest absent : {folder}")
    meta = json.loads(layout.read_text(encoding="utf-8-sig"))
    content = meta.get("content", [])
    if not content or not isinstance(content, list):
        raise RuntimeError(f"layout vide : {folder}")
    for item in content:
        rel = item.get("path", "")
        if not rel or Path(rel).is_absolute() or ".." in Path(rel.replace("\\", "/")).parts:
            raise RuntimeError(f"Chemin layout invalide : {rel}")
        fp = folder / rel.replace("\\", "/")
        if not fp.is_file() or fp.stat().st_size <= 0:
            raise RuntimeError(f"Fichier layout absent/vide : {rel}")
        if isinstance(item.get("size"), int) and fp.stat().st_size != item["size"]:
            raise RuntimeError(f"Taille layout incoherente : {rel}")
    counts = {".bgl": 0, ".cgl": 0, ".ktx2": 0}
    for f in folder.rglob("*"):
        if f.is_file() and f.suffix.lower() in counts:
            counts[f.suffix.lower()] += 1
    if require_bgl and not counts[".bgl"]:
        raise RuntimeError("Aucun BGL compile")
    if require_cgl and not counts[".cgl"]:
        raise RuntimeError("Aucun CGL compile")
    if require_ktx and not counts[".ktx2"]:
        raise RuntimeError("Aucune texture KTX2 compilee")
    return {"path": str(folder), "files": len(content), "BGL": counts[".bgl"],
            "CGL": counts[".cgl"], "KTX2": counts[".ktx2"],
            "bytes": sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())}


def sdk_compile(sdk: Path, project: Path, slug: str, timeout: int,
                root: Path, flavor: str, attempts: int = 2) -> tuple[Path, int, float]:
    try:
        return _sdk_compile_once(sdk, project, slug, timeout, root, flavor)
    except RuntimeError as exc:
        if attempts <= 1 or "0x87E5002B" not in str(exc):
            raise
        say("   Relance apres liberation des processus de build (0x87E5002B) ...")
        clean_build_helpers()
        time.sleep(3)
        return _sdk_compile_once(sdk, project, slug, timeout, root, flavor)


def _sdk_compile_once(sdk: Path, project: Path, slug: str, timeout: int,
                      root: Path, flavor: str) -> tuple[Path, int, float]:
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    attempt = project.parent / ("compile_" + stamp)
    n = 2
    while attempt.exists():
        attempt = project.parent / f"compile_{stamp}_{n}"
        n += 1
    dist = attempt / "dist"
    temp = attempt / "tmp"
    dist.mkdir(parents=True)
    temp.mkdir()
    logs = root / "journaux"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"{flavor}_{slug}_{stamp}.log"

    clean_build_helpers()
    command = f'"{sdk}" "{project}" -outputdir "{dist}" -tempdir "{temp}" -nopause'
    say(f"   SDK: {slug} | delai max {timeout // 60} min | {log.name}")
    started = time.time()
    return_code = None
    with log.open("w", encoding="utf-8", errors="replace") as fh:
        fh.write(command + "\n")
        fh.flush()
        # Redirection vers un fichier (pas un pipe) : le simulateur garde une console valide.
        process = subprocess.Popen(
            [str(sdk), str(project), "-outputdir", str(dist),
             "-tempdir", str(temp), "-nopause"],
            cwd=str(project.parent),
            stdout=fh, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        package = None
        announced = False
        while True:
            time.sleep(2)
            found = [p.parent for p in dist.rglob("manifest.json")
                     if p.parent.name.lower() == slug.lower()]
            if found:
                package = found[0]
                break
            if process.poll() is not None:
                # Le lanceur a rendu la main : la compilation peut continuer dans
                # une instance relancee par le SDK. Ne conclure qu'en son absence.
                if return_code is None:
                    return_code = process.returncode
                if builder_sim_running():
                    if not announced:
                        say("   Lanceur sorti, mais une instance de build vit encore : attente")
                        announced = True
                    continue
                break
            if time.time() - started > timeout:
                say("   Delai maximal atteint : arret du build")
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                               capture_output=True)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                clean_build_helpers(verbose=False)
                raise RuntimeError(f"Compilation {slug} trop longue ; journal {log}")
        if package is None:
            # Le simulateur ecrit parfois le manifeste apres avoir rendu la main.
            for _ in range(10):
                time.sleep(2)
                found = [p.parent for p in dist.rglob("manifest.json")
                         if p.parent.name.lower() == slug.lower()]
                if found:
                    package = found[0]
                    break
                if not builder_sim_running():
                    break
        if process.poll() is None:
            # Le lanceur reste parfois bloque apres un build reussi : artefacts valides.
            for _ in range(30):
                time.sleep(2)
                if process.poll() is not None:
                    break
            else:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                               capture_output=True)
    if return_code is None:
        return_code = process.returncode if process.returncode is not None else 0
    if package is None:
        clean_build_helpers(verbose=False)
        raise RuntimeError(
            f"{slug}: package absent (SDK 0x{return_code & 0xffffffff:08X}) ; journal {log}")
    return package, return_code, time.time() - started


# ---------------------------------------------------------------- checkpoints
def checkpoint(workspace: Path, slug: str, expect: str, source_sig: str):
    mark = workspace / "checked" / (slug + ".json")
    if not mark.is_file():
        return None
    try:
        record = json.loads(mark.read_text(encoding="utf-8"))
        if record.get("expect") != expect or record.get("source_sig") != source_sig:
            return None
        pkg = Path(record["path"])
        verify_package(pkg, expect == "building", expect == "cgl", expect == "building")
        return pkg
    except (OSError, KeyError, ValueError, RuntimeError):
        return None


def save_checkpoint(workspace: Path, slug: str, expect: str, pkg: Path,
                    code: int, source_sig: str) -> None:
    write_json(workspace / "checked" / (slug + ".json"),
               {"slug": slug, "expect": expect, "path": str(pkg),
                "source_sig": source_sig, "sdk_exit": code,
                "validated_at": dt.datetime.now().isoformat()})


# ---------------------------------------------------------------- Community
def choose_community(arg: str = "") -> Path:
    if arg:
        p = Path(arg)
        if not p.is_dir():
            raise RuntimeError(f"Community introuvable : {p}")
        return p
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    envs = []
    if local:
        envs.append(Path(local) / "Packages" / "Microsoft.Limitless_8wekyb3d8bbwe" / "LocalCache")
    if roaming:
        envs.append(Path(roaming) / "Microsoft Flight Simulator 2024")
    configs = []
    for p in envs:
        opt = p / "UserCfg.opt"
        if opt.is_file():
            text = opt.read_text(encoding="utf-8-sig", errors="replace")
            m = re.search(r'InstalledPackagesPath\s+"([^"]+)"', text, re.I)
            if m:
                pp = Path(m.group(1)) / "Community"
                if pp.is_dir():
                    configs.append(pp)
    if len(set(configs)) == 1:
        return configs[0]
    candidates = [p / "Packages" / "Community" for p in envs if (p / "Packages" / "Community").is_dir()]
    if len(set(candidates)) == 1:
        return candidates[0]
    raise RuntimeError("Community ambigu : utiliser --community CHEMIN")


def publish(packages: list[Path], community: Path) -> None:
    backup_root = community / "_RSM24_SAUVEGARDES"
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stage = community / ("_RSM24_PRET_" + stamp)
    stage.mkdir(parents=True)
    for pkg in packages:
        staged = stage / pkg.name
        say(f"  Copie validee : {pkg.name}")
        shutil.copytree(pkg, staged)
        verify_package(staged, pkg.name == BUILDINGS_SLUG,
                       pkg.name != BUILDINGS_SLUG, pkg.name == BUILDINGS_SLUG)
    say("Tous les packages copies et revalides. Installation ...")
    moved, installed = [], []
    names = [LEGACY_SLUG] + [p.name for p in packages]
    try:
        for name in names:
            current = community / name
            if current.exists():
                backup_root.mkdir(parents=True, exist_ok=True)
                dest = backup_root / f"{name}.{stamp}"
                if dest.exists():
                    raise RuntimeError(f"Sauvegarde existe deja : {dest}")
                current.rename(dest)
                moved.append((dest, current))
        for pkg in packages:
            dest = community / pkg.name
            (stage / pkg.name).rename(dest)
            installed.append(dest)
    except Exception:
        for path in reversed(installed):
            if path.exists():
                backup_root.mkdir(parents=True, exist_ok=True)
                path.rename(backup_root / (path.name + ".rollback." + stamp))
        for backup, original in reversed(moved):
            if backup.exists() and not original.exists():
                backup.rename(original)
        raise
    finally:
        if stage.is_dir() and not any(stage.iterdir()):
            stage.rmdir()
    say(f"INSTALLATION TERMINEE : {len(packages)} packages dans {community}")
    say(f"Sauvegardes : {backup_root}")


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdk", default="")
    ap.add_argument("--community", default="")
    ap.add_argument("--sans-installation", action="store_true")
    ap.add_argument("--preparer-seulement", action="store_true")
    ap.add_argument("--sans-batiments", action="store_true")
    ap.add_argument("--sans-ortho", action="store_true")
    ap.add_argument("--parts", type=int, default=2,
                    help="nombre de packages CGL (limite 4 Go par fichier)")
    ap.add_argument("--timeout-batiments", type=int, default=1800)
    ap.add_argument("--timeout-ortho", type=int, default=7200)
    ap.add_argument("--workdir", default="")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent
    workspace = Path(args.workdir) if args.workdir else Path(root.anchor) / "RSM24S"
    workspace.mkdir(parents=True, exist_ok=True)
    marker = workspace / "original_root.txt"
    if marker.is_file() and Path(marker.read_text(encoding="utf-8").strip()).resolve() != root.resolve():
        raise RuntimeError(f"Dossier de travail d'un autre projet : {workspace}")
    marker.write_text(str(root), encoding="utf-8")

    tiles_dir = root / "output" / "PackageSources" / "CGL" / "aerial_images"
    if not tiles_dir.is_dir():
        raise RuntimeError(f"Tuiles absentes : {tiles_dir}")
    lots = load_lots(workspace, tiles_dir)
    total = sum(len(p) for _, _, p in lots)
    all_tiles = [t for _, _, paths in lots for t in paths]
    say("=== REAL EARTH SAINT-MAURICE / COMPILATION FIABLE ===")
    say(f"Source   : {root}")
    say(f"Travail  : {workspace}")
    say(f"Ortho    : {total} tuiles (un seul package, chemin CGL unique)")
    if args.preparer_seulement:
        for number, part in enumerate(split_tiles(all_tiles, args.parts), 1):
            suffix = "-" + chr(96 + number) if args.parts > 1 else ""
            prepare_cgl_part(workspace, part, suffix)
        say("PREPARATION VALIDEE (aucune compilation).")
        return 0

    sdk = get_sdk(args.sdk)
    say(f"SDK      : {sdk}")
    clean_build_helpers()

    packages = []
    report = []

    if not args.sans_batiments:
        say("\n[1] BATIMENTS + MODELIB + BGL")
        project, nmodels = prepare_building(root, workspace)
        sig = fingerprint(list((workspace / "B" / "PackageSources" / "Scenery" / "saintmaurice" / "modellib").glob("*.gltf")))
        pkg = checkpoint(workspace, BUILDINGS_SLUG, "building", sig)
        if pkg:
            say(f"   Reutilise (checkpoint valide) : {pkg}")
        else:
            pkg, code, secs = sdk_compile(sdk, project, BUILDINGS_SLUG,
                                          args.timeout_batiments, workspace, "batiments")
            checks = verify_package(pkg, True, False, True)
            say(f"   OK en {secs:.0f}s : {checks['BGL']} BGL, {checks['KTX2']} KTX2, "
                f"{checks['files']} fichiers, {checks['bytes']/1e6:.1f} Mo (exit {code})")
            save_checkpoint(workspace, BUILDINGS_SLUG, "building", pkg, code, sig)
        report.append({"kind": "buildings", "models": nmodels, "package": str(pkg)})
        packages.append(pkg)

    if not args.sans_ortho:
        say(f"\n[2] ORTHOPHOTOS HD : {total} tuiles en {args.parts} package(s)")
        parts = split_tiles(all_tiles, args.parts)
        for number, part in enumerate(parts, 1):
            suffix = "-" + chr(96 + number) if len(parts) > 1 else ""
            say(f"\n   Package ortho {number}/{len(parts)} : {len(part)} tuiles")
            project, slug = prepare_cgl_part(workspace, part, suffix)
            sig = fingerprint(part)
            pkg = checkpoint(workspace, slug, "cgl", sig)
            if pkg:
                say(f"   Reutilise (checkpoint valide) : {pkg}")
            else:
                pkg, code, secs = sdk_compile(sdk, project, slug, args.timeout_ortho,
                                              workspace, "ortho")
                checks = verify_package(pkg, False, True, False)
                biggest = max(f.stat().st_size for f in pkg.rglob("*.cgl"))
                if biggest >= 4 * 1024**3:
                    raise RuntimeError(
                        f"{slug}: CGL de {biggest/1e9:.2f} Go >= limite 4 Go ; augmenter --parts")
                say(f"   OK en {secs:.0f}s : {checks['CGL']} CGL, {checks['files']} fichiers, "
                    f"{checks['bytes']/1e9:.2f} Go, plus gros CGL {biggest/1e9:.2f} Go (exit {code})")
                save_checkpoint(workspace, slug, "cgl", pkg, code, sig)
            report.append({"kind": "cgl", "part": number, "tiles": len(part),
                           "package": str(pkg)})
            packages.append(pkg)

    clean_build_helpers(verbose=False)
    write_json(workspace / "resultat_compilation.json", report)
    say(f"\n{len(packages)} PACKAGES VERIFIES SUR DISQUE.")
    if args.sans_installation:
        say("Installation Community non effectuee (--sans-installation).")
        return 0
    community = choose_community(args.community)
    say(f"Community : {community}")
    publish(packages, community)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        say(f"\nECHEC SECURISE : {type(exc).__name__}: {exc}")
        say("Sources, monuments et packages deja valides conserves.")
        sys.exit(1)
