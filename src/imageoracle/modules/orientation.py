# -*- coding: utf-8 -*-
"""判决层：`orientation`（题目 M1）。

**数值口径不在本文件定义**：8 元变换矩阵的唯一真源是 `data/README.md` §8.1，
本文件只是它的机器可读副本；`tests/test_m2_orientation.py` 逐行比对两者。

最易搞反的一条（已写成单测）：**6 = Rotate 90 CW = 顺时针 90°**，不是逆时针。
"""

from __future__ import annotations

import re
from typing import Any

from ..model import Container
from ..specs import get as get_spec
from ..readers import tiff as tiff_reader

#: `data/README.md` §8.1 的机器可读副本。顺序 = (flip_h, flip_v, rotate_cw_deg, swap_wh)
ORIENTATION_MATRIX: dict[int, tuple[bool, bool, int, bool]] = {
    1: (False, False, 0, False),
    2: (True, False, 0, False),
    3: (False, False, 180, False),
    4: (False, True, 0, False),
    5: (True, False, 270, True),
    6: (False, False, 90, True),
    7: (True, False, 90, True),
    8: (False, False, 270, True),
}

#: ExifTool 原文标签（断言文案直接引用它，防止日后被"改反"）
ORIENTATION_LABELS: dict[int, str] = {
    1: "Horizontal (normal)",
    2: "Mirror horizontal",
    3: "Rotate 180",
    4: "Mirror vertical",
    5: "Mirror horizontal and rotate 270 CW",
    6: "Rotate 90 CW",
    7: "Mirror horizontal and rotate 90 CW",
    8: "Rotate 270 CW",
}

TAG_ORIENTATION = 274

#: XMP 里可能携带方向的属性（不同写入方用不同的前缀/大小写）
XMP_ORIENTATION_PATTERNS = (
    re.compile(r'tiff:Orientation\s*=\s*["\'](\d+)["\']'),
    re.compile(r'<tiff:Orientation>\s*(\d+)\s*</tiff:Orientation>'),
)


def finding(
    code: str,
    severity: str,
    confidence: str,
    message: str,
    spec_id: str,
    location: dict[str, Any],
) -> dict[str, Any]:
    clause = get_spec(spec_id)
    return {
        "module": "orientation",
        "code": code,
        "severity": severity,
        "confidence": confidence,
        "message": message,
        "evidence": {"spec": clause.id, "quote": clause.quote, "location": location},
    }


def transform_for(value: int) -> dict[str, Any]:
    flip_h, flip_v, rotate, swap = ORIENTATION_MATRIX[value]
    return {
        "flip_h": flip_h,
        "flip_v": flip_v,
        "rotate_cw_deg": rotate,
        "swap_wh": swap,
        "label": ORIENTATION_LABELS[value],
    }


def effective_size(width: int, height: int, value: int) -> tuple[int, int]:
    """5/6/7/8 交换 W/H；2/3/4 不交换。"""
    if ORIENTATION_MATRIX[value][3]:
        return height, width
    return width, height


def analyze(container: Container, *, source: dict[str, Any] | None = None) -> dict[str, Any]:
    """产出 findings + 逐来源原始值 + 变换 + 有效宽高。

    返回值同时供 M3（double-rotate）复用——它读的是同一份 `sources`。
    """
    findings: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    container_kind = container.kind

    for block in container.exif:
        for ifd in block.ifds:
            entry = tiff_reader.get_entry(ifd, TAG_ORIENTATION)
            key = f"exif.{ifd.name}.orientation"
            location = {
                "container": container_kind,
                "chunk": "APP1" if container_kind == "jpeg" else ("eXIf" if container_kind == "png" else block.container),
                "offset": entry.value_offset if entry else block.offset,
                "ifd": ifd.name,
            }

            if entry is None:
                sources.append({"source": key, "value": None, "state": "absent", "location": location})
                continue

            value = tiff_reader.read_short(entry, block.byte_order)
            if value is None:
                findings.append(
                    finding(
                        "orientation_not_int16u",
                        "error",
                        "certain",
                        f"{key} has TIFF type {entry.type} (expected 3/int16u)",
                        "EXIF-TAG274",
                        location,
                    )
                )
                sources.append({"source": key, "value": None, "state": "not_int16u", "location": location})
                continue

            if value not in ORIENTATION_MATRIX:
                findings.append(
                    finding(
                        "orientation_out_of_range",
                        "error",
                        "certain",
                        f"{key} = {value}, outside the defined range 1..8",
                        "EXIF-TAG274",
                        location,
                    )
                )
                sources.append({"source": key, "value": value, "state": "out_of_range", "location": location})
                continue

            sources.append(
                {
                    "source": key,
                    "value": value,
                    "state": "present",
                    "label": ORIENTATION_LABELS[value],
                    "transform": transform_for(value),
                    "location": location,
                }
            )

    for xmp in container.xmp:
        value = _xmp_orientation(xmp.text)
        location = {"container": container_kind, "chunk": "XMP", "offset": xmp.offset}
        if value is None:
            sources.append({"source": "xmp.tiff:Orientation", "value": None, "state": "absent", "location": location})
            continue
        if value not in ORIENTATION_MATRIX:
            findings.append(
                finding(
                    "orientation_out_of_range",
                    "error",
                    "certain",
                    f"xmp.tiff:Orientation = {value}, outside the defined range 1..8",
                    "EXIF-TAG274",
                    location,
                )
            )
            sources.append({"source": "xmp.tiff:Orientation", "value": value, "state": "out_of_range", "location": location})
            continue
        sources.append(
            {
                "source": "xmp.tiff:Orientation",
                "value": value,
                "state": "present",
                "label": ORIENTATION_LABELS[value],
                "transform": transform_for(value),
                "location": location,
            }
        )

    # 有效宽高：只有存在确定方向值时才有意义
    effective = None
    primary = _primary_orientation(sources)
    if primary is not None and container.image_info is not None:
        w, h = effective_size(container.image_info.width, container.image_info.height, primary)
        effective = {"stored": [container.image_info.width, container.image_info.height], "effective": [w, h]}

    if not sources:
        findings.append(
            finding(
                "orientation_absent",
                "info",
                "certain",
                f"no orientation source found in {container_kind}",
                "EXIF-TAG274",
                {"container": container_kind, "chunk": None, "offset": 0},
            )
        )

    return {
        "findings": findings,
        "sources": sources,
        "primary": primary,
        "effective_size": effective,
    }


def _primary_orientation(sources: list[dict[str, Any]]) -> int | None:
    """主图方向：优先 ifd0，其次第一个有值的来源。**不默认 1**（缺失就是缺失）。"""
    for s in sources:
        if s["source"].endswith("ifd0.orientation") and s.get("value") in ORIENTATION_MATRIX:
            return s["value"]
    for s in sources:
        if s.get("value") in ORIENTATION_MATRIX:
            return s["value"]
    return None


def _xmp_orientation(text: str) -> int | None:
    for pattern in XMP_ORIENTATION_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
    return None


def read_xmp_orientation(text: str) -> int | None:
    """供 M3 复用（保持单一实现，避免两处正则漂移）。"""
    return _xmp_orientation(text)
