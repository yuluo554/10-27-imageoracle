# -*- coding: utf-8 -*-
"""容器层：JPEG。只切段，不解释语义。

覆盖：SOI → APPn → DQT/DHT → SOF0/SOF2 → SOS。**不解码像素**，不做熵解码。
"""

from __future__ import annotations

from ..model import ImageInfo, Segment

#: 有长度的段（SOI/EOI/RSTn 之外都是）
SOF_MARKERS = {
    0xC0: ("SOF0", False),   # baseline
    0xC1: ("SOF1", False),
    0xC2: ("SOF2", True),    # progressive
    0xC3: ("SOF3", False),
    0xC5: ("SOF5", False),
    0xC6: ("SOF6", False),
    0xC7: ("SOF7", False),
    0xC9: ("SOF9", True),
    0xCA: ("SOF10", True),
    0xCB: ("SOF11", True),
    0xCD: ("SOF13", True),
    0xCE: ("SOF14", True),
    0xCF: ("SOF15", True),
}

STANDALONE_MARKERS = {0xD8: "SOI", 0xD9: "EOI"}
STANDALONE_MARKERS.update({m: f"RST{i}" for i, m in enumerate(range(0xD0, 0xD8))})


class JpegError(ValueError):
    """输入不是可解析的 JPEG（→ exit 3）。"""


def parse(data: bytes) -> tuple[list[Segment], ImageInfo | None]:
    """返回 (段列表, ImageInfo|None)。偏移一律绝对文件偏移。"""
    if len(data) < 2 or data[0] != 0xFF or data[1] != 0xD8:
        raise JpegError("missing SOI (FF D8)")

    segments: list[Segment] = []
    info: ImageInfo | None = None
    pos = 0

    while pos < len(data):
        if data[pos] != 0xFF:
            # 填充字节或熵编码数据（SOS 之后）；跳到下一个标记
            nxt = data.find(b"\xff", pos)
            if nxt < 0:
                break
            pos = nxt
            continue

        # 跳过 0xFF 填充
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            break

        marker = data[pos]
        marker_offset = pos - 1

        if marker in STANDALONE_MARKERS:
            segments.append(
                Segment(marker=marker, name=STANDALONE_MARKERS[marker], offset=marker_offset,
                        length=0, data_offset=pos + 1)
            )
            pos += 1
            continue

        if marker == 0x00:  # FF00 = 熵编码里的转义
            pos += 1
            continue

        if pos + 2 >= len(data):
            break
        length = (data[pos + 1] << 8) | data[pos + 2]
        if length < 2:
            raise JpegError(f"segment at {marker_offset} has invalid length {length}")
        data_start = pos + 3
        data_end = pos + 1 + length
        if data_end > len(data):
            raise JpegError(f"segment 0x{marker:02X} at {marker_offset} truncated")

        name = SOF_MARKERS.get(marker, (f"0x{marker:02X}", False))[0]
        if marker not in SOF_MARKERS:
            if 0xE0 <= marker <= 0xEF:
                name = f"APP{marker - 0xE0}"
            elif marker == 0xDB:
                name = "DQT"
            elif marker == 0xC4:
                name = "DHT"
            elif marker == 0xDD:
                name = "DRI"
            elif marker == 0xFE:
                name = "COM"
            elif marker == 0xDA:
                name = "SOS"
            elif marker == 0xEE:
                name = "APP14"

        segments.append(
            Segment(marker=marker, name=name, offset=marker_offset, length=length,
                    data_offset=data_start, raw_data=data[data_start:data_end])
        )

        if marker in SOF_MARKERS and info is None:
            info = _parse_sof(name, data[data_start:data_end], marker)

        pos = data_end

        if marker == 0xDA:  # SOS 之后是熵编码字节流，扫到下一个真正的标记
            pos = _skip_entropy(data, pos)

    return segments, info


def _parse_sof(name: str, payload: bytes, marker: int) -> ImageInfo:
    # payload 从精度开始：precision(1) height(2) width(2) ncomp(1) ...
    if len(payload) < 6:
        raise JpegError(f"{name} payload too short ({len(payload)} bytes)")
    precision = payload[0]
    height = (payload[1] << 8) | payload[2]
    width = (payload[3] << 8) | payload[4]
    ncomp = payload[5]
    return ImageInfo(
        width=width,
        height=height,
        bit_depth=precision,
        color_type=ncomp,
        precision=precision,
        progressive=SOF_MARKERS.get(marker, (name, False))[1],
    )


def _skip_entropy(data: bytes, pos: int) -> int:
    """跳过熵编码数据：FF00 是转义，FF D0-D7 是 RST，其它 FF xx 是下一个段。"""
    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        nxt = data[pos + 1]
        if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
            pos += 2
            continue
        return pos
    return len(data)


def find_segments(segments: list[Segment], name: str) -> list[Segment]:
    return [s for s in segments if s.name == name]
