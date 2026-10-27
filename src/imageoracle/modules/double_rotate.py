# -*- coding: utf-8 -*-
"""判决层：`double-rotate`（题目 M2）—— 双重旋转探测器。

契约（详见 `plan/03-模块详设.md` §二；判据与阈值**唯一定义处** = `data/README.md` §8.6）：

| # | 条件 | confidence | severity |
|---|---|---|---|
| 1 | IFD0 与 IFD1 的 274 都存在且值不同 | `certain` | `warning` |
| 2 | XMP `tiff:Orientation` 与 EXIF 274 都存在且值不同 | `certain` | `warning` |
| 3 | 声明 5/6/7/8 但容器存储宽 > 高（大边在水平） | `gray-heuristic` | `suspicion` |

输出：`{condition_hits, certain, heuristic, verdicts:[{consumer, condition, trigger_chain,
consequence, evidence}]}`。`certain` 与 `heuristic` **分列**，不得混进同一个分数（`plan/00` R4）。

复用约定：本模块读 `modules.orientation.analyze()` 产出的 `sources` / `primary` / `effective_size`，
**不重读容器、不重复实现 XMP 正则**（`orientation.read_xmp_orientation` 是唯一实现，K17）。

两条刻意留下的边界（改之前先看 `data/README` §8.6 与 `plan/06` D17）：

- **条件 2 只认"两侧都存在且值不同"**。合同原文里"一方存在且非 1 而另一方缺失"那一支**不实现**：
  它会把"EXIF=6 且没有 XMP"这种最常见的正常照片全判成 `certain`，与 M3 出口门
  （M2 的 22 份好样本不得产生 `certain`）以及 K3（`absent` ≠ `=1`）直接冲突。
- **条件 3 只出 `suspicion`**，不进退出码（`data/README` §8.5 不含 `suspicion`）。
"""

from __future__ import annotations

from typing import Any

from ..model import Container
from ..specs import get as get_spec
from . import orientation

MILESTONE = "M3"

#: 条件编号 → 输出码（与 `fixtures/manifest.json` 里 `m3_*` 的 `triggers[].code` 同名）
CONDITION_CODES: dict[int, str] = {
    1: "double_rotate_ifd1_unsynced",
    2: "double_rotate_xmp_conflict",
    3: "double_rotate_bigedge_mismatch",
}

#: 条件编号 → 置信度 / 严重级别（`data/README` §8.6 表）
CONDITION_CONFIDENCE: dict[int, str] = {1: "certain", 2: "certain", 3: "gray-heuristic"}
CONDITION_SEVERITY: dict[int, str] = {1: "warning", 2: "warning", 3: "suspicion"}

#: 条件 3 只对"声明了 90° 类旋转"的值评估
ROTATING_VALUES = frozenset({5, 6, 7, 8})

#: 条件编号 → 事实依据条款（finding 的 `evidence.spec`）
CONDITION_SPEC: dict[int, str] = {
    1: "EXIF-TAG274",
    2: "EXIF-TAG274",
    3: "GRAY-DECODE-REQUIRED",
}

