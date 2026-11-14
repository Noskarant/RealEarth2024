"""Convert user-provided original GLB models into MSFS 2024 SDK sources.
The binary GLBs are distributed separately in the downloadable ZIP.
No Blender or third-party Python module is required.
"""
import json
import struct
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "assets" / "glb_source"
MODEL = ROOT / "project" / "PackageSources" / "Scenery" / "valmorel" / "modellib"
NAMESPACE = uuid.UUID("2d19def8-fc7c-42fa-abd3-eb8589ec046b")
ASSETS = [
    "Planchamp_Gare_Aval", "Planchamp_Gare_Amont",
    "Planchamp_Cabine_Type_A", "Planchamp_Pylone_Type",
    "Pierrafort_Gare_Aval", "Pierrafort_Gare_Amont",
    "Pierrafort_Cabine_Type_A", "Pierrafort_Pylone_Type",
]


def guid(name):
    return "{" + str(uuid.uuid5(NAMESPACE, name)).upper() + "}"


def unpack_glb(path):
    data = path.read_bytes()
    magic, version, size = struct.unpack_from("<III", data)
    if magic != 0x46546C67 or version != 2 or size != len(data):
        raise ValueError("Invalid GLB: " + str(path))
    chunks = {}
    offset = 12
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunks[kind] = data[offset:offset + length]
        offset += length
    return json.loads(chunks[0x4E4F534A]), chunks[0x004E4942]


def main():
    MODEL.mkdir(parents=True, exist_ok=True)
    tex = MODEL / "texture"
    tex.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        source = GLB / (name + ".glb")
        if not source.is_file():
            raise FileNotFoundError(source)
        doc, binary = unpack_glb(source)
        if len(doc.get("buffers", [])) != 1:
            raise ValueError("Unexpected buffers " + name)
        prefix = name + "_LOD00"
        doc["buffers"][0]["uri"] = prefix + ".bin"
        remove = {"KHR_materials_transmission", "KHR_materials_ior"}
        if set(doc.get("extensionsRequired", [])) & remove:
            raise ValueError("Required unsupported extension " + name)
        doc["extensionsUsed"] = [x for x in doc.get("extensionsUsed", []) if x not in remove]
        doc["extensionsRequired"] = [x for x in doc.get("extensionsRequired", []) if x not in remove]
        if not doc["extensionsUsed"]:
            doc.pop("extensionsUsed")
        if not doc["extensionsRequired"]:
            doc.pop("extensionsRequired")
        for mat in doc.get("materials", []):
            ext = mat.get("extensions", {})
            glass = "KHR_materials_transmission" in ext
            for key in remove:
                ext.pop(key, None)
            if not ext:
                mat.pop("extensions", None)
            if glass:
                mat["alphaMode"] = "BLEND"
                rgba = mat.setdefault("pbrMetallicRoughness", {}).setdefault("baseColorFactor", [1, 1, 1, 1])
                rgba[3] = min(float(rgba[3]), 0.45)
                mat["doubleSided"] = True
        for i, img in enumerate(doc.get("images", [])):
            if img.get("mimeType") != "image/png" or "bufferView" not in img:
                raise ValueError("Unexpected texture in " + name)
            view = doc["bufferViews"][img["bufferView"]]
            start = view.get("byteOffset", 0)
            data = binary[start:start + view["byteLength"]]
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Bad PNG")
            filename = "valmorel_" + name.lower() + "_" + str(i).zfill(2) + ".png"
            # MSFS 2024 requires texture width/height divisible by four.
            # Three Blender logo atlases were 3935x1070 and are padded in
            # the standalone ZIP to 3936x1072, preserving all source pixels.
            width, height = struct.unpack_from(">II", data, 16)
            if width < 8 or height < 8:
                raise ValueError(f"Too-small texture: {filename} ({width}x{height})")
            if width % 4 or height % 4:
                override = ROOT / "assets" / "texture_overrides" / filename
                if not override.is_file():
                    raise FileNotFoundError(
                        f"SDK invalid texture dimensions {width}x{height} for {filename}; missing corrected PNG: {override}"
                    )
                data = override.read_bytes()
                neww, newh = struct.unpack_from(">II", data, 16)
                if neww % 4 or newh % 4 or neww < width or newh < height:
                    raise ValueError(f"Invalid corrected texture {filename}: {neww}x{newh}")
                print(f"FIX bitmap dimensions: {filename}: {width}x{height} -> {neww}x{newh}")
            (tex / filename).write_bytes(data)
            (tex / (filename + ".xml")).write_text(
                "<BitmapConfiguration>\n<BitmapSlot>MTL_BITMAP_DECAL0</BitmapSlot>\n</BitmapConfiguration>\n", encoding="utf-8"
            )
            img.pop("bufferView")
            img.pop("mimeType", None)
            img["uri"] = "texture/" + filename
        for mesh in doc.get("meshes", []):
            for primitive in mesh.get("primitives", []):
                if not {"POSITION", "NORMAL"}.issubset(primitive.get("attributes", {})):
                    raise ValueError("Missing vertex normals in " + name)
        (MODEL / (prefix + ".bin")).write_bytes(binary)
        (MODEL / (prefix + ".gltf")).write_text(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        (MODEL / (name + ".xml")).write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            + '<ModelInfo version="1.1" guid="' + guid(name) + '">\n'
            + '<LODS><LOD minSize="0" ModelFile="' + prefix + '.gltf"/></LODS>\n'
            + '</ModelInfo>\n', encoding="utf-8"
        )
    print("SDK sources prepared:", len(ASSETS), "GLB models")


if __name__ == "__main__":
    main()
