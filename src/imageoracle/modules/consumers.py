# -*- coding: utf-8 -*-
"""判决层：`consumers`（题目 M5）—— 消费者矩阵 + 风险清单 + 加工命令 diff。

契约（`plan/03-模块详设.md` §五）；**表体与口径的唯一定义处 = `data/README.md` §8.9**，
条款原文登记在 §1.13（`tests/test_m6_consumers.py` 解析该表逐字对账）。

输出三件：

1. **消费者矩阵**：9 行（chrome / safari / firefox / macos_preview / windows_photos /
   imagemagick / libvips / sharp / exiftran）× 6 列，每行带 `evidence`；
2. **风险清单**：`{consumer, risk, severity, trigger, confidence, evidence}`；
3. **处理前后 diff**：6 条加工命令（≥4 条硬验收），每条给"哪些 chunk 消失 / 哪些字段变"。

四条边界（改之前先看 `data/README` §8.9）：

- **表体只来自台账**：每行的值都能对回 §2 / §3 / §4 / §1.x，不来自运行时猜测；
  取不到第一方文档的格写 `unknown`（值本身就是"不可判"的声明），行置信度降 `gray`。
- **风险清单的 `severity` 用 risk 词表**（high/medium/low/unknown），**不是** finding 的
  error/warning/info —— 它描述"你若让这个软件处理这张图会发生什么"，不是文件缺陷。
- **本模块只出 `info` finding**：预言不是判缺陷，风险清单不进 `exit_code_for`（§8.9 末段）。
- **M2–M5 的结果不被重算**：方向来源复用 `orientation.analyze()`（K17：XMP 正则只有一处实现），
  容器事实只读 `container.chunks` / `.exif`，不重解析字节。
"""

from __future__ import annotations

from typing import Any

from ..model import Container
from ..specs import get as get_spec
from . import orientation as orientation_module
from .color import RISK_BY_SEVERITY   # severity→risk 只保留一份定义（`data/README` §8.2）

MILESTONE = "M6"

#: 星数与能力矩阵的快照日期（可过期事实，报告头必须写出；`data/README` §2 采集日）
SNAPSHOT_DATE = "2026-10-27"

#: 消费者矩阵的行（固定顺序 = `data/README` §8.9 表序）
CONSUMERS: tuple[str, ...] = (
    "chrome",
    "safari",
    "firefox",
    "macos_preview",
    "windows_photos",
    "imagemagick",
    "libvips",
    "sharp",
    "exiftran",
)

#: 六列的列名（`evidence` 是第 6 列，单独校验）
COLUMNS: tuple[str, ...] = (
    "applies_orientation",
    "applies_icc",
    "dropped_chunks",
    "double_rotate_risk",
    "frame_duration",
)

#: 列取值词表（不在词表里的值 = 实现缺陷，§8.9）
VALUE_VOCAB: dict[str, tuple[str, ...]] = {
    "applies_orientation": ("yes", "partial", "no", "unknown"),
    "applies_icc": ("yes", "no", "unknown"),
    "double_rotate_risk": ("low", "medium", "high", "unknown"),
    "frame_duration": ("per-container-unit", "unknown", "n/a"),
}

#: 证据形态与置信度词表（`plan/03` §五硬验收）
EVIDENCE_KINDS: tuple[str, ...] = ("spec", "tool-doc", "hn-quote")
CONFIDENCES: tuple[str, ...] = ("certain", "single-source", "gray")

#: risk 词表（`data/README` §8.2 的 risk 列，不是 finding 的 severity 词表）
RISK_LEVELS: tuple[str, ...] = ("high", "medium", "low", "unknown")

#: 两条已逐字复核的工具文档页（`data/README` §3.1）——只有这两处允许出现 `tool-doc`
TOOL_DOC_URLS = {
    "sharp": "https://sharp.pixelplumbing.com/api-operation",
    "imagemagick": "https://imagemagick.org/command-line-options/",
}

#: HN 条目地址（`data/README` §4 的 item id）
HN_URLS = {
    "HN-ORIENTATION-PNG": "https://news.ycombinator.com/item?id=46004364",
    "HN-ICC-RENDER": "https://news.ycombinator.com/item?id=46403048",
    "HN-SOFTWARE-EITHER": "https://news.ycombinator.com/item?id=5026565",
}


