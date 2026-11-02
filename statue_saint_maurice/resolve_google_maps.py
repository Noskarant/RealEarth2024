"""Resolve a *pinned location* from a Google Maps share link.

This is intentionally conservative: map viewport/camera coordinates (/@lat,lon)
are never silently used as an object's position. Writes placement.json only
when a precise coordinate pair is explicitly encoded in the shared URL.

Run on the user's Windows PC, which can access maps.app.goo.gl redirects.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://maps.app.goo.gl/jKMSu8kzVjR1cien6"
ROOT = Path(__file__).resolve().parent
PLACEMENT = ROOT / "placement.json"

LAT_MIN, LAT_MAX = 45.54, 45.61
LON_MIN, LON_MAX = 4.57, 4.68


def in_area(lat: float, lon: float) -> bool:
    return (math.isfinite(lat) and math.isfinite(lon)
            and LAT_MIN <= lat <= LAT_MAX
            and LON_MIN <= lon <= LON_MAX)


def parse_pair(lat: str, lon: str, name: str):
    try:
        a, b = float(lat), float(lon)
    except ValueError:
        return None
    return (a, b, name) if in_area(a, b) else None


def precise_pairs(url: str):
    """Return explicitly pinned positions, strongest first.

    /@lat,lon is only the camera/view center and MUST NOT be used.
    """
    decoded = urllib.parse.unquote(url)
    matches = []
    patterns = (
        (r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", "Google Maps place pin"),
        (r"!2d(-?\d+(?:\.\d+)?)!3d(-?\d+(?:\.\d+)?)", "Google Maps geographic pin (lon/lat)"),
    )
    for pattern, label in patterns:
        for m in re.finditer(pattern, decoded):
            if label.endswith("(lon/lat)"):
                coords = parse_pair(m.group(2), m.group(1), label)
            else:
                coords = parse_pair(m.group(1), m.group(2), label)
            if coords:
                matches.append(coords)

    u = urllib.parse.urlsplit(decoded)
    query = urllib.parse.parse_qs(u.query, keep_blank_values=False)
    for key in ("query", "q", "ll", "center"):
        # "center" can also denote the viewport, so do not accept it as a
        # pinned coordinate without another stronger indicator.
        if key == "center":
            continue
        for value in query.get(key, []):
            m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", value)
            if m:
                pair = parse_pair(m.group(1), m.group(2), f"query parameter {key}")
                if pair:
                    matches.append(pair)
    for m in re.finditer(
        r"(?:/place/|/search/)[^?#]*/(-?\d+\.\d+),(-?\d+\.\d+)", decoded
    ):
        pair = parse_pair(m.group(1), m.group(2), "Google Maps place path")
        if pair:
            matches.append(pair)
    return matches


def camera_pair(url: str):
    decoded = urllib.parse.unquote(url)
    m = re.search(r"/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", decoded)
    if not m:
        return None
    return parse_pair(m.group(1), m.group(2), "map camera center (not a pin)")


def resolve_url(link: str) -> tuple[str, list[str]]:
    if not link.startswith(("https://maps.app.goo.gl/", "https://www.google.com/maps",
                            "https://google.com/maps", "https://maps.google.com/")):
        raise ValueError("Expected Google Maps share URL")
    request = urllib.request.Request(link, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    })
    with urllib.request.urlopen(request, timeout=22) as response:
        final_url = response.url
        # Google maps URLs often redirect with coordinates in their URL;
        # a small HTML sample may also contain a canonical share link.
        html = response.read(500_000).decode("utf-8", errors="replace")
    candidates = [final_url]
    for pattern in (
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)',
        r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)',
        r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)',
    ):
        for m in re.finditer(pattern, html, re.IGNORECASE):
            value = m.group(1).replace("&amp;", "&")
            if value.startswith("https://"):
                candidates.append(value)
    return final_url, candidates


def manually_copy_pin():
    print("Open the Google Maps link, right-click on the exact CENTRE")
    print("of the monument base, and click its decimal GPS coordinates.")
    raw = input("Paste latitude, longitude (or Enter to cancel): ").strip()
    match = re.fullmatch(
        r"\\s*(-?\\d+\\.\\d+)\\s*[,; ]\\s*(-?\\d+\\.\\d+)\\s*", raw
    )
    if match is None:
        raise ValueError("No valid GPS coordinates were supplied")
    point = parse_pair(match.group(1), match.group(2), "manual pin")
    if point is None:
        raise ValueError("Coordinates are outside Saint-Maurice area")
    return point


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--overwrite", action="store_true",
                        help="Permit updating a previously configured pin")
    args = parser.parse_args()
    try:
        final_url, candidates = resolve_url(args.url)
        print("Google Maps destination:", final_url)
    except Exception as exc:
        print("Unable to expand the Google Maps link:", exc)
        candidates = []

    precise = []
    for url in candidates:
        precise.extend(precise_pairs(url))
    # Do not silently accept a different nearby camera position.
    if precise:
        lat, lon, source = precise[0]
        if any(math.hypot((lat-lat2)*111_000, (lon-lon2)*78_000) > 35
               for lat2, lon2, _ in precise[1:]):
            print("Conflicting pinned positions in Google Maps:", precise)
            precise = []
    if not precise:
        center = next((camera_pair(url) for url in candidates if camera_pair(url)), None)
        print("No reliable monument-pin coordinates in the shared URL.")
        if center:
            print("Map camera center only (NOT used):", center[:2])
        if args.non_interactive:
            return 3
        try:
            lat, lon, source = manually_copy_pin()
        except ValueError as exc:
            print(exc)
            return 3
    if PLACEMENT.is_file():
        data = json.loads(PLACEMENT.read_text(encoding="utf-8"))
    else:
        data = {"heading_degrees": 0, "scale": 1, "agl_offset_m": 0}
    old_lat, old_lon = data.get("latitude"), data.get("longitude")
    if old_lat is not None and old_lon is not None and not args.overwrite:
        if math.hypot((lat-float(old_lat))*111_000, (lon-float(old_lon))*78_000) > 0.5:
            print("Existing position differs from link; refusing overwrite.")
            print("Use --overwrite to confirm replacement.")
            return 5
    data.update(latitude=lat, longitude=lon)
    PLACEMENT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PRECISE LOCATION SAVED: {lat:.8f}, {lon:.8f} ({source})")
    print("File:", PLACEMENT)
    print("Next: compile_statue.py; check alignment and orientation in FS2024.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
