"""Probe the Geoplateforme WCS for available elevation coverages."""
from __future__ import annotations

import re

import requests

ENDPOINTS = (
    "https://data.geopf.fr/wcs/ows",
    "https://data.geopf.fr/wcs",
    "https://data.geopf.fr/wcs/ows?",
)


def main() -> None:
    for url in ENDPOINTS:
        try:
            r = requests.get(url, params={
                "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCapabilities",
            }, timeout=90)
        except Exception as exc:  # noqa: BLE001
            print(url, "ERR", exc)
            continue
        print(url, r.status_code, len(r.content))
        if r.status_code != 200:
            continue
        text = r.content.decode("utf-8", errors="replace")
        ids = re.findall(r"<wcs:CoverageId>([^<]+)</wcs:CoverageId>", text)
        if not ids:
            ids = re.findall(r"<CoverageId>([^<]+)</CoverageId>", text)
        print("  coverage count:", len(ids))
        for cid in ids:
            up = cid.upper()
            if any(k in up for k in ("ALTI", "MNT", "DEM", "LIDAR", "ELEV")):
                print("   *", cid)
        break


if __name__ == "__main__":
    main()