def _evidence(kind: str, clause_id: str, *, tool: str | None = None) -> dict[str, Any]:
    """按 kind 组证据：`spec` 只要条款；`tool-doc` / `hn-quote` **必须**带 URL（§8.9）。"""
    clause = get_spec(clause_id)
    payload: dict[str, Any] = {
        "kind": kind,
        "spec": clause.id,
        "quote": clause.quote,
        "source": clause.source,
    }
    if kind == "tool-doc":
        payload["url"] = TOOL_DOC_URLS[tool or ""]
    elif kind == "hn-quote":
        payload["url"] = HN_URLS[clause_id]
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# 表体：`data/README.md` §8.9 的机器可读副本
# ─────────────────────────────────────────────────────────────────────────────

MATRIX_ROWS: tuple[dict[str, Any], ...] = (
    {
        "consumer": "chrome",
        "kind": "browser",
        "applies_orientation": "partial",
        "applies_icc": "yes",
        "dropped_chunks": [],
        "double_rotate_risk": "medium",
        "frame_duration": "per-container-unit",
        "confidence": "single-source",
        "note": "JPEG 的 EXIF 方向会应用；PNG 的 eXIf 在 image-orientation: from-image 下没有被采用",
        "evidence": _evidence("hn-quote", "HN-ORIENTATION-PNG"),
    },
    {
        "consumer": "safari",
        "kind": "browser",
        "applies_orientation": "partial",
        "applies_icc": "yes",
        "dropped_chunks": [],
        "double_rotate_risk": "medium",
        "frame_duration": "per-container-unit",
        "confidence": "single-source",
        "note": "与 Chrome 同属 PNG eXIf 缺口；PNG iCCP 的呈现与 Chrome 不同（单来源）",
        "evidence": _evidence("hn-quote", "HN-ICC-RENDER"),
    },
    {
        "consumer": "firefox",
        "kind": "browser",
        "applies_orientation": "unknown",
        "applies_icc": "unknown",
        "dropped_chunks": [],
        "double_rotate_risk": "unknown",
        "frame_duration": "per-container-unit",
        "confidence": "gray",
        "note": "未取到第一方文档（data/README §9 #11）：方向与色彩行为只能标不可判",
        "evidence": _evidence("hn-quote", "HN-SOFTWARE-EITHER"),
    },
    {
        "consumer": "macos_preview",
        "kind": "app",
        "applies_orientation": "unknown",
        "applies_icc": "unknown",
        "dropped_chunks": [],
        "double_rotate_risk": "unknown",
        "frame_duration": "unknown",
        "confidence": "gray",
        "note": "未取到第一方文档（data/README §9 #11）",
        "evidence": _evidence("hn-quote", "HN-SOFTWARE-EITHER"),
    },
    {
        "consumer": "windows_photos",
        "kind": "app",
        "applies_orientation": "unknown",
        "applies_icc": "unknown",
        "dropped_chunks": [],
        "double_rotate_risk": "unknown",
        "frame_duration": "unknown",
        "confidence": "gray",
        "note": "未取到第一方文档（data/README §9 #12）",
        "evidence": _evidence("hn-quote", "HN-SOFTWARE-EITHER"),
    },
    {
        "consumer": "imagemagick",
        "kind": "cli",
        "applies_orientation": "yes",
        "applies_icc": "yes",
        "dropped_chunks": [],
        "double_rotate_risk": "high",
        "frame_duration": "per-container-unit",
        "confidence": "certain",
        "note": "-auto-orient 读并重置 Orientation，按 90 度转；`-profile` 段未取（§9 #5）",
        "evidence": _evidence("tool-doc", "IMAGEMAGICK-AUTOORIENT-RESET", tool="imagemagick"),
    },
    {
        "consumer": "libvips",
        "kind": "library",
        "applies_orientation": "unknown",
        "applies_icc": "yes",
        "dropped_chunks": [],
        "double_rotate_risk": "unknown",
        "frame_duration": "per-container-unit",
        "confidence": "single-source",
        "note": "icc_import 无 profile 时按内置 profile 搜索，不假设 sRGB；autorot 页未取（§9 #4）",
        "evidence": _evidence("spec", "ICC-DEFAULTS"),
    },
    {
        "consumer": "sharp",
        "kind": "library",
        "applies_orientation": "yes",
        "applies_icc": "unknown",
        "dropped_chunks": ["exif_orientation_tag"],
        "double_rotate_risk": "high",
        "frame_duration": "per-container-unit",
        "confidence": "certain",
        "note": "rotate() 无参 = autoOrient()：只认 EXIF，转正后移除该 tag（XMP 里的旧方向留着）",
        "evidence": _evidence("tool-doc", "SHARP-AUTOORIENT-REMOVE", tool="sharp"),
    },
    {
        "consumer": "exiftran",
        "kind": "cli",
        "applies_orientation": "yes",
        "applies_icc": "no",
        "dropped_chunks": [],
        "double_rotate_risk": "low",
        "frame_duration": "n/a",
        "confidence": "certain",
        "note": "读方向、连缩略图一起转、把方向写回 1；JPEG only（不处理动画）",
        "evidence": _evidence("spec", "EXIFTRAN-ROTATE"),
    },
)

