# -*- coding: utf-8 -*-
"""语义层：统一中间表示。

只描述**结构**（偏移 / 长度 / 类型字节），不判对错。判决层只读这些结构，
于是"跨容器同一件事"（如一帧的时长、一个 IFD 的 tag）只写一次。

本模块不 import 任何第三方包，也不读时钟。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImageInfo:
    """从头部字段读到的图像基本信息（**不解码像素**）。"""

    width: int
    height: int
    bit_depth: int | None = None
    color_type: int | None = None  # PNG color type / JPEG 通道数 / GIF 无此概念
    precision: int | None = None   # JPEG SOF precision
    progressive: bool | None = None  # JPEG: SOF2/SOF10 = True


@dataclass(frozen=True)
class Chunk:
    """一个容器块（PNG chunk / RIFF chunk / GIF block）。

    `offset` 一律是**绝对文件偏移**；`data_offset` 是块数据起点。
    """

    type: str
    offset: int
    length: int
    data_offset: int
    crc: int | None = None
    crc_offset: int | None = None
    raw_data: bytes = b""


@dataclass(frozen=True)
class Segment:
    """JPEG 段（marker + 长度 + 数据起点）。"""

    marker: int
    name: str
    offset: int
    length: int
    data_offset: int
    raw_data: bytes = b""


@dataclass(frozen=True)
class IfdEntry:
    tag: int
    type: int
    count: int
    value_offset: int
    raw_value: bytes


@dataclass(frozen=True)
class Ifd:
    """一个 IFD（ifd0 = 主图，ifd1 = 缩略图）。"""

    name: str
    offset: int
    entries: tuple[IfdEntry, ...] = ()


@dataclass(frozen=True)
class ExifBlock:
    """一处 EXIF/TIFF 结构。`byte_order` ∈ {"II", "MM"}，决定 int16u 的读法。"""

    container: str
    offset: int
    byte_order: str
    ifds: tuple[Ifd, ...] = ()


@dataclass(frozen=True)
class XmpBlock:
    container: str
    offset: int
    text: str


@dataclass(frozen=True)
class IccRef:
    """ICC profile 的载体引用（尚未拼接/解压）。"""

    container: str
    carrier: str            # "APP2" | "iCCP" | "ICCP" | "tag34675"
    segments: tuple[Segment | Chunk, ...] = ()
    total_length: int | None = None
    compressed: bool = False


@dataclass(frozen=True)
class Frame:
    """动画帧的**归一化**时长，单位整数毫秒（`data/README` §8.3）。"""

    index: int
    duration_ms: int | None      # None = 该格式的时长不在样本内（AVIF）
    raw_duration: int | None
    raw_unit: str                # "1/100s" | "num/den" | "ms" | "not-in-band"
    dispose: int | None = None


@dataclass
class Container:
    kind: str
    path: str
    size: int
    image_info: ImageInfo | None = None
    chunks: list[Chunk] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    exif: list[ExifBlock] = field(default_factory=list)
    xmp: list[XmpBlock] = field(default_factory=list)
    icc: IccRef | None = None
    frames: list[Frame] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
