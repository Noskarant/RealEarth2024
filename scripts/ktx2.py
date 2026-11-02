"""Minimal BC1 + KTX2 encoder compatible with the MSFS 2024 texture format.

MSFS 2024 only loads KTX2 textures, and its own PNG -> KTX2 build step does
not run in this headless pipeline. This module writes the container itself.

Format reference: a real simulator asset (`fs-base-effects-legacy`,
FX_2.BMP.KTX2) uses vkFormat 133 (BC1_RGBA_SRGB), 6 mip levels, no
supercompression. Its Data Format Descriptor and the ASOBO key/value block
are reproduced byte for byte below, so the runtime sees a familiar file.
"""
from __future__ import annotations

import json
import struct
import time
from pathlib import Path

import numpy as np
from PIL import Image

KTX2_MAGIC = bytes.fromhex("ab4b5458203230bb0d0a1a0a")

VK_FORMAT_BC1_RGBA_SRGB = 133

# Data Format Descriptor taken verbatim from the simulator's own BC1 asset.
DFD_BC1_SRGB = bytes.fromhex(
    "2c0000000000000002002800800101000303000008000000000000000000"
    "3f010000000000000000ffffffff"
)

ASOBO_FLAGS = "BILINEAR\0COMPRESSION\0MIPMAP\0REDUCE_LESS\0PLATFORM_FORMAT\0"
WRITER = "RealEarth2024"


def _kvd() -> bytes:
    """Key/value block, same keys and values as the simulator's own files."""

    def entry(key: str, value: bytes) -> bytes:
        payload = key.encode("ascii") + b"\0" + value
        out = struct.pack("<I", len(payload)) + payload
        return out + b"\0" * (-len(out) % 4)

    blob = b""
    blob += entry("ASOBO_flags", ASOBO_FLAGS.encode("ascii"))
    blob += entry("ASOBO_opacities", b"")
    blob += entry("ASOBO_transp", b"")
    blob += entry("ASOBOtexversion", struct.pack("<I", 1))
    blob += entry("KTXwriter", WRITER.encode("ascii") + b"\0")
    return blob + b"\0" * (-len(blob) % 4)


# ---------------------------------------------------------------- BC1 codec
def _rgb565(rgb: np.ndarray) -> np.ndarray:
    r = (rgb[..., 0].astype(np.uint32) * 31 + 127) // 255
    g = (rgb[..., 1].astype(np.uint32) * 63 + 127) // 255
    b = (rgb[..., 2].astype(np.uint32) * 31 + 127) // 255
    return (r << 11) | (g << 5) | b


def _unpack565(c: int) -> np.ndarray:
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return np.array([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)],
                    dtype=np.float32)


def _encode_block(block: np.ndarray) -> bytes:
    """4x4x3 uint8 -> 8 bytes of BC1."""
    flat = block.reshape(16, 3).astype(np.int32)
    lo = flat.min(axis=0)
    hi = flat.max(axis=0)

    c0 = int(_rgb565(hi[None, :])[0])
    c1 = int(_rgb565(lo[None, :])[0])
    if c0 < c1:
        c0, c1 = c1, c0
    if c0 == c1:
        return struct.pack("<HHI", c0, c1, 0)

    p0 = _unpack565(c0)
    p1 = _unpack565(c1)
    palette = np.stack([p0, p1, (2 * p0 + p1) / 3.0, (p0 + 2 * p1) / 3.0])

    d = ((flat[:, None, :] - palette[None, :, :]) ** 2).sum(axis=2)
    idx = d.argmin(axis=1).astype(np.uint32)

    packed = 0
    for i, v in enumerate(idx):
        packed |= int(v) << (2 * i)
    return struct.pack("<HHI", c0, c1, packed)


def _pad_to_block(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    ph, pw = (-h) % 4, (-w) % 4
    if ph or pw:
        img = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="edge")
    return img