#: "软件 × 触发链"表（`plan/03` §二 的三例）。`consequences` 按条件分列——一条 verdict
#: 只对应**一个**条件，避免把两种成因混进一句结论。
CONSUMER_CHAINS: tuple[dict[str, Any], ...] = (
    {
        "consumer": "jpegtran -copy all -rotate 90",
        "spec": "JPEGTRAN-COPYALL",
        "trigger_chain": (
            "libjpeg-turbo 的 jpegtran 不读方向；-rotate 90 由人指定，-copy all 时"
            ' "Thumbnails are copied as-is and not transformed"'
        ),
        "consequences": {
            1: "主图被转过而 IFD1 缩略图原样复制 → 缩略图仍按旧方向显示，与主图不一致",
        },
    },
    {
        "consumer": "sharp.autoOrient()",
        "spec": "SHARP-AUTOORIENT",
        "trigger_chain": (
            'rotate()/autoOrient() 只按 EXIF tag 274 归一："Only the EXIF Orientation tag is '
            'considered; orientation carried in other places"'
        ),
        "consequences": {
            2: "autoOrient() 把 EXIF 归 1，但未改写 XMP tiff:Orientation → 下游读 XMP 的软件再转一次（#4585）",
            3: "若像素已手工转正而 tag 未重置成 1，autoOrient() 会照着旧 tag 再转一次",
        },
    },
    {
        "consumer": "ImageMagick -auto-orient",
        "spec": "IMAGEMAGICK-AUTOORIENT",
        "trigger_chain": (
            '-auto-orient "reads and resets the EXIF image profile setting \'Orientation\'"；'
            "遇到已被修正但 tag 未重置的图照转不误"
        ),
        "consequences": {
            2: '"images already corrected without resetting the tag may be rotated wrongly a second time"（XMP 侧仍留着旧值）',
            3: '"images already corrected without resetting the tag may be rotated wrongly a second time"',
        },
    },
)


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    """三条件取或；命中几条报几条，`certain` / `heuristic` 分列。

    基线（`sources` / `primary` / `effective_size`）原样透传，便于"先跑 orientation 确认基线"。
    """
    base = orientation.analyze(container)
    sources: list[dict[str, Any]] = base["sources"]

    entries: list[dict[str, Any]] = []

    hit = _condition_1(sources)
    if hit:
        entries.append(hit)

    hit = _condition_2(sources)
    if hit:
        entries.append(hit)

    hit = _condition_3(container, base)
    if hit:
        entries.append(hit)

    certain = [e for e in entries if e["confidence"] == "certain"]
    heuristic = [e for e in entries if e["confidence"] != "certain"]

    # 基线 findings（越界 / 类型错 / 全缺）原样带上：`plan/01` §3 M2 的输入是"M1 解析结果的超集，
    # 同文件可同时出 M1+M2 报告"。若丢掉它们，越界样本会在 `double-rotate` 下静默变成 exit 0
    # ——那是把 error 降级成"干净"，违反退出码纪律。
    findings = list(base["findings"]) + [
        {
            "module": "double-rotate",
            "code": e["code"],
            "severity": e["severity"],
            "confidence": e["confidence"],
            "message": e["message"],
            "evidence": e["evidence"],
        }
        for e in entries
    ]

    return {
        "findings": findings,
        "condition_hits": [e["condition"] for e in entries],
        "certain": certain,
        "heuristic": heuristic,
        "verdicts": _verdicts(entries),
        "sources": sources,
        "primary": base["primary"],
        "effective_size": base["effective_size"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 三个条件（各自返回一条命中记录，或 None）
# ─────────────────────────────────────────────────────────────────────────────

def _condition_1(sources: list[dict[str, Any]]) -> dict[str, Any] | None:
    """IFD0 与 IFD1 的 274 都存在且值不同（缩略图未同步）。"""
    ifd0 = _present(sources, "exif.ifd0.orientation")
    ifd1 = _present(sources, "exif.ifd1.orientation")
    if ifd0 is None or ifd1 is None:
        return None
    if ifd0["value"] == ifd1["value"]:
        return None

    a, b = ifd0["value"], ifd1["value"]
    return _entry(
        1,
        message=(
            f"exif.ifd0.orientation={a} but exif.ifd1.orientation={b} "
            "(thumbnail direction was not synced with the main image)"
        ),
        facts={"exif.ifd0.orientation": a, "exif.ifd1.orientation": b},
        location=ifd1["location"],
    )


def _condition_2(sources: list[dict[str, Any]]) -> dict[str, Any] | None:
    """XMP `tiff:Orientation` 与 EXIF 274 **都存在**且值不同（sharp #4585 形态）。

    "一方缺失"不算冲突——理由见模块 docstring 与 `data/README` §8.6。
    """
    exif = _present(sources, "exif.ifd0.orientation")
    xmp = _present(sources, "xmp.tiff:Orientation")
    if exif is None or xmp is None:
        return None
    if exif["value"] == xmp["value"]:
        return None

    a, b = exif["value"], xmp["value"]
    return _entry(
        2,
        message=(
            f"exif.ifd0.orientation={a} but xmp.tiff:Orientation={b} "
            "(EXIF was normalized while the XMP copy of the same tag was left behind)"
        ),
        facts={"exif.ifd0.orientation": a, "xmp.tiff:Orientation": b},
        location=xmp["location"],
    )


def _condition_3(container: Container, base: dict[str, Any]) -> dict[str, Any] | None:
    """声明 5/6/7/8 且**存储宽 > 高** → 大边启发式命中（只出 `suspicion`）。"""
    primary = base["primary"]
    if primary not in ROTATING_VALUES:
        return None
    info = container.image_info
    if info is None:
        return None
    if not info.width > info.height:
        return None

    stored = [info.width, info.height]
    effective = base["effective_size"]["effective"] if base["effective_size"] else None
    return _entry(
        3,
        message=(
            f"orientation {primary} declares a 90-degree rotation but the stored size is "
            f"{info.width}x{info.height} (wide); the pixels may already be corrected while the tag "
            "was not reset - this needs decoded pixels to confirm"
        ),
        facts={
            "exif.ifd0.orientation": primary,
            "stored": stored,
            "effective": effective,
        },
        location=_size_source_location(container),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 装配
# ─────────────────────────────────────────────────────────────────────────────

def _entry(
    condition: int,
    *,
    message: str,
    facts: dict[str, Any],
    location: dict[str, Any],
) -> dict[str, Any]:
    clause = get_spec(CONDITION_SPEC[condition])
    return {
        "condition": condition,
        "code": CONDITION_CODES[condition],
        "confidence": CONDITION_CONFIDENCE[condition],
        "severity": CONDITION_SEVERITY[condition],
        "message": message,
        "facts": facts,
        "evidence": {"spec": clause.id, "quote": clause.quote, "location": location},
    }


def _verdicts(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """每个命中的（消费者 × 条件）一条 verdict；顺序由 `CONSUMER_CHAINS` 与条件号固定。"""
    hits = {e["condition"]: e for e in entries}
    out: list[dict[str, Any]] = []
    for chain in CONSUMER_CHAINS:
        for condition in sorted(chain["consequences"]):
            entry = hits.get(condition)
            if entry is None:
                continue
            clause = get_spec(chain["spec"])
            out.append(
                {
                    "consumer": chain["consumer"],
                    "condition": condition,
                    "confidence": entry["confidence"],
                    "severity": entry["severity"],
                    "trigger_chain": chain["trigger_chain"],
                    "consequence": chain["consequences"][condition],
                    "evidence": {
                        "spec": clause.id,
                        "quote": clause.quote,
                        "location": entry["evidence"]["location"],
                    },
                }
            )
    return out


def _present(sources: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """取某个来源的 `state == "present"` 记录（`absent` / 越界 / 类型错都不算）。"""
    for source in sources:
        if source["source"] == name and source.get("state") == "present":
            return source
    return None


#: 各容器承载"存储宽高"的块名（`data/README` §1.10 未列，但判据面在这里落点）
_SIZE_CARRIERS = {
    "jpeg": ("SOF0", "SOF1", "SOF2", "SOF3", "SOF5", "SOF6", "SOF7"),
    "png": ("IHDR",),
    "webp": ("VP8X", "VP8", "VP8L"),
}


def _size_source_location(container: Container) -> dict[str, Any]:
    """**存储宽高**的绝对偏移（`plan/03` §0.1：`location.offset` 一律绝对文件偏移）。

    宽度来源随容器不同：JPEG = SOF 段、PNG = IHDR、WebP = VP8X、TIFF = IFD0。
    找不到承载块时 offset 记 0 并在 `chunk` 里说清是哪个结构（宁可少一处偏移，不编造偏移）。
    """
    names = _SIZE_CARRIERS.get(container.kind, ())
    for seg in container.segments:            # JPEG
        if seg.name in names:
            return {"container": container.kind, "chunk": seg.name, "offset": seg.offset}
    for chunk in container.chunks:            # PNG / WebP
        if chunk.type in names:
            return {"container": container.kind, "chunk": chunk.type, "offset": chunk.offset}
    for block in container.exif:              # TIFF（tag 256/257 在 IFD0）
        if block.ifds:
            return {"container": container.kind, "chunk": "IFD0", "offset": block.ifds[0].offset}
    return {"container": container.kind, "chunk": "stored-size", "offset": 0}
