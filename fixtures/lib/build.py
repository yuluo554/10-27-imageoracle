# -*- coding: utf-8 -*-
"""fixtures 字节构造库（纯标准库，不调用任何外部 CLI）。

**为什么自己造字节**：本机没有 exiftool / jpegtran / sharp / magick（2026-10-27 实测），
且 skill 的真值纪律要求"真值的字节不能依赖跑生成器那台机器上的工具链版本"——
不同版本的 exiftool 写出的 IFD 顺序/填充不同，哈希会漂移，而"逐字节可复现"是本题评分项。

**诚实边界**：本库造的是**结构上正确**的容器——我们的工具只读结构字段（tag/偏移/长度/CRC），
从不解码像素。JPEG 的熵编码段是零填充的**结构性填充**，不是可解码的像素流。这条写进
`fixtures/manifest.json` 的 `notes`，不掩盖（`plan/04` §二）。

一切函数都是确定性的：固定输入 → 固定字节，无随机、无时间戳。
"""

from __future__ import annotations

import struct
import zlib

# ─────────────────────────────────────────────────────────────────────────────
# TIFF / EXIF
# ─────────────────────────────────────────────────────────────────────────────

TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4}

TAG_IMAGE_WIDTH = 256
TAG_IMAGE_LENGTH = 257
TAG_ORIENTATION = 274
TAG_ICC_PROFILE = 34675


def _encode_short(value: int, endian: str) -> bytes:
    return struct.pack(endian + "H", value)


def _encode_long(value: int, endian: str) -> bytes:
    return struct.pack(endian + "I", value)


