# -*- coding: utf-8 -*-
"""容器层入口：按**文件签名**分派（不按扩展名，不按内容嗅探扩展名）。

只读：以 "rb" 打开，读完即关。不解码像素、不解压图像数据。
"""

from __future__ import annotations

from pathlib import Path

from ..model import Container, ExifBlock, IccRef, XmpBlock
from . import gif as gif_reader
from . import jpeg as jpeg_reader
from . import png as png_reader
from . import tiff as tiff_reader
from . import webp as webp_reader

XMP_JPEG_PREFIX = b"http://ns.adobe.com/xap/1.0/\x00"
EXIF_JPEG_PREFIX = b"Exif\x00\x00"
ICC_JPEG_PREFIX = b"ICC_PROFILE\x00"


class UnsupportedFormat(ValueError):
    """无法识别的容器（→ exit 3）。"""


def sniff(head: bytes) -> str:
    if head.startswith(png_reader.PNG_SIGNATURE):
        return "png"
    if head.startswith(b"\xff\xd8"):
        return "jpeg"
    if head.startswith((gif_reader.GIF87A, gif_reader.GIF89A)):
        return "gif"
    if head.startswith(b"II*\x00") or head.startswith(b"MM\x00*"):
        return "tiff"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "webp"
    raise UnsupportedFormat(f"unrecognized container signature {head[:12]!r}")


def read(path: str | Path) -> Container:
    """读一个文件成统一中间表示。**源文件只读，绝不写回。**"""
    p = Path(path)
    data = p.read_bytes()          # 只读一次，后续全部在内存里切片
    kind = sniff(data[:12])

    container = Container(kind=kind, path=str(path), size=len(data))

    if kind == "jpeg":
        segments, info = jpeg_reader.parse(data)
        container.segments = segments
        container.image_info = info
        _collect_jpeg_metadata(container, segments)
    elif kind == "png":
        chunks, info, frames = png_reader.parse(data)
        container.chunks = chunks
        container.image_info = info
        container.frames = frames
        _collect_png_metadata(container, chunks)
    elif kind == "webp":
        chunks, info, frames = webp_reader.parse(data)
        container.chunks = chunks
        container.image_info = info
        container.frames = frames
        _collect_webp_metadata(container, chunks)
    elif kind == "gif":
        chunks, info, frames = gif_reader.parse(data)
        container.chunks = chunks
        container.image_info = info
        container.frames = frames
    elif kind == "tiff":
        block = tiff_reader.parse(data, container="tiff", base_offset=0)
        container.exif.append(block)
        container.image_info = _tiff_image_info(block, tiff_reader)
        _collect_tiff_icc(container, block, tiff_reader)
    else:  # pragma: no cover - sniff 已穷举
        raise UnsupportedFormat(kind)

    return container


def _collect_jpeg_metadata(container: Container, segments) -> None:
    for seg in segments:
        if seg.name != "APP1":
            continue
        raw = seg.raw_data
        if raw.startswith(EXIF_JPEG_PREFIX):
            try:
                block = tiff_reader.parse(
                    raw[len(EXIF_JPEG_PREFIX):],
                    container="jpeg",
                    base_offset=seg.data_offset + len(EXIF_JPEG_PREFIX),
                )
                container.exif.append(block)
            except tiff_reader.TiffError as exc:
                container.notes.append(f"APP1 Exif unparsable: {exc}")
            continue
        if raw.startswith(XMP_JPEG_PREFIX):
            text = raw[len(XMP_JPEG_PREFIX):].decode("utf-8", errors="replace")
            container.xmp.append(
                XmpBlock(container="jpeg", offset=seg.data_offset, text=text)
            )

    icc_segs = [
        s for s in segments
        if s.name == "APP2" and s.raw_data.startswith(ICC_JPEG_PREFIX)
    ]
    if icc_segs:
        container.icc = IccRef(
            container="jpeg", carrier="APP2", segments=tuple(icc_segs), compressed=False
        )


def _collect_png_metadata(container: Container, chunks) -> None:
    for chunk in chunks:
        if chunk.type == "eXIf":
            # PNG 的 eXIf **不含** `Exif\0\0` 前缀：chunk 数据直接是 TIFF 结构（D10）
            payload = chunk.raw_data
            prefix_skipped = 0
            if payload.startswith(EXIF_JPEG_PREFIX):
                # 容错：少数编码器会带前缀；记录事实而不是静默处理
                payload = payload[len(EXIF_JPEG_PREFIX):]
                prefix_skipped = len(EXIF_JPEG_PREFIX)
                container.notes.append("eXIf chunk carried an unexpected Exif\\0\\0 prefix")
            try:
                block = tiff_reader.parse(
                    payload, container="png", base_offset=chunk.data_offset + prefix_skipped
                )
                container.exif.append(block)
            except tiff_reader.TiffError as exc:
                container.notes.append(f"eXIf unparsable: {exc}")
        elif chunk.type == "iCCP":
            container.icc = IccRef(
                container="png", carrier="iCCP", segments=(chunk,), compressed=True
            )


def _collect_webp_metadata(container: Container, chunks) -> None:
    for chunk in chunks:
        if chunk.type == "EXIF":
            payload = chunk.raw_data
            prefix_skipped = 0
            if payload.startswith(EXIF_JPEG_PREFIX):
                payload = payload[len(EXIF_JPEG_PREFIX):]
                prefix_skipped = len(EXIF_JPEG_PREFIX)
            try:
                block = tiff_reader.parse(
                    payload, container="webp", base_offset=chunk.data_offset + prefix_skipped
                )
                container.exif.append(block)
            except tiff_reader.TiffError as exc:
                container.notes.append(f"EXIF chunk unparsable: {exc}")
        elif chunk.type == "ICCP":
            container.icc = IccRef(
                container="webp", carrier="ICCP", segments=(chunk,), compressed=False
            )
        elif chunk.type == "XMP ":
            text = chunk.raw_data.decode("utf-8", errors="replace")
            container.xmp.append(
                XmpBlock(container="webp", offset=chunk.data_offset, text=text)
            )


def _collect_tiff_icc(container: Container, block: ExifBlock, reader) -> None:
    """TIFF 的 ICC 载在 tag 34675 上（`data/README` §1.11 四种载体之一）。"""
    for ifd in block.ifds:
        entry = reader.get_entry(ifd, reader.TAG_ICC_PROFILE)
        if entry is not None and entry.raw_value:
            container.icc = IccRef(
                container="tiff", carrier="tag34675", segments=(entry,), compressed=False
            )
            return


def _tiff_image_info(block: ExifBlock, reader) -> object:
    if not block.ifds:
        return None
    ifd = block.ifds[0]
    width_entry = reader.get_entry(ifd, reader.TAG_IMAGE_WIDTH)
    height_entry = reader.get_entry(ifd, reader.TAG_IMAGE_LENGTH)
    if not width_entry or not height_entry:
        return None

    def _read(entry):
        if entry.type == 4 and len(entry.raw_value) >= 4:   # LONG
            endian = "<" if block.byte_order == "II" else ">"
            return int.from_bytes(entry.raw_value[:4], "little" if endian == "<" else "big")
        return reader.read_short(entry, block.byte_order)

    from ..model import ImageInfo

    w, h = _read(width_entry), _read(height_entry)
    if w is None or h is None:
        return None
    return ImageInfo(width=w, height=h)
