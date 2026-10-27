# -*- coding: utf-8 -*-
"""容器层：PNG / APNG。只切 chunk，不解压 IDAT，不做 CRC 校验（那属于 M5 判决层）。

CRC 计算放在这里是因为它是**结构解析**的一部分，但**判定**（报不报错）在 modules/container。
APNG 的帧时长（`fcTL` 的 `delay_num`/`delay_den`）也在这里切成 `Frame`——判决层只读归一化结果，
不重解析 chunk 字节（`data/README` §8.3 的整数口径只实现一次）。
"""

from __future__ import annotations

import struct
import zlib

from ..model import Chunk, Frame, ImageInfo

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: PNG `iCCP` chunk 里 profile 名与压缩流的分隔（name\\0 compression_method profile）
ICCP_COMPRESSION_METHOD_NULL = 0x00


class PngError(ValueError):
    """不是可解析的 PNG（→ exit 3）。"""


def parse(data: bytes) -> tuple[list[Chunk], ImageInfo | None, list[Frame]]:
    if not data.startswith(PNG_SIGNATURE):
        raise PngError("missing PNG signature")

    chunks: list[Chunk] = []
    frames: list[Frame] = []
    info: ImageInfo | None = None
    pos = len(PNG_SIGNATURE)

    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype_bytes = data[pos + 4:pos + 8]
        try:
            ctype = ctype_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise PngError(f"non-ASCII chunk type at {pos}") from exc

        data_offset = pos + 8
        data_end = data_offset + length
        crc_offset = data_end
        crc = None
        if crc_offset + 4 <= len(data):
            crc = struct.unpack(">I", data[crc_offset:crc_offset + 4])[0]

        raw = data[data_offset:data_end] if data_end <= len(data) else data[data_offset:]
        chunks.append(
            Chunk(type=ctype, offset=pos, length=length, data_offset=data_offset,
                  crc=crc, crc_offset=crc_offset, raw_data=raw)
        )

        if ctype == "IHDR" and len(raw) >= 13 and info is None:
            width, height = struct.unpack(">II", raw[:8])
            bit_depth = raw[8]
            color_type = raw[9]
            info = ImageInfo(width=width, height=height, bit_depth=bit_depth, color_type=color_type)

        if ctype == "fcTL" and len(raw) >= 26:
            frame = _fctl_frame(len(frames) + 1, raw)
            if frame is not None:
                frames.append(frame)

        pos = data_end + 4
        if ctype == "IEND":
            break

    return chunks, info, frames


def _fctl_frame(index: int, raw: bytes) -> Frame | None:
    """`fcTL` 载荷 → `Frame`。`delay_den == 0` 按 100 处理（`data/README` §1.6 / §8.3）。"""
    try:
        (_seq, _w, _h, _x, _y, delay_num, delay_den,
         dispose_op, _blend_op) = struct.unpack(">IIIIIHHBB", raw[:26])
    except struct.error:        # pragma: no cover - 上面已判 len(raw) >= 26
        return None
    den = delay_den or 100
    return Frame(
        index=index,
        duration_ms=delay_num * 1000 // den,   # 整数运算，不出浮点（§8.3）
        raw_duration=delay_num,
        raw_unit="num/den",
        dispose=dispose_op,
        raw_den=delay_den,
    )


def chunk_bytes(chunk: Chunk) -> bytes:
    """chunk type + data —— CRC 的**覆盖范围**（不含 length，`data/README` §1.4）。"""
    return chunk.type.encode("ascii") + chunk.raw_data


def compute_crc(chunk: Chunk) -> int:
    return zlib.crc32(chunk_bytes(chunk)) & 0xFFFFFFFF


def parse_iccp(chunk: Chunk) -> tuple[str, bytes, int] | None:
    """拆 `iCCP`：返回 (profile_name, compressed_bytes, compression_method) 或 None。

    **不解压**（`plan/00` D9）。压缩流原样返回，供判决层标
    `unknown: compressed_profile_not_inspected`。
    """
    raw = chunk.raw_data
    nul = raw.find(b"\x00")
    if nul < 0 or nul + 2 > len(raw):
        return None
    try:
        name = raw[:nul].decode("latin-1")
    except UnicodeDecodeError:
        return None
    method = raw[nul + 1]
    return name, raw[nul + 2:], method