#: 风险清单：`severity` 用 risk 词表；`trigger` 机器可读（见 `TRIGGERS`）
RISKS: tuple[dict[str, Any], ...] = (
    {
        "id": "R01",
        "consumer": "imagemagick",
        "risk": "-auto-orient 对「已修正但 tag 未重置」的图会再转一次",
        "severity": "high",
        "trigger": "exif_orientation_present",
        "confidence": "certain",
        "evidence": _evidence("spec", "IMAGEMAGICK-AUTOORIENT"),
    },
    {
        "id": "R02",
        "consumer": "sharp",
        "risk": "autoOrient() 只认 EXIF 并移除该 tag，XMP 里残留的方向留给下游 → 再转一次",
        "severity": "high",
        "trigger": "xmp_orientation_present",
        "confidence": "certain",
        "evidence": _evidence("tool-doc", "SHARP-AUTOORIENT", tool="sharp"),
    },
    {
        "id": "R03",
        "consumer": "chrome",
        "risk": "PNG 的 eXIf 方向不被采用 → 竖拍 PNG 显示成横的",
        "severity": "medium",
        "trigger": "png_exif_orientation_present",
        "confidence": "single-source",
        "evidence": _evidence("hn-quote", "HN-ORIENTATION-PNG"),
    },
    {
        "id": "R04",
        "consumer": "safari",
        "risk": "PNG iCCP 的呈现与 Chrome 不同 → 同一文件两处颜色不一致",
        "severity": "medium",
        "trigger": "png_iccp_present",
        "confidence": "single-source",
        "evidence": _evidence("hn-quote", "HN-ICC-RENDER"),
    },
    {
        "id": "R05",
        "consumer": "jpegtran",
        "risk": "-copy all -rotate 90 主图转了、缩略图原样复制 → IFD1 双重旋转",
        "severity": "high",
        "trigger": "jpeg_ifd1_present",
        "confidence": "certain",
        "evidence": _evidence("spec", "JPEGTRAN-COPYALL"),
    },
    {
        "id": "R06",
        "consumer": "oxipng",
        "risk": "--strip safe 丢掉 gAMA/cHRM（不在保留集）→ 颜色可能改变",
        "severity": "medium",
        "trigger": "png_gama_or_chrm",
        "confidence": "certain",
        "evidence": _evidence("spec", "OXIPNG-STRIP-SAFE"),
    },
    {
        "id": "R07",
        "consumer": "oxipng",
        "risk": "--strip all 把 APNG 转成静态 PNG（动画控制 chunk 全丢）",
        "severity": "high",
        "trigger": "apng_present",
        "confidence": "certain",
        "evidence": _evidence("spec", "OXIPNG-STRIP-ALL"),
    },
    {
        "id": "R08",
        "consumer": "oxipng",
        "risk": "--fix 不做 CRC 校验 → 「用 oxipng 校验过」是伪安全",
        "severity": "medium",
        "trigger": "always",
        "confidence": "certain",
        "evidence": _evidence("spec", "OXIPNG-FIX"),
    },
    {
        "id": "R09",
        "consumer": "exiftran",
        "risk": "JPEG only → 对 PNG / WebP / GIF 完全无效",
        "severity": "low",
        "trigger": "not_jpeg",
        "confidence": "certain",
        "evidence": _evidence("spec", "EXIFTRAN-ROTATE"),
    },
    {
        "id": "R10",
        "consumer": "firefox",
        "risk": "方向 / 色彩行为无可取第一方文档 → 只能标不可判",
        "severity": "unknown",
        "trigger": "always",
        "confidence": "gray",
        "evidence": _evidence("hn-quote", "HN-SOFTWARE-EITHER"),
    },
    {
        "id": "R11",
        "consumer": "macos_preview",
        "risk": "方向 / 色彩行为无可取第一方文档 → 只能标不可判（§9 #11）",
        "severity": "unknown",
        "trigger": "always",
        "confidence": "gray",
        "evidence": _evidence("hn-quote", "HN-SOFTWARE-EITHER"),
    },
    {
        "id": "R12",
        "consumer": "windows_photos",
        "risk": "方向 / 色彩行为无可取第一方文档 → 只能标不可判（§9 #12）",
        "severity": "unknown",
        "trigger": "always",
        "confidence": "gray",
        "evidence": _evidence("hn-quote", "HN-SOFTWARE-EITHER"),
    },
    {
        "id": "R13",
        "consumer": "libvips",
        "risk": "autorot 文档未取（§9 #4）→ 方向行为不可判",
        "severity": "unknown",
        "trigger": "always",
        "confidence": "gray",
        "evidence": _evidence("hn-quote", "HN-SOFTWARE-EITHER"),
    },
)

