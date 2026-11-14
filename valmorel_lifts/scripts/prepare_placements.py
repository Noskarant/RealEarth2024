"""Generate a provisional four-station BGL placement file.
No building exclusions; cabins/pylons remain assets until surveyed.
"""
import json
import uuid
from pathlib import Path
from prepare_sdk import ROOT, guid

INFILE = ROOT / "docs" / "implantation_preview.json"
OUTFILE = ROOT / "project" / "PackageSources" / "Scenery" / "valmorel" / "scenery" / "valmorel_telecabines_preview.xml"
NAMESPACE = uuid.UUID("95aa56bd-023a-498b-b044-169a8bf3d8b2")

def instance_id(value):
    return "{" + str(uuid.uuid5(NAMESPACE, value)).upper() + "}"

def main():
    info = json.loads(INFILE.read_text(encoding="utf-8"))
    points = info["items"]
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<FSData version="9.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="bglcomp.xsd">',
        '  <!-- PROVISIONAL preview: no terrain, buildings or autogen exclusions. -->'
    ]
    for p in points:
        if not p.get("enabled", False):
            continue
        assert -90 <= p["latitude"] <= 90 and -180 <= p["longitude"] <= 180
        lines.append(
            f'  <SceneryObject instanceId="{instance_id(p["id"])}" lat="{p["latitude"]:.9f}" '
            f'lon="{p["longitude"]:.9f}" alt="{p["altitude_agl_m"]:.3f}" pitch="0" bank="0" '
            f'heading="{p["heading_deg"]:.3f}" imageComplexity="NORMAL" '
            f'altitudeIsAgl="TRUE" snapToGround="TRUE" snapToNormal="FALSE">'
        )
        lines.append(f'    <LibraryObject name="{guid(p["model"])}" scale="1.000000"/>')
        lines.append('  </SceneryObject>')
    lines.append('</FSData>')
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Written", OUTFILE, "with", sum(p.get("enabled",False) for p in points), "stations")

if __name__ == "__main__":
    main()
