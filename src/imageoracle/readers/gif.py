# -*- coding: utf-8 -*-
"""容器层：GIF87a/89a。只切块，不解 LZW 图像数据。"""

from __future__ import annotations

import struct

from ..model import Chunk, Frame, ImageInfo

GIF87A = b"GIF87a"
GIF89A = b"GIF89a"

#: Graphic Control Extension 的固定引导
GCE_INTRO = 0x21
GCE_LABEL = 0xF9
IMAGE_SEPARATOR = 0x2C
TRAILER = 0x3B
EXTENSION_INTRO = 0x21


class GifError(ValueError):
    """不是可解析的 GIF（→ exit 3）。"""


def parse(data: bytes) -> tuple[list[Chunk], ImageInfo | None, list[Frame]]:
    if len(data) < 13 or data[:6] not in (GIF87A, GIF89A):
        raise GifError("missing GIF87a/GIF89a header")

    width, height = struct.unpack("<HH", data[6:10])
    info = ImageInfo(width=width, height=height)

    chunks: list[Chunk] = []
    frames: list[Frame] = []
    pos = 13

    # Logical Screen Descriptor 的 packed 字段决定是否有全局色表
    packed = data[10]
    if packed & 0x80:
        gct_size = 3 * (2 ** ((packed & 0x07) + 1))
        chunks.append(
            Chunk(type="GCT", offset=13, length=gct_size, data_offset=13,
                  raw_data=data[13:13 + gct_size])
        )
        pos = 13 + gct_size

    pending_dispose: int | None = None
    pending_delay: int | None = None
    frame_index = 0

    while pos < len(data):
        block = data[pos]

        if block == TRAILER:
            chunks.append(Chunk(type="TRAILER", offset=pos, length=1, data_offset=pos + 1))
            break

        if block == EXTENSION_INTRO and pos + 2 < len(data):
            label = data[pos + 1]
            if label == GCE_LABEL:
                # 0x21 0xF9 blockSize(4) packed delay(2) transparentIndex(1) terminator(1)
                size = data[pos + 2]
                payload_start = pos + 3
                payload = data[payload_start:payload_start + size]
                chunks.append(
                    Chunk(type="GCE", offset=pos, length=size + 3, data_offset=payload_start,
                          raw_data=payload)
                )
                if len(payload) >= 4:
                    gce_packed = payload[0]
                    pending_dispose = (gce_packed >> 2) & 0x07
                    pending_delay = struct.unpack("<H", payload[1:3])[0]
                pos = payload_start + size
                if pos < len(data) and data[pos] == 0x00:
                    pos += 1  # block terminator
                continue

            # 其它扩展（注释 / 应用 / 明文）：跳过 length-prefixed 的子块
            pos += 2
            while pos < len(data) and data[pos] != 0x00:
                pos += data[pos] + 1
            pos += 1
            continue

        if block == IMAGE_SEPARATOR:
            if pos + 10 > len(data):
                raise GifError(f"image descriptor at {pos} truncated")
            img_packed = data[pos + 9]
            local_size = 0
            if img_packed & 0x80:
                local_size = 3 * (2 ** ((img_packed & 0x07) + 1))
            lzw_min = pos + 10 + local_size
            if lzw_min >= len(data):
                raise GifError(f"image data at {pos} truncated")
            # 跳过 LZW 子块
            p = lzw_min + 1
            while p < len(data) and data[p] != 0x00:
                p += data[p] + 1
            p += 1
            raw = data[pos:p]
            chunks.append(
                Chunk(type="IMAGE", offset=pos, length=len(raw), data_offset=pos, raw_data=raw)
            )

            frame_index += 1
            delay_cs = pending_delay if pending_delay is not None else 0
            frames.append(
                Frame(
                    index=frame_index,
                    duration_ms=delay_cs * 10,      # 1/100 s → ms
                    raw_duration=delay_cs,
                    raw_unit="1/100s",
                    dispose=pending_dispose if pending_dispose is not None else 0,
                )
            )
            pending_dispose = None
            pending_delay = None
            pos = p
            continue

        # 未知块：无法安全前进，停止解析（判决层会看到结构不完整）
        chunks.append(
            Chunk(type=f"0x{block:02X}", offset=pos, length=1, data_offset=pos + 1)
        )
        pos += 1

    return chunks, info, frames