def bc1_encode(img: np.ndarray) -> bytes:
    """RGB uint8 image (already block aligned) -> BC1 byte stream."""
    h, w = img.shape[:2]
    out = bytearray()
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            out += _encode_block(img[by:by + 4, bx:bx + 4])
    return bytes(out)


def bc1_decode(data: bytes, w: int, h: int) -> np.ndarray:
    """Reference decoder used only by the QA step."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    per_row = w // 4
    for i in range((w * h) // 16):
        c0, c1, packed = struct.unpack_from("<HHI", data, i * 8)
        p0, p1 = _unpack565(c0), _unpack565(c1)
        if c0 > c1:
            pal = [p0, p1, (2 * p0 + p1) / 3.0, (p0 + 2 * p1) / 3.0]
        else:
            pal = [p0, p1, (p0 + p1) / 2.0, np.zeros(3)]
        by = (i // per_row) * 4
        bx = (i % per_row) * 4
        for t in range(16):
            idx = (packed >> (2 * t)) & 3
            img[by + t // 4, bx + t % 4] = np.clip(pal[idx], 0, 255).astype(np.uint8)
    return img


# ------------------------------------------------------------------- KTX2
def _mip_chain(img: Image.Image, max_size: int) -> list[np.ndarray]:
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((max(1, round(img.width * ratio)),
                          max(1, round(img.height * ratio))), Image.LANCZOS)
    levels: list[np.ndarray] = []
    cur = img
    while True:
        arr = _pad_to_block(np.asarray(cur.convert("RGB")))
        levels.append(arr)
        if cur.width == 1 and cur.height == 1:
            break
        cur = cur.resize((max(1, cur.width // 2), max(1, cur.height // 2)), Image.BOX)
    return levels


def encode_image(png: Path, out_ktx2: Path, max_size: int = 512) -> dict:
    """Encode one PNG to a BC1/sRGB KTX2 with a full mip chain."""
    with Image.open(png) as im:
        images = _mip_chain(im, max_size)

    payloads = [bc1_encode(level) for level in images]
    level_count = len(payloads)
    width, height = images[0].shape[1], images[0].shape[0]

    dfd = DFD_BC1_SRGB
    kvd = _kvd()
    level_index_len = 24 * level_count
    dfd_off = 80 + level_index_len
    kvd_off = dfd_off + len(dfd)
    data_start = kvd_off + len(kvd)
    data_start += -data_start % 8

    offsets = []
    cursor = data_start
    for payload in payloads:
        offsets.append(cursor)
        cursor += len(payload)
        cursor += -cursor % 8

    header = KTX2_MAGIC
    header += struct.pack("<9I", VK_FORMAT_BC1_RGBA_SRGB, 1, width, height,
                          0, 0, 1, level_count, 0)
    header += struct.pack("<4I", dfd_off, len(dfd), kvd_off, len(kvd))
    header += struct.pack("<2Q", 0, 0)

    index = b"".join(struct.pack("<3Q", offsets[i], len(payloads[i]), len(payloads[i]))
                     for i in range(level_count))

    blob = bytearray(header + index)
    blob += dfd
    blob += kvd
    blob += b"\0" * (data_start - len(blob))
    for i, payload in enumerate(payloads):
        blob += b"\0" * (offsets[i] - len(blob))
        blob += payload

    out_ktx2.parent.mkdir(parents=True, exist_ok=True)
    out_ktx2.write_bytes(bytes(blob))

    sidecar = {
        "Version": 2,
        "SourceFileDate": int(time.time() * 1e7) + 116444736000000000,
        "Flags": ["FL_BITMAP_COMPRESSION", "FL_BITMAP_MIPMAP", "FL_BITMAP_QUALITY_HIGH"],
    }
    Path(str(out_ktx2) + ".json").write_text(json.dumps(sidecar), encoding="utf-8")

    return {"width": width, "height": height, "levels": level_count,
            "bytes": len(blob), "source": png.name}


if __name__ == "__main__":
    import sys

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    print(encode_image(src, dst))