#: 处理前后 diff：≥4 条加工命令（`plan/03` §五 第 3 项）
PROCESS_DIFFS: tuple[dict[str, Any], ...] = (
    {
        "command": "oxipng --strip safe",
        "container": "png",
        "loses": ["gAMA", "cHRM"],
        "keeps": ["cICP", "iCCP", "sRGB", "pHYs", "acTL", "fcTL", "fdAT"],
        "changes": ["gAMA / cHRM 消失 → 只按 gamma 解释的软件看到的颜色会变"],
        "evidence": _evidence("spec", "OXIPNG-STRIP-SAFE"),
    },
    {
        "command": "oxipng --strip all",
        "container": "png",
        "loses": ["all-ancillary"],
        "keeps": ["IHDR", "PLTE", "IDAT", "IEND"],
        "changes": ["色彩与动画控制 chunk 全丢 → APNG 变成静态 PNG"],
        "evidence": _evidence("spec", "OXIPNG-STRIP-ALL"),
    },
    {
        "command": "oxipng --fix",
        "container": "png",
        "loses": [],
        "keeps": [],
        "changes": ["结构不变；但 oxipng 自己不校验 CRC，坏 CRC 不会被它发现"],
        "evidence": _evidence("spec", "OXIPNG-FIX"),
    },
    {
        "command": "sharp.rotate()",
        "container": "jpeg/png/webp/tiff",
        "loses": ["exif_orientation_tag"],
        "keeps": ["xmp tiff:Orientation"],
        "changes": ["像素转正 + EXIF Orientation tag 被移除；XMP 里的旧方向仍在 → 下游再转一次"],
        "evidence": _evidence("spec", "SHARP-AUTOORIENT-REMOVE"),
    },
    {
        "command": "exiftran",
        "container": "jpeg",
        "loses": [],
        "keeps": [],
        "changes": ["方向 tag 改写为 1；主图与缩略图一起转（JPEG only）"],
        "evidence": _evidence("spec", "EXIFTRAN-ROTATE"),
    },
    {
        "command": "jpegtran -copy all -rotate 90",
        "container": "jpeg",
        "loses": [],
        "keeps": [],
        "changes": ["主图转 90°；IFD1 缩略图原样复制、不参与变换 → 缩略图方向与主图不一致"],
        "evidence": _evidence("spec", "JPEGTRAN-COPYALL"),
    },
)

