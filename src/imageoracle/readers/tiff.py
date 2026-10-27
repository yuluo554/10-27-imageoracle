# -*- coding: utf-8 -*-
"""容器层：TIFF / EXIF。只读 IFD 结构，不解释 tag 语义。

**字节序必须按头部 `II`/`MM` 读**，不得固定小端（`data/README` §1.1 核对点）。
"""

from __future__ import annotations

import struct

from ..model import ExifBlock, Ifd, IfdEntry

#: 常见 TIFF 字段类型的字节宽度
TYPE_SIZES = {
    1: 1,   # BYTE
    2: 1,   # ASCII
    3: 2,   # SHORT
    4: 4,   # LONG
    5: 8,   # RATIONAL
    6: 1,   # SBYTE
    7: 1,   # UNDEFINED
    8: 2,   # SSHORT
    9: 4,   # SLONG
    10: 8,  # SRATIONAL
    11: 4,  # FLOAT
    12: 8,  # DOUBLE
    13: 4,  # IFD
}

TAG_ORIENTATION = 274
TAG_IMAGE_WIDTH = 256
TAG_IMAGE_LENGTH = 257
TAG_EXIF_IFD = 0x8769
TAG_ICC_PROFILE = 34675


class TiffError(ValueError):
    """不是可解析的 TIFF/EXIF 结构。"""


def parse(data: bytes, *, container: str, base_offset: int = 0) -> ExifBlock:
    """解析一处 TIFF 结构。

    `base_offset` 是该结构在**外层文件**里的起点（JPEG APP1 的数据起点、PNG eXIf 的
    chunk 数据起点），用于把 IFD 内部偏移换算成绝对偏移。
    """
    if len(data) < 8:
        raise TiffError(f"TIFF header too short ({len(data)} bytes)")

    if data[:2] == b"II":
        byte_order, endian = "II", "<"
    elif data[:2] == b"MM":
        byte_order, endian = "MM", ">"
    else:
        raise TiffError(f"bad TIFF byte order marker {data[:2]!r}")

    magic = struct.unpack(endian + "H", data[2:4])[0]
    if magic != 42:
        raise TiffError(f"bad TIFF magic {magic} (expected 42)")

    ifd0_offset = struct.unpack(endian + "I", data[4:8])[0]
    ifds: list[Ifd] = []
    seen: set[int] = set()

    name, offset = "ifd0", ifd0_offset
    while offset and offset not in seen and len(ifds) < 8:
        seen.add(offset)
        ifd, next_offset = _parse_ifd(data, offset, name, endian, base_offset)
        ifds.append(ifd)
        if name == "ifd0":
            name = "ifd1"
        else:
            name = f"ifd{len(ifds)}"
        offset = next_offset

    return ExifBlock(container=container, offset=base_offset, byte_order=byte_order, ifds=tuple(ifds))


def _parse_ifd(
    data: bytes, offset: int, name: str, endian: str, base_offset: int
) -> tuple[Ifd, int]:
    if offset + 2 > len(data):
        raise TiffError(f"{name} offset {offset} beyond data ({len(data)} bytes)")
    count = struct.unpack(endian + "H", data[offset:offset + 2])[0]
    entries: list[IfdEntry] = []
    pos = offset + 2
    for _ in range(count):
        if pos + 12 > len(data):
            raise TiffError(f"{name} entry at {pos} truncated")
        tag, ftype, n = struct.unpack(endian + "HHI", data[pos:pos + 8])
        size = TYPE_SIZES.get(ftype, 0)
        total = size * n
        if 0 < total <= 4:
            raw = data[pos + 8:pos + 8 + total]
            value_offset = base_offset + pos + 8
        else:
            raw = b""
            value_offset = 0
            if size:
                vo = struct.unpack(endian + "I", data[pos + 8:pos + 12])[0]
                if vo + total <= len(data):
                    raw = data[vo:vo + total]
                    value_offset = base_offset + vo
        entries.append(
            IfdEntry(tag=tag, type=ftype, count=n, value_offset=value_offset, raw_value=raw)
        )
        pos += 12
    next_offset = 0
    if pos + 4 <= len(data):
        next_offset = struct.unpack(endian + "I", data[pos:pos + 4])[0]
    return Ifd(name=name, offset=base_offset + offset, entries=tuple(entries)), next_offset


def read_short(entry: IfdEntry, byte_order: str) -> int | None:
    """读 int16u（type=3）。类型不符 → None（由判决层报"非 int16u"）。"""
    if entry.type != 3 or entry.count < 1 or len(entry.raw_value) < 2:
        return None
    endian = "<" if byte_order == "II" else ">"
    return struct.unpack(endian + "H", entry.raw_value[:2])[0]


def get_entry(ifd: Ifd, tag: int) -> IfdEntry | None:
    for entry in ifd.entries:
        if entry.tag == tag:
            return entry
    return None
