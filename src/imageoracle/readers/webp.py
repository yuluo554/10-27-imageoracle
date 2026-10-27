# -*- coding: utf-8 -*-
"""容器层：WebP（RIFF 容器）。只切 chunk，不解码 VP8/VP8L/ANMF 图像数据。"""

from __future__ import annotations

import struct

from ..model import Chunk, Frame, ImageInfo

RIFF = b"RIFF"
WEBP = b"WEBP"


class WebpError(ValueError):
    """不是可解析的 WebP（→ exit 3）。"""


def parse(data: bytes) -> tuple[list[Chunk], ImageInfo | None, list[Frame]]:
    if len(data) < 12 or data[:4] != RIFF or data[8:12] != WEBP:
        raise WebpError("missing RIFF/WEBP header")

    riff_size = struct.unpack("<I", data[4:8])[0]
    end = min(len(data), 8 + riff_size)

    chunks: list[Chunk] = []
    frames: list[Frame] = []
    info: ImageInfo | None = None
    pos = 12
    frame_index = 0

    while pos + 8 <= end:
        fourcc_bytes = data[pos:pos + 4]
        try:
            fourcc = fourcc_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise WebpError(f"non-ASCII chunk fourcc at {pos}") from exc
        length = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        data_offset = pos + 8
        data_end = data_offset + length
        raw = data[data_offset:min(data_end, len(data))]

        chunks.append(
            Chunk(type=fourcc, offset=pos, length=length, data_offset=data_offset, raw_data=raw)
        )

        if fourcc == "VP8X" and len(raw) >= 10 and info is None:
            w = 1 + int.from_bytes(raw[4:7], "little")
            h = 1 + int.from_bytes(raw[7:10], "little")
            info = ImageInfo(width=w, height=h)

        if fourcc == "ANMF" and len(raw) >= 16:
            # ANMF: Frame X(3) Y(3) Width-1(3) Height-1(3) Duration(3) Flags(1)
            duration = int.from_bytes(raw[12:15], "little")
            flags = raw[15]
            dispose = (flags >> 0) & 0x01
            frame_index += 1
            frames.append(
                Frame(
                    index=frame_index,
                    duration_ms=duration,          # 已经是 1 ms 单位
                    raw_duration=duration,
                    raw_unit="ms",
                    dispose=dispose,
                )
            )

        # RIFF chunk 按偶数字节对齐
        pos = data_end + (length & 1)

    return chunks, info, frames


def anim_info(chunk: Chunk) -> dict[str, object] | None:
    """拆 `ANIM`：Background Color(u32, BGRA) + Loop Count(u16, 0=无限)。"""
    raw = chunk.raw_data
    if len(raw) < 6:
        return None
    bg = raw[:4]
    loop = struct.unpack("<H", raw[4:6])[0]
    return {
        "background_bgra": [bg[0], bg[1], bg[2], bg[3]],
        "loop_count": loop,
        "loop_infinite": loop == 0,
    }
