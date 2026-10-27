# -*- coding: utf-8 -*-
"""判决层：`container`（题目 M4）—— 容器结构校验器 + 跨格式帧时长归一化。

契约（详见 `plan/03-模块详设.md` §四）。**检查项与级别的唯一定义处 = `data/README.md` §8.8**；
**帧时长归一化与 `unit_mismatch` 判据的唯一定义处 = §8.3**；条款原文在 §1.12。

| # | 检查 | 结果码 |
|---|---|---|
| 1 | PNG chunk 顺序（IHDR 首 / IEND 末 / PLTE / 色彩 chunk / `acTL,eXIf,pHYs,sPLT` / `bKGD,hIST,tRNS` / `fcTL` / `fdAT`） | `png_chunk_order`(error) |
| 2 | CRC = `chunk type + data`（**不含 length**），每个 chunk 都要有 | `png_crc_mismatch` / `png_crc_missing`(error) |
| 3 | `IDAT` 连续 | `png_idat_nonconsecutive`(error) |
| 4 | APNG：`num_frames == fcTL count`；首序号 0；序号单调无缺口无重复；`delay_den==0→100`；`acTL` 在首 IDAT 前 | `apng_num_frames_mismatch` / `apng_sequence_gap`(error) |
| 5 | WebP：`ANIM`（BGRA / Loop u16）/ `ANMF` duration 24-bit ms / 内部边界 | `webp_anim_structure` / `webp_anmf_truncated`(error) |
| 6 | GIF：disposal 含 4–7 / delay 1/100 s / GCE 位置 | `gif_disposal_undefined`(warning) / `gif_gce_position`(error) |
| 7 | JPEG 段顺序 + APP14 位置 | `jpeg_segment_order` / `jpeg_app14_position`(error) |
| 8 | 跨格式帧时长归一化到 ms + `unit_mismatch`（10× / 1×） | `frame_duration_normalized`(info) / `unit_mismatch`(warning) |

三条边界（改之前先看 `data/README` §8.3 / §8.8）：

- **层职责**：`readers/` 只切结构（PNG 的 `fcTL` 时长也在 reader 里切成 `Frame`），本模块只读
  `container.chunks` / `.segments` / `.frames` / `.image_info`，**不重解析字节**、不做像素解码。
- **CRC 覆盖范围不含 length**：`readers/png.py::compute_crc` 是唯一实现，本模块只比较"存储值 vs 计算值"。
- **`unit_mismatch` 不是启发式**：触发条件是 §8.3 的数值判据（假读值恰为 100 ms 而声明单位不是），
  假阳性代价（合法的 1 s GIF / 10 ms WebP）已在 §8.3 声明；其余判据全是结构事实。

CRC 已知向量单测：`crc32(b"IEND") == 0xAE426082`（`data/README` §1.4）。
"""

from __future__ import annotations

import struct
from typing import Any

from ..model import Container, Frame
from ..readers import png as png_reader
from ..specs import get as get_spec
from .color import RISK_BY_SEVERITY   # severity→risk 只保留一份定义（`data/README` §8.2）

MILESTONE = "M5"

#: 结果码 → (severity, confidence)。级别口径 = `data/README` §8.8。
SEVERITY = {
    "png_chunk_order": ("error", "certain"),
    "png_idat_nonconsecutive": ("error", "certain"),
    "png_crc_mismatch": ("error", "certain"),
    "png_crc_missing": ("error", "certain"),
    "apng_num_frames_mismatch": ("error", "certain"),
    "apng_sequence_gap": ("error", "certain"),
    "webp_anmf_truncated": ("error", "certain"),
    "webp_anim_structure": ("error", "certain"),
    "gif_disposal_undefined": ("warning", "certain"),
    "gif_gce_position": ("error", "certain"),
    "jpeg_segment_order": ("error", "certain"),
    "jpeg_app14_position": ("error", "certain"),
    "unit_mismatch": ("warning", "certain"),
    "frame_duration_normalized": ("info", "certain"),
}