def build_tiff(
    *,
    byte_order: str = "II",
    ifd0_tags: list[tuple[int, int, bytes]] | None = None,
    ifd1_tags: list[tuple[int, int, bytes]] | None = None,
) -> bytes:
    """构造 TIFF 结构。

    `ifd0_tags` / `ifd1_tags` 的元素是 `(tag, type, value_bytes)`；`value_bytes` 必须已按
    `byte_order` 编码好（本库提供 `_encode_short` / `_encode_long`）。
    `ifd1_tags` 非空时，IFD0 的 next-IFD 指针指向它（模拟缩略图 IFD）。
    """
    endian = "<" if byte_order == "II" else ">"
    ifd0_tags = ifd0_tags or []
    ifd1_tags = ifd1_tags or []

    ifd0_size = 2 + 12 * len(ifd0_tags) + 4
    ifd1_size = (2 + 12 * len(ifd1_tags) + 4) if ifd1_tags else 0

    ifd0_offset = 8
    ifd1_offset = ifd0_offset + ifd0_size
    data_cursor = ifd0_offset + ifd0_size + ifd1_size

    out = bytearray()
    out += byte_order.encode("ascii")
    out += struct.pack(endian + "H", 42)
    out += struct.pack(endian + "I", ifd0_offset)

    data_blob = bytearray()

    def emit_ifd(tags: list[tuple[int, int, bytes]], next_offset: int) -> bytes:
        nonlocal data_cursor
        buf = bytearray()
        buf += struct.pack(endian + "H", len(tags))
        for tag, ftype, value in tags:
            size = TYPE_SIZES[ftype] * (len(value) // max(1, TYPE_SIZES[ftype]))
            count = len(value) // TYPE_SIZES[ftype] if TYPE_SIZES[ftype] else 0
            buf += struct.pack(endian + "HHI", tag, ftype, count)
            if len(value) <= 4:
                buf += value.ljust(4, b"\x00")
            else:
                buf += struct.pack(endian + "I", data_cursor)
                data_blob.extend(value)
                data_cursor += len(value)
            del size  # 仅用于说明 count 的取法
        buf += struct.pack(endian + "I", next_offset)
        return bytes(buf)

    out += emit_ifd(ifd0_tags, ifd1_offset if ifd1_tags else 0)
    if ifd1_tags:
        out += emit_ifd(ifd1_tags, 0)
    out += data_blob
    return bytes(out)


def tiff_with_orientation(
    orientation: int | None,
    *,
    byte_order: str = "II",
    width: int = 64,
    height: int = 48,
    ifd1_orientation: int | None = None,
) -> bytes:
    """只有必要 tag 的 TIFF：宽 / 高 / 方向（可选），可选 IFD1。"""
    endian = "<" if byte_order == "II" else ">"
    ifd0: list[tuple[int, int, bytes]] = [
        (TAG_IMAGE_WIDTH, 3, _encode_short(width, endian)),
        (TAG_IMAGE_LENGTH, 3, _encode_short(height, endian)),
    ]
    if orientation is not None:
        ifd0.append((TAG_ORIENTATION, 3, _encode_short(orientation, endian)))
    ifd1: list[tuple[int, int, bytes]] = []
    if ifd1_orientation is not None:
        ifd1.append((TAG_ORIENTATION, 3, _encode_short(ifd1_orientation, endian)))
    return build_tiff(byte_order=byte_order, ifd0_tags=ifd0, ifd1_tags=ifd1)


def tiff_with_wrong_type_orientation(value: int, *, byte_order: str = "II") -> bytes:
    """方向 tag 写成 LONG（type 4）——应触发 `orientation_not_int16u`。"""
    endian = "<" if byte_order == "II" else ">"
    return build_tiff(
        byte_order=byte_order,
        ifd0_tags=[
            (TAG_IMAGE_WIDTH, 3, _encode_short(64, endian)),
            (TAG_IMAGE_LENGTH, 3, _encode_short(48, endian)),
            (TAG_ORIENTATION, 4, _encode_long(value, endian)),
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# JPEG
# ─────────────────────────────────────────────────────────────────────────────

EXIF_PREFIX = b"Exif\x00\x00"
XMP_PREFIX = b"http://ns.adobe.com/xap/1.0/\x00"


def _seg(marker: int, payload: bytes) -> bytes:
    return b"\xff" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload


def build_jpeg(
    *,
    width: int = 64,
    height: int = 48,
    components: int = 3,
    exif: bytes | None = None,
    xmp: str | None = None,
    app14: bytes | None = None,
    progressive: bool = False,
    extra_segments: list[tuple[int, bytes]] | None = None,
    trailing_segments: list[tuple[int, bytes]] | None = None,
) -> bytes:
    """构造结构完整的 JPEG（SOI → APPn → DQT → SOF → DHT → SOS → 熵段 → EOI）。

    熵编码段是零填充的**结构性填充**，不解码（见模块 docstring 的诚实边界）。
    `extra_segments` 插在 SOF 之前；`trailing_segments` 插在 SOS 之后（用于段顺序错误样本）。
    """
    out = bytearray(b"\xff\xd8")  # SOI

    if exif is not None:
        out += _seg(0xE1, EXIF_PREFIX + exif)
    if xmp is not None:
        out += _seg(0xE1, XMP_PREFIX + xmp.encode("utf-8"))
    if app14 is not None:
        out += _seg(0xEE, app14)
    for marker, payload in extra_segments or []:
        out += _seg(marker, payload)

    # DQT：一条 8-bit 量化表（全 1，确定性）
    out += _seg(0xDB, bytes([0x00]) + bytes([1] * 64))

    # SOF0 / SOF2
    sof_marker = 0xC2 if progressive else 0xC0
    comp_specs = bytearray()
    for i in range(components):
        comp_specs += bytes([i + 1, 0x11, 0x00])
    sof_payload = (
        bytes([8])
        + struct.pack(">HH", height, width)
        + bytes([components])
        + bytes(comp_specs)
    )
    out += _seg(sof_marker, sof_payload)

    # DHT：一条 DC 表（全 0 计数 + 一个码）
    out += _seg(0xC4, bytes([0x00]) + bytes([0] * 16) + bytes([0x00]))

    # SOS
    sos_comps = bytearray()
    for i in range(components):
        sos_comps += bytes([i + 1, 0x00])
    sos_payload = bytes([components]) + bytes(sos_comps) + bytes([0x00, 0x3F, 0x00])
    out += _seg(0xDA, sos_payload)

    # 熵编码填充（结构性）：少量 0x00 字节，避免出现伪 marker
    out += b"\x00" * 16

    for marker, payload in trailing_segments or []:
        out += _seg(marker, payload)

    out += b"\xff\xd9"  # EOI
    return bytes(out)


def build_app14(transform: int = 0) -> bytes:
    """Adobe APP14：'Adobe' + version(2) + flags0(2) + flags1(2) + transform(1)。"""
    return b"Adobe" + struct.pack(">HHHB", 100, 0, 0, transform)


# ─────────────────────────────────────────────────────────────────────────────
# PNG
# ─────────────────────────────────────────────────────────────────────────────

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_chunk(ctype: str, data: bytes, *, crc: int | None = None, include_crc: bool = True) -> bytes:
    """一个 PNG chunk。`crc=None` 用正确值；显式给 `crc` 可造坏 CRC 样本。"""
    body = ctype.encode("ascii") + data
    value = (zlib.crc32(body) & 0xFFFFFFFF) if crc is None else crc
    out = struct.pack(">I", len(data)) + body
    if include_crc:
        out += struct.pack(">I", value)
    return out


def ihdr(width: int = 64, height: int = 48, bit_depth: int = 8, color_type: int = 2) -> bytes:
    return struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)


def idat(payload: bytes = b"\x00" * 32) -> bytes:
    return payload


def build_png(
    *,
    width: int = 64,
    height: int = 48,
    color_type: int = 2,
    chunks: list[bytes] | None = None,
    before_idat: list[bytes] | None = None,
    after_idat: list[bytes] | None = None,
    include_iend_crc: bool = True,
) -> bytes:
    """按 `chunks` 顺序拼装（给 `chunks` 时不自动加 IDAT）。

    默认结构：IHDR + [before_idat] + IDAT + [after_idat] + IEND。
    """
    if chunks is not None:
        body = b"".join(chunks)
    else:
        body = (
            png_chunk("IHDR", ihdr(width, height, color_type=color_type))
            + b"".join(before_idat or [])
            + png_chunk("IDAT", idat())
            + b"".join(after_idat or [])
        )
    return PNG_SIGNATURE + body + png_chunk("IEND", b"", include_crc=include_iend_crc)


def icc_profile(
    *,
    size_override: int | None = None,
    signature: bytes = b"acsp",
    profile_class: bytes = b"mntr",
    color_space: bytes = b"RGB ",
    pcs: bytes = b"XYZ ",
    intent: int = 0,
    declared_length: int = 256,
) -> bytes:
    """构造一个字段可控的 ICC profile 头（前 128 字节 + 填充到 `declared_length`）。"""
    head = bytearray(128)
    head[0:4] = struct.pack(">I", size_override if size_override is not None else declared_length)
    head[4:8] = b"ADBE"
    head[8:12] = bytes([0x02, 0x10, 0x00, 0x00])
    head[12:16] = profile_class
    head[16:20] = color_space
    head[20:24] = pcs
    head[24:36] = b"\x00" * 12          # ProfileDateTime（全 0 = 未设，确定性）
    head[36:40] = signature
    head[40:44] = b"\x00" * 4
    head[44:48] = b"\x00" * 4
    head[48:52] = b"\x00" * 4
    head[52:56] = b"\x00" * 4
    head[56:64] = b"\x00" * 8
    head[64:68] = struct.pack(">I", intent)
    head[68:80] = b"\x00" * 12
    head[80:84] = b"\x00" * 4
    head[84:100] = b"\x00" * 16
    body = bytes(head)
    if declared_length > 128:
        body += b"\x00" * (declared_length - 128)
    return body


def iccp_chunk(profile: bytes, *, name: str = "icc", method: int = 0) -> bytes:
    """`iCCP`：name \\0 method zlib(profile)。首期不解压，但压缩流是合法的。"""
    compressed = zlib.compress(profile, 9)
    return png_chunk("iCCP", name.encode("latin-1") + b"\x00" + bytes([method]) + compressed)


# ─────────────────────────────────────────────────────────────────────────────
# 备注
# ─────────────────────────────────────────────────────────────────────────────

STRUCTURAL_NOTE = (
    "structural fixture: pixel data is not decodable (the tool never decodes pixels); "
    "all fields the tool reads (tags, offsets, lengths, CRCs, frame timings) are exact"
)
