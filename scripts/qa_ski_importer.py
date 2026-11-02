"""Offline round-trip test of glTF KHR_mesh_quantization -> MSFS native glTF."""
from __future__ import annotations
import json
import struct
import tempfile
from pathlib import Path

import numpy as np

from ski_assets import convert_glb

def make_fixture(path: Path):
    # Three vertices quantized as uint16, expanded using node scale 0.01.
    pos = np.array([[0, 0, 0], [100, 0, 0], [0, 100, 0],
                    [0, 0, 100]], dtype="<u2")
    idx = np.array([0,1,2,0,2,3,0,3,1,1,3,2], dtype="<u2")
    binary = pos.tobytes() + idx.tobytes()
    doc = {
        "asset":{"version":"2.0"},
        "extensionsUsed":["KHR_mesh_quantization"],
        "extensionsRequired":["KHR_mesh_quantization"],
        "scene":0, "scenes":[{"nodes":[0]}],
        "nodes":[{"mesh":0, "scale":[0.01,0.01,0.01]}],
        "meshes":[{"primitives":[{
            "attributes":{"POSITION":0}, "indices":1, "material":0,
            "mode":4
        }]}],
        "materials":[{"pbrMetallicRoughness":{
            "baseColorFactor":[0.5,0.2,0.1,1.0],
            "roughnessFactor":0.8,"metallicFactor":0.0
        }}],
        "accessors":[
            {"bufferView":0,"componentType":5123,"count":4,"type":"VEC3"},
            {"bufferView":1,"componentType":5123,"count":12,"type":"SCALAR"}
        ],
        "bufferViews":[
            {"buffer":0,"byteOffset":0,"byteLength":len(pos.tobytes())},
            {"buffer":0,"byteOffset":len(pos.tobytes()),"byteLength":len(idx.tobytes())}
        ],
        "buffers":[{"byteLength":len(binary)}]
    }
    json_bytes = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((-len(json_bytes)) % 4)
    binary += b"\x00" * ((-len(binary)) % 4)
    length = 12 + 8 + len(json_bytes) + 8 + len(binary)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, length)
                     + struct.pack("<I4s", len(json_bytes), b"JSON")
                     + json_bytes
                     + struct.pack("<I4s", len(binary), b"BIN\x00")
                     + binary)

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        src = root / "sample.glb"
        make_fixture(src)
        stats = convert_glb(src, root, "ski_test_fixture")
        assert stats["triangles"] == 4, stats
        result = json.loads((root / "ski_test_fixture.gltf").read_text())
        assert result["asset"]["version"] == "2.0"
        assert "KHR_mesh_quantization" not in result.get("extensionsUsed", [])
        assert result["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"] == [
            0.5, 0.2, 0.1, 1.0
        ]
        assert result["accessors"][0]["componentType"] == 5126
        assert result["buffers"][0]["byteLength"] == (
            root / "ski_test_fixture.bin"
        ).stat().st_size
        assert "texture" not in str(result).lower()
        assert (root / "ski_test_fixture.xml").is_file()
    print("CC0 GLB CONVERTER QA: OK (quantized vertices, PBR color, native glTF)")

if __name__ == "__main__":
    main()