#: 结果码 → 事实依据条款（`evidence.spec`，必须是 `specs.CLAUSES` 里的 ID）
CODES_SPEC = {
    "png_chunk_order": "PNG3-T7",
    "png_idat_nonconsecutive": "PNG3-T7",
    "png_crc_mismatch": "PNG3-CRC",
    "png_crc_missing": "PNG3-CRC-PRESENT",
    "apng_num_frames_mismatch": "APNG-SEQ",
    "apng_sequence_gap": "APNG-SEQ",
    "webp_anmf_truncated": "WEBP-ANMF",
    "webp_anim_structure": "WEBP-ANIM",
    "gif_disposal_undefined": "GIF89A-GCE",
    "gif_gce_position": "GIF89A-GCE-SCOPE",
    "jpeg_segment_order": "JPEG-T81-FRAME",
    "jpeg_app14_position": "JPEG-T81-FRAME",
    "unit_mismatch": "FRAME-UNITS",
    "frame_duration_normalized": "FRAME-UNITS",
}

#: PNG-3 Table 7（`data/README` §1.3）：位置约束分组
PNG_BEFORE_PLTE_AND_IDAT = ("cHRM", "cICP", "gAMA", "iCCP", "sBIT", "sRGB")
PNG_BEFORE_IDAT = ("acTL", "eXIf", "pHYs", "sPLT")
PNG_AFTER_PLTE_BEFORE_IDAT = ("bKGD", "hIST", "tRNS")

#: 跨格式 100 ms 参照（`data/README` §1.9）：GIF=10 / APNG=10/100 / WebP=100
REFERENCE_MS = 100

#: ANIM 载荷固定 6 字节 = Background Color(u32, BGRA) + Loop Count(u16, 0=无限)（§1.7）
ANIM_PAYLOAD_SIZE = 6

#: ANMF 固定头部 16 字节（FrameX/Y/W-1/H-1 各 3 + Duration 3 + Flags 1）（§1.7）
ANMF_HEADER_SIZE = 16

#: GIF disposal 4–7 是 "To be defined"（§1.8）→ warning，不是 error
GIF_UNDEFINED_DISPOSALS = frozenset({4, 5, 6, 7})


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    """按容器类型跑结构检查，返回错误清单 + 归一化帧时长表。"""
    findings: list[dict[str, Any]] = []

    if container.kind == "png":
        _check_png_chunk_order(container, findings)
        _check_png_crc(container, findings)
        _check_apng(container, findings)
    elif container.kind == "webp":
        _check_webp(container, findings)
    elif container.kind == "gif":
        _check_gif(container, findings)
    elif container.kind == "jpeg":
        _check_jpeg(container, findings)
    else:
        # TIFF 等不在 §四 的容器面内：记事实（报告头 container.notes 会带出），不假装"检查过了"
        container.notes.append(
            f"container checks are not defined for {container.kind} "
            "(PNG/APNG/WebP/GIF/JPEG only)"
        )

    frames = [_frame_dict(frame) for frame in container.frames]
    _check_frame_durations(container, findings)

    return {
        "findings": findings,
        "frames": frames,
        "container_facts": _container_facts(container),
    }