#: 触发条件的机器可读说明（值是 `_context()` 里的键）
TRIGGERS: dict[str, str] = {
    "always": "任何输入",
    "exif_orientation_present": "读到了 EXIF tag 274（任一 IFD）",
    "xmp_orientation_present": "读到了 XMP tiff:Orientation",
    "png_exif_orientation_present": "容器是 PNG 且读到了方向来源",
    "jpeg_ifd1_present": "容器是 JPEG 且带 IFD1（缩略图）",
    "png_gama_or_chrm": "容器是 PNG 且带 gAMA 或 cHRM",
    "apng_present": "容器是 PNG 且带 acTL（APNG）",
    "png_iccp_present": "容器是 PNG 且带 iCCP",
    "not_jpeg": "容器不是 JPEG",
}


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    """产出矩阵 + 风险清单 + 加工 diff + `info` findings。"""
    context = _context(container)

    active = [risk for risk in RISKS if context[risk["trigger"]]]
    findings: list[dict[str, Any]] = [_matrix_finding(context, active)]
    for diff in PROCESS_DIFFS:
        findings.append(_diff_finding(diff, context))

    return {
        "findings": findings,
        "consumers": [dict(row) for row in MATRIX_ROWS],
        "risks": [dict(risk) for risk in RISKS],
        "process_diffs": [dict(diff) for diff in PROCESS_DIFFS],
        "matrix": {
            "rows": len(MATRIX_ROWS),
            "columns": list(COLUMNS) + ["evidence"],
            "snapshot_date": SNAPSHOT_DATE,
            "risk_rows": len(RISKS),
            "diff_rows": len(PROCESS_DIFFS),
            "active_risks": [risk["id"] for risk in active],
            "tool_doc_rows": sum(1 for row in MATRIX_ROWS if row["evidence"]["kind"] == "tool-doc"),
            "gray_rows": sum(1 for row in MATRIX_ROWS if row["confidence"] == "gray"),        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 把"这张图"的字节事实折进触发条件（不猜、不重解析：只读 M2/M5 的产物）
# ─────────────────────────────────────────────────────────────────────────────

def _context(container: Container) -> dict[str, Any]:
    # 方向来源复用 M2 的实现（K17：XMP 正则只有一处定义）
    orientation = orientation_module.analyze(container)
    sources = orientation.get("sources") or []
    primary = orientation.get("primary")
    xmp_present = any(
        source.get("source") == "xmp.tiff:Orientation" and source.get("value") is not None
        for source in sources
    )

    chunk_types = {chunk.type for chunk in container.chunks}
    ifd_names = {ifd.name for block in container.exif for ifd in block.ifds}
    is_png = container.kind == "png"
    is_jpeg = container.kind == "jpeg"

    return {
        "always": True,
        "exif_orientation_present": primary is not None,
        "xmp_orientation_present": xmp_present,
        "png_exif_orientation_present": is_png and primary is not None,
        "jpeg_ifd1_present": is_jpeg and "ifd1" in ifd_names,
        "png_gama_or_chrm": is_png and bool(chunk_types & {"gAMA", "cHRM"}),
        "apng_present": is_png and "acTL" in chunk_types,
        "png_iccp_present": is_png and "iCCP" in chunk_types,
        "not_jpeg": not is_jpeg,
        # diff 用：这张图里确实存在的"会被丢掉的载体"
        "_chunk_types": chunk_types,
        "_has_ifd1": "ifd1" in ifd_names,
        "_has_primary": primary is not None,
    }


def _lost_tokens_present(diff: dict[str, Any], context: dict[str, Any]) -> list[str]:
    """该命令的 `loses` 里，哪些在这张图上真的存在（逐字对 chunk 名，不做推测）。"""
    chunk_types: set[str] = context["_chunk_types"]
    hits: list[str] = []
    for token in diff["loses"]:
        if token == "all-ancillary":
            if any(chunk[0].islower() for chunk in chunk_types):
                hits.append(token)
        elif token == "exif_orientation_tag":
            if context["_has_primary"]:
                hits.append(token)
        elif token in chunk_types:
            hits.append(token)
    return hits


# ─────────────────────────────────────────────────────────────────────────────
# 装配
# ─────────────────────────────────────────────────────────────────────────────

def _matrix_finding(context: dict[str, Any], active: list[dict[str, Any]]) -> dict[str, Any]:
    return _finding(
        "consumer_matrix",
        "CONSUMER-MATRIX",
        "certain",
        message=(
            f"{len(MATRIX_ROWS)} consumers × {len(COLUMNS) + 1} columns, snapshot {SNAPSHOT_DATE}; "
            f"{len(active)} of {len(RISKS)} documented risks apply to this file"
        ),
        facts={
            "rows": len(MATRIX_ROWS),
            "columns": len(COLUMNS) + 1,
            "snapshot_date": SNAPSHOT_DATE,
            "active_risks": [risk["id"] for risk in active],
            "risk_rows": len(RISKS),
        },
    )


def _diff_finding(diff: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    hits = _lost_tokens_present(diff, context)
    if hits:
        suffix = f" (affects this file: {', '.join(hits)})"
    elif not diff["loses"]:
        suffix = " (no chunk-level loss: the lie is in what the tool does not check)"
    else:
        suffix = " (not triggered by this file)"
    return _finding(
        "process_diff",
        diff["evidence"]["spec"],
        "certain",
        message=(
            f"{diff['command']}: "
            + ("; ".join(diff["changes"]) if diff["changes"] else "no structural change")
            + suffix
        ),
        facts={
            "command": diff["command"],
            "container": diff["container"],
            "loses": list(diff["loses"]),
            "keeps": list(diff["keeps"]),
            "changes": list(diff["changes"]),
            "hits": hits,
        },
    )


def _finding(
    code: str,
    spec_id: str,
    confidence: str,
    *,
    message: str,
    facts: dict[str, Any],
) -> dict[str, Any]:
    clause = get_spec(spec_id)
    severity = "info"   # §8.9 末段：预言不是判缺陷，风险清单不进退出码
    return {
        "module": "consumers",
        "code": code,
        "severity": severity,
        "confidence": confidence,
        "risk": RISK_BY_SEVERITY[severity],
        "message": message,
        "facts": facts,
        "evidence": {
            "spec": clause.id,
            "quote": clause.quote,
            "location": {"container": "any", "chunk": None, "offset": 0},
        },
    }