def _container_facts(container: Container) -> dict[str, Any]:
    return {
        "kind": container.kind,
        "chunks": len(container.chunks),
        "segments": len(container.segments),
        "frames": len(container.frames),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1 / 2 / 3. PNG：chunk 顺序 + CRC + IDAT 连续
# ─────────────────────────────────────────────────────────────────────────────

def _check_png_chunk_order(container: Container, findings: list[dict[str, Any]]) -> None:
    chunks = container.chunks
    if not chunks:
        return

    types = [chunk.type for chunk in chunks]
    if types[0] != "IHDR":
        findings.append(
            _png_order(chunks[0], "IHDR shall be the first chunk", f"first chunk is {types[0]}")
        )
    if types[-1] != "IEND":
        findings.append(
            _png_order(chunks[-1], "IEND shall be last", f"last chunk is {types[-1]}")
        )

    first_idat = types.index("IDAT") if "IDAT" in types else None
    plte_index = types.index("PLTE") if "PLTE" in types else None
    color_type = container.image_info.color_type if container.image_info is not None else None

    if plte_index is not None and color_type in (0, 4):
        findings.append(
            _png_order(
                chunks[plte_index],
                f"PLTE is not allowed for color type {color_type}",
                "PLTE present",
            )
        )
    if "tRNS" in types and color_type in (4, 6):
        trns = chunks[types.index("tRNS")]
        findings.append(
            _png_order(trns, f"tRNS is not allowed for color type {color_type}", "tRNS present")
        )

    for chunk_type in PNG_BEFORE_PLTE_AND_IDAT:
        for index, chunk in enumerate(chunks):
            if chunk.type != chunk_type:
                continue
            if first_idat is not None and index > first_idat:
                findings.append(_png_order(chunk, "before IDAT", f"{chunk_type} after IDAT"))
            elif plte_index is not None and index > plte_index:
                findings.append(_png_order(chunk, "before PLTE", f"{chunk_type} after PLTE"))

    for chunk_type in PNG_BEFORE_IDAT:
        for index, chunk in enumerate(chunks):
            if chunk.type == chunk_type and first_idat is not None and index > first_idat:
                findings.append(_png_order(chunk, "before IDAT", f"{chunk_type} after IDAT"))

    for chunk_type in PNG_AFTER_PLTE_BEFORE_IDAT:
        for index, chunk in enumerate(chunks):
            if chunk.type != chunk_type:
                continue
            if plte_index is not None and index < plte_index:
                findings.append(_png_order(chunk, "after PLTE", f"{chunk_type} before PLTE"))
            if first_idat is not None and index > first_idat:
                findings.append(_png_order(chunk, "before IDAT", f"{chunk_type} after IDAT"))

    # fcTL：允许一个在 IDAT 前，其余必须在 IDAT 后（§1.3 / §1.6）
    fctl_before = [
        index for index, chunk in enumerate(chunks)
        if chunk.type == "fcTL" and (first_idat is None or index < first_idat)
    ]
    if len(fctl_before) > 1:
        findings.append(
            _png_order(
                chunks[fctl_before[1]],
                "One fcTL may occur before IDAT; all others shall be after IDAT",
                f"{len(fctl_before)} fcTL chunks before IDAT",
            )
        )

    # fdAT 必须在 IDAT 之后
    for index, chunk in enumerate(chunks):
        if chunk.type == "fdAT" and (first_idat is None or index < first_idat):
            findings.append(_png_order(chunk, "fdAT after IDAT", "fdAT before IDAT"))

    # IDAT 连续：首个与最后一个 IDAT 之间不得夹其它 chunk
    idat_indices = [index for index, chunk in enumerate(chunks) if chunk.type == "IDAT"]
    if len(idat_indices) >= 2:
        for index in range(idat_indices[0], idat_indices[-1] + 1):
            if types[index] != "IDAT":
                findings.append(
                    _finding(
                        "png_idat_nonconsecutive",
                        message=(
                            f"IDAT chunks are not consecutive: {types[index]} at offset "
                            f"{chunks[index].offset} sits between IDAT chunks"
                        ),
                        location={"container": "png", "chunk": "IDAT", "offset": chunks[index].offset},
                        facts={
                            "chunk": "IDAT",
                            "rule": "Multiple IDAT chunks shall be consecutive",
                            "interrupted_by": types[index],
                        },
                    )
                )
                break


def _png_order(chunk, rule: str, detail: str) -> dict[str, Any]:
    return _finding(
        "png_chunk_order",
        message=f"PNG chunk order violation: {chunk.type} at offset {chunk.offset} — {detail}",
        location={"container": "png", "chunk": chunk.type, "offset": chunk.offset},
        facts={"chunk": chunk.type, "rule": rule, "offset": chunk.offset},
    )


def _check_png_crc(container: Container, findings: list[dict[str, Any]]) -> None:
    """CRC = chunk type + data（不含 length）；每个 chunk 都必须有 4 字节 CRC（§1.4）。"""
    for chunk in container.chunks:
        location = {"container": "png", "chunk": chunk.type, "offset": chunk.offset}
        if chunk.crc is None:
            findings.append(
                _finding(
                    "png_crc_missing",
                    message=(
                        f"{chunk.type} chunk at offset {chunk.offset} has no 4-byte CRC "
                        "(CRC is always present, even for empty chunk data)"
                    ),
                    location=location,
                    facts={"chunk": chunk.type, "offset": chunk.offset},
                )
            )
            continue
        computed = png_reader.compute_crc(chunk)
        if chunk.crc != computed:
            findings.append(
                _finding(
                    "png_crc_mismatch",
                    message=(
                        f"{chunk.type} chunk CRC is 0x{chunk.crc:08X} but chunk type + data "
                        f"give 0x{computed:08X} (length is not covered)"
                    ),
                    location=location,
                    facts={
                        "chunk": chunk.type,
                        "offset": chunk.offset,
                        "stored": chunk.crc,
                        "computed": computed,
                    },
                )
            )


# ─────────────────────────────────────────────────────────────────────────────
# 4. APNG：num_frames / 序号 / acTL 位置
# ─────────────────────────────────────────────────────────────────────────────

def _check_apng(container: Container, findings: list[dict[str, Any]]) -> None:
    chunks = container.chunks
    actls = [chunk for chunk in chunks if chunk.type == "acTL"]
    fctls = [chunk for chunk in chunks if chunk.type == "fcTL"]
    if not actls and not fctls:
        return

    if actls and len(actls[0].raw_data) >= 4:
        declared = struct.unpack(">I", actls[0].raw_data[:4])[0]
        actual = len(fctls)
        if declared != actual:
            findings.append(
                _finding(
                    "apng_num_frames_mismatch",
                    message=(
                        f"acTL.num_frames says {declared} but the stream holds {actual} fcTL chunk(s)"
                    ),
                    location={"container": "png", "chunk": "acTL", "offset": actls[0].offset},
                    facts={"declared": declared, "actual": actual},
                )
            )

    shared = _apng_sequences(chunks)
    if not shared:
        return
    values = [sequence for _chunk_type, sequence, _chunk in shared]
    fctl_sequences = [sequence for chunk_type, sequence, _chunk in shared if chunk_type == "fcTL"]
    problem = _apng_sequence_problem(values, fctl_sequences)
    if problem is None:
        return

    first = shared[0][2]
    findings.append(
        _finding(
            "apng_sequence_gap",
            message=(
                f"APNG sequence numbers must start at 0, be in order and have no gaps or "
                f"duplicates; stream holds {values} ({problem})"
            ),
            location={"container": "png", "chunk": first.type, "offset": first.offset},
            facts={
                "sequence": fctl_sequences,
                "shared_sequence": values,
                "expected": list(range(len(values))),
                "problem": problem,
            },
        )
    )


def _apng_sequences(chunks) -> list[tuple[str, int, Any]]:
    """`fcTL` / `fdAT` 共享一个 sequence_number 序列（`data/README` §1.6，按生成器口径）。"""
    out: list[tuple[str, int, Any]] = []
    for chunk in chunks:
        if chunk.type in ("fcTL", "fdAT") and len(chunk.raw_data) >= 4:
            out.append((chunk.type, struct.unpack(">I", chunk.raw_data[:4])[0], chunk))
    return out


def _apng_sequence_problem(values: list[int], fctl_sequences: list[int]) -> str | None:
    if fctl_sequences and fctl_sequences[0] != 0:
        return "first_sequence_nonzero"
    if len(set(values)) != len(values):
        return "duplicate"
    if any(later <= earlier for earlier, later in zip(values, values[1:])):
        return "out_of_order"
    if values != list(range(len(values))):
        return "gap"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. WebP：ANIM 结构 + ANMF 边界
# ─────────────────────────────────────────────────────────────────────────────

def _check_webp(container: Container, findings: list[dict[str, Any]]) -> None:
    for chunk in container.chunks:
        if chunk.type == "ANIM":
            _check_anim(chunk, findings)
        elif chunk.type == "ANMF":
            _check_anmf(container, chunk, findings)


def _check_anim(chunk, findings: list[dict[str, Any]]) -> None:
    """ANIM 载荷固定 6 字节 = Background Color(u32, BGRA) + Loop Count(u16)（§1.7）。"""
    location = {"container": "webp", "chunk": "ANIM", "offset": chunk.offset}
    if chunk.length != ANIM_PAYLOAD_SIZE or len(chunk.raw_data) != ANIM_PAYLOAD_SIZE:
        findings.append(
            _finding(
                "webp_anim_structure",
                message=(
                    f"ANIM payload is {chunk.length} byte(s); RFC 9649 fixes it at 6 "
                    "(Background Color u32, BGRA + Loop Count u16). An extra field means the "
                    "Loop Count was written as u32 / before the Background Color"
                ),
                location=location,
                facts={
                    "chunk": "ANIM",
                    "fields": "Background/Loop swapped",
                    "size": chunk.length,
                    "expected_size": ANIM_PAYLOAD_SIZE,
                    "available": len(chunk.raw_data),
                },
            )
        )


def _check_anmf(container: Container, chunk, findings: list[dict[str, Any]]) -> None:
    available = max(0, container.size - chunk.data_offset)
    if chunk.length > available or len(chunk.raw_data) < ANMF_HEADER_SIZE:
        findings.append(
            _finding(
                "webp_anmf_truncated",
                message=(
                    f"ANMF declares {chunk.length} byte(s) but only {available} byte(s) remain "
                    f"and {len(chunk.raw_data)} byte(s) were read (header alone needs 16)"
                ),
                location={"container": "webp", "chunk": "ANMF", "offset": chunk.offset},
                facts={
                    "chunk": "ANMF",
                    "declared": chunk.length,
                    "available": available,
                    "payload": len(chunk.raw_data),
                },
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. GIF：disposal + GCE 作用域
# ─────────────────────────────────────────────────────────────────────────────

def _check_gif(container: Container, findings: list[dict[str, Any]]) -> None:
    chunks = container.chunks
    for index, chunk in enumerate(chunks):
        if chunk.type != "GCE":
            continue
        following = chunks[index + 1] if index + 1 < len(chunks) else None
        if following is None or following.type != "IMAGE":
            findings.append(
                _finding(
                    "gif_gce_position",
                    message=(
                        f"Graphic Control Extension at offset {chunk.offset} is followed by "
                        f"{following.type if following else 'end of file'}, not an image block "
                        "(its scope is the first graphic rendering block that follows)"
                    ),
                    location={"container": "gif", "chunk": "GCE", "offset": chunk.offset},
                    facts={
                        "gce_offset": chunk.offset,
                        "next": following.type if following else None,
                    },
                )
            )

    for frame in container.frames:
        if frame.dispose in GIF_UNDEFINED_DISPOSALS:
            findings.append(
                _finding(
                    "gif_disposal_undefined",
                    message=(
                        f"GIF frame {frame.index} uses Disposal Method {frame.dispose}, "
                        "which GIF89a leaves 'To be defined'"
                    ),
                    location={
                        "container": "gif",
                        "chunk": "GCE",
                        "offset": _frame_offset(container, frame.index),
                    },
                    facts={"disposal": frame.dispose, "frame": frame.index},
                )
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. JPEG：段顺序 + APP14 位置
# ─────────────────────────────────────────────────────────────────────────────

def _check_jpeg(container: Container, findings: list[dict[str, Any]]) -> None:
    segments = container.segments
    if not segments:
        return

    sos = [segment for segment in segments if segment.name == "SOS"]
    sof = [segment for segment in segments if segment.name.startswith("SOF")]

    if sos and sof and sof[0].offset > sos[0].offset:
        findings.append(
            _finding(
                "jpeg_segment_order",
                message=(
                    f"{sof[0].name} at offset {sof[0].offset} comes after the first SOS at "
                    f"{sos[0].offset}; a frame shall begin with a frame header"
                ),
                location={"container": "jpeg", "chunk": sof[0].name, "offset": sof[0].offset},
                facts={"before": sos[0].name, "after": sof[0].name},
            )
        )

    if sos:
        for segment in segments:
            if segment.name == "APP14" and segment.offset > sos[0].offset:
                findings.append(
                    _finding(
                        "jpeg_app14_position",
                        message=(
                            f"APP14 at offset {segment.offset} comes after the first SOS at "
                            f"{sos[0].offset}; miscellaneous (APPn) marker segments precede a scan header"
                        ),
                        location={"container": "jpeg", "chunk": "APP14", "offset": segment.offset},
                        facts={"segment": "APP14", "after": "SOS"},
                    )
                )


# ─────────────────────────────────────────────────────────────────────────────
# 8. 跨格式帧时长：归一化表 + unit_mismatch
# ─────────────────────────────────────────────────────────────────────────────

def _check_frame_durations(container: Container, findings: list[dict[str, Any]]) -> None:
    for frame in container.frames:
        findings.append(
            _finding(
                "frame_duration_normalized",
                message=(
                    f"{container.kind} frame {frame.index}: {frame.raw_duration} {frame.raw_unit} "
                    f"→ {frame.duration_ms} ms"
                ),
                location={
                    "container": container.kind,
                    "chunk": _frame_carrier(container.kind),
                    "offset": _frame_offset(container, frame.index),
                },
                facts=_frame_finding_facts(frame),
            )
        )
        mismatch = _unit_mismatch(container, frame)
        if mismatch is not None:
            findings.append(mismatch)


def _frame_offset(container: Container, index: int) -> int:
    """第 N 帧对应 chunk 的**绝对文件偏移**（GCE / fcTL / ANMF）。"""
    carrier = _frame_carrier(container.kind)
    seen = 0
    for chunk in container.chunks:
        if chunk.type == carrier:
            seen += 1
            if seen == index:
                return chunk.offset
    return 0


def _frame_finding_facts(frame: Frame) -> dict[str, Any]:
    """finding 的 facts 用短名（`ms` / `raw`），与 `fixtures/manifest.json` 的 expected 对齐；
    顶层 `frames` 表用长名（`duration_ms` / `raw_duration`）。两者同源、不各算一遍。"""
    facts: dict[str, Any] = {
        "index": frame.index,
        "ms": frame.duration_ms,
        "raw": frame.raw_duration,
        "raw_unit": frame.raw_unit,
        "dispose": frame.dispose,
    }
    if frame.raw_den is not None:
        facts["delay_num"] = frame.raw_duration
        facts["delay_den"] = frame.raw_den
    return facts


def _frame_carrier(kind: str) -> str:
    return {"gif": "GCE", "png": "fcTL", "webp": "ANMF"}.get(kind, kind)


def _alternate_ms(kind: str, frame: Frame) -> int | None:
    """把 raw 值按**另一格式的单位**假读一次（`data/README` §8.3 的 `alt_ms`）。"""
    if frame.raw_duration is None:
        return None
    if kind == "gif":
        return frame.raw_duration                 # 1/100 s 字段当 ms 读
    if kind == "webp":
        return frame.raw_duration * 10            # ms 字段当 1/100 s 读
    if kind == "png":                             # APNG：delay_num 当 ms 读
        return frame.raw_duration
    return None


def _unit_mismatch(container: Container, frame: Frame) -> dict[str, Any] | None:
    """§8.3：假读值恰为 100 ms 而声明单位归一化值不是 → `warning: unit_mismatch`。"""
    if frame.duration_ms is None:
        return None
    kind = container.kind
    alt_ms = _alternate_ms(kind, frame)
    if alt_ms != REFERENCE_MS or frame.duration_ms == REFERENCE_MS:
        return None

    declared = frame.duration_ms
    factor = max(declared, REFERENCE_MS) // min(declared, REFERENCE_MS)
    scale = "10x" if declared > REFERENCE_MS else "1/10x"
    facts: dict[str, Any] = {
        "raw": frame.raw_duration,
        "raw_unit": frame.raw_unit,
        "ms": declared,
        "alternate_ms": alt_ms,
        "expected_ms": REFERENCE_MS,
        "factor": factor,
        "scale": scale,
    }
    if frame.raw_den is not None:
        facts["delay_num"] = frame.raw_duration
        facts["delay_den"] = frame.raw_den
    return _finding(
        "unit_mismatch",
        message=(
            f"{kind} frame {frame.index}: {frame.raw_duration} {frame.raw_unit} normalises to "
            f"{declared} ms, but reading the same number with the other format's unit gives "
            f"exactly {REFERENCE_MS} ms — indistinguishable from a {scale} unit miswrite"
        ),
        location={
            "container": kind,
            "chunk": _frame_carrier(kind),
            "offset": _frame_offset(container, frame.index),
        },
        facts=facts,
    )


def _frame_dict(frame: Frame) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "index": frame.index,
        "duration_ms": frame.duration_ms,
        "raw_duration": frame.raw_duration,
        "raw_unit": frame.raw_unit,
        "dispose": frame.dispose,
    }
    if frame.raw_den is not None:
        payload["raw_den"] = frame.raw_den
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# 装配
# ─────────────────────────────────────────────────────────────────────────────

def _finding(
    code: str,
    *,
    message: str,
    location: dict[str, Any],
    facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    severity, confidence = SEVERITY[code]
    clause = get_spec(CODES_SPEC[code])
    return {
        "module": "container",
        "code": code,
        "severity": severity,
        "confidence": confidence,
        "risk": RISK_BY_SEVERITY[severity],
        "message": message,
        "facts": facts or {},
        "evidence": {"spec": clause.id, "quote": clause.quote, "location": location},
    }
