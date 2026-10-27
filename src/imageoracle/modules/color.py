# -*- coding: utf-8 -*-
"""判决层：`color`（题目 M3）—— 色彩体检器。

契约（详见 `plan/03-模块详设.md` §三）。**校验项与级别的唯一定义处 = `data/README.md` §8.2**；
**默认假设表的唯一定义处 = `data/README.md` §8.7**（本文件只放它的机器可读副本，
`tests/test_m4_defaults.py` 解析该表逐行对账，不在测试里另抄一份）。

| # | 检查 | 结果码 |
|---|---|---|
| 1 | ICC 存在性（JPEG APP2 多段拼接 + 段号 `i/n` 连续；PNG `iCCP`；WebP `ICCP`；TIFF 34675） | `icc_missing`(info) / `icc_present`(info) / `icc_segment_gap`(error) |
| 2 | 128B 头逐字段（`ProfileSize` / `ProfileClass@12` / `ColorSpaceData@16` / PCS@20 / `acsp`@36 / `RenderingIntent@64`） | 见 §8.2 表 |
| 3 | PNG `iCCP` ↔ `sRGB` 并存 | `warning: iccp_srgb_conflict` |
| 4 | `gAMA` / `cHRM` 有无组合（PNG） | `info: color_markers` |
| 5 | 位深（若不解码读不到 → `unknown`） | `info: color_bit_depth` / `unknown: color_bit_depth_unknown` |
| 6 | CMYK JPEG（四分量 / APP14 `transform`） | `warning: cmyk_jpeg` |
| 7 | **默认假设表 7 行，逐行带 `source`** | `info: color_default_assumption` |

两条刻意留下的边界（改之前先看 `data/README` §8.2 / §8.7 与 `plan/06` D9/D19）：

- **PNG `iCCP` 不解压是硬约束**（`plan/00` D9）：PNG 侧一律
  `unknown: compressed_profile_not_inspected`，**不许**为了"让损坏样本报 error"而加 zlib 解压
  （`tests/test_layering.py::TestRedLines` 的 `zlib.decompress` 禁令会当场抓住）。
  三类损坏各造 PNG + JPEG APP2 **双承载**样本，两条行为都被证明——这才是"范围限定"而不是"漏实现"。
- **`cmyk_jpeg` 的触发条件收窄为"四分量 JPEG"**（`plan/06` D19）：题目原文写"存在 Adobe APP14
  `transform` 字段即告警"，但普通 YCbCr 的 Adobe JPEG 也带 APP14（`transform=1`），照抄会把
  最常见的好样本报成 CMYK。APP14 `transform` 仍作为 **fact** 报出，不作触发依据。

**绝不出色值**：本模块不做颜色变换、不引 lcms；只报"各方默认 + 依据 + 风险级别"。
"""

from __future__ import annotations

import struct
from typing import Any

from ..model import Container
from ..readers import png as png_reader
from ..specs import get as get_spec

MILESTONE = "M4"

#: ICC 128B 头（`data/README` §1.2 偏移表）
ICC_HEAD_MIN = 128
OFF_PROFILE_SIZE = 0
OFF_PROFILE_CLASS = 12
OFF_COLOR_SPACE = 16
OFF_PCS = 20
OFF_SIGNATURE = 36
OFF_RENDERING_INTENT = 64

#: `ProfileClass`（§1.2 / §8.2）：白名单 / ICC 合法但非首期白名单（报 `info`）
KNOWN_CLASSES = frozenset({"mntr", "scnr", "prtr"})
OTHER_LEGAL_CLASSES = frozenset({"spac", "abst", "nmcl"})

#: `ColorSpaceData` / `ProfileConnectionSpace` 的已知集合（§1.2 原文含尾随空格）
KNOWN_SPACES = frozenset({"RGB ", "CMYK", "GRAY", "XYZ ", "Lab "})

#: JPEG APP2 里 ICC profile 的引导
ICC_JPEG_PREFIX = b"ICC_PROFILE\x00"

#: 结果码 → (severity, confidence)。级别口径 = `data/README` §8.2。
SEVERITY = {
    "icc_missing": ("info", "certain"),
    "icc_present": ("info", "certain"),
    "icc_segment_gap": ("error", "certain"),
    "icc_header_truncated": ("error", "certain"),
    "icc_bad_signature": ("error", "certain"),
    "icc_size_mismatch": ("error", "certain"),
    "icc_unknown_class": ("warning", "certain"),
    "icc_class_legal": ("info", "certain"),
    "icc_unknown_space": ("warning", "certain"),
    "icc_bad_intent": ("warning", "certain"),
    "compressed_profile_not_inspected": ("unknown", "gray"),
    "iccp_srgb_conflict": ("warning", "certain"),
    "cmyk_jpeg": ("warning", "certain"),
    "color_markers": ("info", "certain"),
    "color_default_assumption": ("info", "certain"),
    "color_bit_depth": ("info", "certain"),
    "color_bit_depth_unknown": ("unknown", "gray"),
}

#: 结果码 → 事实依据条款（`evidence.spec`，必须是 `specs.CLAUSES` 里的 ID）
CODES_SPEC = {
    "icc_missing": "ICC-CARRIERS",
    "icc_present": "ICC-CARRIERS",
    "icc_segment_gap": "ICC-CARRIERS",
    "icc_header_truncated": "ICC-HEAD",
    "icc_bad_signature": "ICC-HEAD",
    "icc_size_mismatch": "ICC-HEAD",
    "icc_unknown_class": "ICC-HEAD",
    "icc_class_legal": "ICC-HEAD",
    "icc_unknown_space": "ICC-HEAD",
    "icc_bad_intent": "ICC-HEAD",
    "compressed_profile_not_inspected": "ICC-NOT-INSPECTED",
    "iccp_srgb_conflict": "PNG3-ICCP-SRGB",
    "cmyk_jpeg": "CMYK-APP14",
    "color_markers": "PNG-COLOR-CHUNKS",
    "color_default_assumption": "ICC-DEFAULTS",
    "color_bit_depth": "COLOR-BITDEPTH",
    "color_bit_depth_unknown": "COLOR-BITDEPTH",
}

#: severity → `risk`（`plan/03` §三 / `plan/01` §3 的确定性纪律：只出
#: `risk: high/medium/low/unknown` + 依据，**绝不出具体色值**）。
#: 映射的唯一定义处 = `data/README` §8.2 里那张 `risk` 表；改这里要同步改那张表。
RISK_BY_SEVERITY = {
    "error": "high",
    "warning": "medium",
    "unknown": "unknown",
    "info": "low",
    "suspicion": "low",
}

#: 默认假设表（**机器可读副本**）：逐行带 `source`。唯一定义处 = `data/README.md` §8.7。
#: 硬验收（`plan/05` §二 M4 出口门 + `plan/03` §三 第 7 项）：**恰好 7 行，每行有 source**。
#: D2 的纪律：不得写"大家都假设 sRGB"——libvips 那行的原文恰恰说"不假设 sRGB"。
DEFAULT_ASSUMPTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "png-no-color-chunk",
        "situation": "PNG 无任何色彩 chunk（无 `iCCP`/`sRGB`/`gAMA`/`cHRM`）",
        "assumed": "多数软件按 sRGB 解释",
        "source": "HN @kloch 31112951、@meindnoch 50137766（原话）",
    },
    {
        "id": "png-srgb-chunk",
        "situation": "PNG 有 `sRGB` chunk",
        "assumed": "显式 sRGB，无需猜测",
        "source": "PNG-3 `sRGB` chunk 定义",
    },
    {
        "id": "png-gama-chrm-no-iccp",
        "situation": "PNG 有 `gAMA`/`cHRM` 但无 `iCCP`",
        "assumed": "依实现各自解释，常见「只取 gamma」",
        "source": "lr0 案例：`Gamma: 0.454545` 被点名为 ImageMagick 的假设",
    },
    {
        "id": "png-iccp",
        "situation": "PNG 有 `iCCP`",
        "assumed": "应应用该 profile；Chrome 与 Safari 的行为有分歧",
        "source": "lr0 案例（单来源）",
    },
    {
        "id": "png-iccp-compressed",
        "situation": "PNG 的 `iCCP` 是 zlib 压缩流（首期不解压）",
        "assumed": "无法判读色彩语义 → `unknown`，不假设任何默认",
        "source": "`data/README` §8.2 末行（`plan/00` D9）",
    },
    {
        "id": "libvips-icc-import-missing",
        "situation": "ICC 缺失且调用 libvips `icc_import`",
        "assumed": "不假设 sRGB：按 embedded → input_profile 文件 → 内置兼容 profile 三处搜索",
        "source": "libvips `icc_import` 文档原文（`data/README` §3）",
    },
    {
        "id": "jpeg-no-icc",
        "situation": "JPEG 无 ICC",
        "assumed": "常见假设 sRGB（非规范强制）",
        "source": "⬜ 待补原文（`data/README` §9）",
    },
)


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    """ICC 体检 + 色彩标记 + 位深 + CMYK，加默认假设表（原样透出基线的容器事实）。"""
    findings: list[dict[str, Any]] = []

    icc = _inspect_icc(container, findings)
    markers = _collect_markers(container, findings)
    _report_bit_depth(container, findings)
    _check_cmyk(container, findings)
    _report_defaults(container, findings, markers)

    return {
        "findings": findings,
        "icc": icc,
        "color_markers": markers,
        "default_assumptions": [dict(row) for row in DEFAULT_ASSUMPTIONS],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1 / 2. ICC 存在性 + 128B 头逐字段
# ─────────────────────────────────────────────────────────────────────────────

def _inspect_icc(container: Container, findings: list[dict[str, Any]]) -> dict[str, Any]:
    ref = container.icc
    if ref is None:
        findings.append(
            _finding(
                "icc_missing",
                message=(
                    f"no ICC profile carrier found in {container.kind} "
                    "(JPEG APP2 / PNG iCCP / WebP ICCP / TIFF tag 34675)"
                ),
                location={"container": container.kind, "chunk": None, "offset": 0},
                facts={"container": container.kind},
            )
        )
        return {
            "present": False,
            "carrier": None,
            "compressed": False,
            "segments": 0,
            "profile_length": None,
            "inspected": False,
            "header": None,
        }

    carrier = ref.carrier
    profile, segments, location = _icc_payload(container, ref)
    findings.append(
        _finding(
            "icc_present",
            message=f"ICC profile present via {carrier} ({len(profile)} byte(s))",
            location=location,
            facts={"carrier": carrier, "profile_length": len(profile), "segments": segments},
        )
    )
    # 拼接连续性问题是"存在之后"的细节：把它的 finding 排到 `icc_present` 之后（顺序稳定）
    gap = _segment_gap_finding(container, ref)
    if gap is not None:
        findings.append(gap)

    info: dict[str, Any] = {
        "present": True,
        "carrier": carrier,
        "compressed": ref.compressed,
        "segments": segments,
        "profile_length": len(profile),
        "inspected": False,
        "header": None,
    }

    # PNG `iCCP` 是 zlib 压缩流：首期不解压（D9）→ 只出 unknown，不解析头
    if ref.compressed:
        findings.append(
            _finding(
                "compressed_profile_not_inspected",
                message=(
                    f"{carrier} carries a zlib-compressed profile ({len(profile)} byte(s)); "
                    "not decompressed in this release - the 128-byte header was not inspected"
                ),
                location=location,
                facts={"carrier": carrier, "compressed_length": len(profile)},
            )
        )
        return info

    header = _parse_header(profile, location, findings)
    if header is not None:
        info["inspected"] = True
        info["header"] = header
    return info


def _icc_payload(container: Container, ref) -> tuple[bytes, int, dict[str, Any]]:
    """把 ICC 载体还原成**未压缩 profile 字节**。返回 (profile, 段数, location)。

    JPEG APP2：按段号 `i/n` 拼接；连续性检查在 `_segment_gap_finding` 里另出一 find。
    PNG `iCCP`：压缩流原样（**不解压**）。WebP `ICCP` / TIFF 34675：原样。
    """
    chunks = list(ref.segments)

    if ref.carrier == "iCCP":
        chunk = chunks[0]
        parsed = png_reader.parse_iccp(chunk)
        compressed = chunk.raw_data if parsed is None else parsed[1]
        return compressed, 1, {"container": container.kind, "chunk": "iCCP", "offset": chunk.offset}

    if ref.carrier == "APP2":
        pieces = [_app2_piece(seg) for seg in chunks]
        location = {"container": container.kind, "chunk": "APP2", "offset": chunks[0].offset}
        profile = b"".join(payload for _seq, _total, payload in sorted(pieces))
        return profile, len(pieces), location

    # WebP `ICCP` / TIFF tag 34675：单载体，原样
    chunk = chunks[0] if chunks else None
    if chunk is None:
        return b"", 0, {"container": container.kind, "chunk": ref.carrier, "offset": 0}
    raw = getattr(chunk, "raw_data", None)
    if raw is None:                                 # TIFF IfdEntry 用 raw_value
        raw = getattr(chunk, "raw_value", b"")
    if hasattr(chunk, "offset"):
        offset = chunk.offset
    else:
        offset = getattr(chunk, "value_offset", 0)
    return raw, 1, {"container": container.kind, "chunk": ref.carrier, "offset": offset}


def _app2_piece(seg) -> tuple[int, int, bytes]:
    """拆一段 APP2：返回 (seq, total, 分片字节)。"""
    raw = seg.raw_data
    body = raw[len(ICC_JPEG_PREFIX):] if raw.startswith(ICC_JPEG_PREFIX) else raw
    seq = body[0] if len(body) >= 1 else 0
    total = body[1] if len(body) >= 2 else 0
    return seq, total, body[2:]


def _segment_gap_finding(container: Container, ref) -> dict[str, Any] | None:
    """JPEG APP2 分段连续性：段号 `i/n` 必须连续且声明总数 == 实到段数（§8.2 #1）。"""
    if ref.carrier != "APP2":
        return None
    pieces = [_app2_piece(seg) for seg in ref.segments]
    seqs = sorted(seq for seq, _total, _payload in pieces)
    totals = sorted({total for _seq, total, _payload in pieces})
    expected = list(range(1, len(pieces) + 1))
    if totals == [len(pieces)] and seqs == expected:
        return None
    location = {"container": container.kind, "chunk": "APP2", "offset": ref.segments[0].offset}
    return _finding(
        "icc_segment_gap",
        message=(
            f"ICC APP2 segment numbering is not continuous: seq={seqs}, "
            f"declared totals={totals}, segments={len(pieces)}"
        ),
        location=location,
        facts={"carrier": "APP2", "segments": len(pieces), "seq": seqs, "declared_totals": totals},
    )


def _parse_header(
    profile: bytes, location: dict[str, Any], findings: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """128B 头逐字段（`data/README` §1.2 偏移表 + §8.2 级别）。长度不足 → error 并停。"""
    actual = len(profile)
    if actual < ICC_HEAD_MIN:
        findings.append(
            _finding(
                "icc_header_truncated",
                message=f"ICC header is {actual} byte(s), shorter than the required 128",
                location=location,
                facts={"length": actual},
            )
        )
        return None

    header = {
        "ProfileSize": struct.unpack(">I", profile[0:4])[0],
        "ProfileCMMType": _ascii(profile[4:8]),
        "ProfileVersion": profile[8:12].hex(),
        "ProfileClass": _ascii(profile[12:16]),
        "ColorSpaceData": _ascii(profile[16:20]),
        "ProfileConnectionSpace": _ascii(profile[20:24]),
        "ProfileDateTime": profile[24:36].hex(),
        "ProfileFileSignature": _ascii(profile[36:40]),
        "PrimaryPlatform": _ascii(profile[40:44]),
        "CMMFlags": struct.unpack(">I", profile[44:48])[0],
        "DeviceManufacturer": _ascii(profile[48:52]),
        "DeviceModel": _ascii(profile[52:56]),
        "DeviceAttributes": struct.unpack(">Q", profile[56:64])[0],
        "RenderingIntent": struct.unpack(">I", profile[64:68])[0],
        "ConnectionSpaceIlluminant": profile[68:80].hex(),
        "ProfileCreator": _ascii(profile[80:84]),
        "ProfileID": profile[84:100].hex(),
    }

    declared = header["ProfileSize"]
    if declared != actual:
        findings.append(
            _finding(
                "icc_size_mismatch",
                message=(
                    f"ProfileSize field says {declared} but the carrier holds {actual} byte(s)"
                ),
                location=location,
                facts={"declared": declared, "actual": actual},
            )
        )

    signature = header["ProfileFileSignature"]
    if signature != "acsp":
        findings.append(
            _finding(
                "icc_bad_signature",
                message=(
                    f"ProfileFileSignature@36 is {signature!r}, expected 'acsp' "
                    "(this is not an ICC profile)"
                ),
                location=location,
                facts={"signature": signature},
            )
        )

    profile_class = header["ProfileClass"]
    if profile_class in KNOWN_CLASSES:
        pass
    elif profile_class in OTHER_LEGAL_CLASSES:
        findings.append(
            _finding(
                "icc_class_legal",
                message=(
                    f"ProfileClass {profile_class!r} is legal per ICC but outside the "
                    "first-release display/input/output whitelist"
                ),
                location=location,
                facts={"profile_class": profile_class},
            )
        )
    else:
        findings.append(
            _finding(
                "icc_unknown_class",
                message=f"ProfileClass {profile_class!r} is not a known ICC profile class",
                location=location,
                facts={"profile_class": profile_class},
            )
        )

    for field in ("ColorSpaceData", "ProfileConnectionSpace"):
        value = header[field]
        if value not in KNOWN_SPACES:
            findings.append(
                _finding(
                    "icc_unknown_space",
                    message=f"{field} {value!r} is outside the known set {sorted(KNOWN_SPACES)}",
                    location=location,
                    facts={"field": field, "value": value},
                )
            )

    intent = header["RenderingIntent"]
    if intent not in (0, 1, 2, 3):
        findings.append(
            _finding(
                "icc_bad_intent",
                message=f"RenderingIntent@64 is {intent}, outside 0..3",
                location=location,
                facts={"rendering_intent": intent},
            )
        )

    return header


def _ascii(raw: bytes) -> str:
    """4 字节 ASCII 字段：latin-1 解码后只去掉尾随 NUL（保留内部/尾随空格，`RGB ` 有空格）。"""
    return raw.decode("latin-1", errors="replace").rstrip("\x00")


# ─────────────────────────────────────────────────────────────────────────────
# 3 / 4. PNG 色彩标记（`iCCP` / `sRGB` / `gAMA` / `cHRM`）与互斥
# ─────────────────────────────────────────────────────────────────────────────

def _collect_markers(container: Container, findings: list[dict[str, Any]]) -> dict[str, Any] | None:
    """PNG 专有：`iCCP`/`sRGB`/`gAMA`/`cHRM` 的有无组合（lr0 案例的成因面）。"""
    if container.kind != "png":
        return None

    by_type: dict[str, list[Any]] = {}
    for chunk in container.chunks:
        by_type.setdefault(chunk.type, []).append(chunk)

    iccp = by_type.get("iCCP", [])
    srgb = by_type.get("sRGB", [])
    gama = by_type.get("gAMA", [])
    chrm = by_type.get("cHRM", [])

    iccp_len = iccp[0].length if iccp else None
    location = {
        "container": "png",
        "chunk": "iCCP" if iccp else (srgb[0].type if srgb else "chunks"),
        "offset": (iccp[0].offset if iccp else (srgb[0].offset if srgb else 0)),
    }

    markers = {
        "iccp": bool(iccp),
        "iccp_length": iccp_len,
        "srgb": bool(srgb),
        "gama": bool(gama),
        "chrm": bool(chrm),
    }

    parts = [
        f"iCCP present (len={iccp_len})" if iccp else "iCCP absent",
        "sRGB present" if srgb else "sRGB absent",
        "gAMA present" if gama else "gAMA absent",
        "cHRM present" if chrm else "cHRM absent",
    ]
    findings.append(
        _finding(
            "color_markers",
            message="; ".join(parts),
            location=location,
            facts=dict(markers),
        )
    )

    if iccp and srgb:
        clause = get_spec("PNG3-ICCP-SRGB")
        phrase = "should not" if "should not" in clause.quote else "shall not"
        findings.append(
            _finding(
                "iccp_srgb_conflict",
                message=(
                    "PNG carries both an iCCP chunk and an sRGB chunk; PNG-3 says the sRGB "
                    "chunk 'should not' be present when iCCP is (warning, not error)"
                ),
                location={"container": "png", "chunk": "sRGB", "offset": srgb[0].offset},
                facts={"quote_says": phrase, "iccp_length": iccp_len},
            )
        )

    return markers


# ─────────────────────────────────────────────────────────────────────────────
# 5. 位深（不解码能读到才报，否则 unknown）
# ─────────────────────────────────────────────────────────────────────────────

def _report_bit_depth(container: Container, findings: list[dict[str, Any]]) -> None:
    info = container.image_info
    location = {"container": container.kind, "chunk": _depth_carrier(container.kind), "offset": 0}

    if container.kind == "jpeg" and info is not None and info.precision is not None:
        findings.append(
            _finding(
                "color_bit_depth",
                message=f"JPEG SOF precision (bit depth) = {info.precision}",
                location=location,
                facts={"format": "jpeg", "bit_depth": info.precision},
            )
        )
        return

    if container.kind == "png" and info is not None and info.bit_depth is not None:
        findings.append(
            _finding(
                "color_bit_depth",
                message=f"PNG IHDR bit depth = {info.bit_depth}",
                location=location,
                facts={"format": "png", "bit_depth": info.bit_depth},
            )
        )
        return

    findings.append(
        _finding(
            "color_bit_depth_unknown",
            message=(
                f"bit depth of {container.kind} is not readable from a container header field "
                "without unpacking the bitstream (not done in this release)"
            ),
            location=location,
            facts={"format": container.kind},
        )
    )


def _depth_carrier(kind: str) -> str:
    return {"jpeg": "SOF", "png": "IHDR", "webp": "VP8X", "gif": "LSD", "tiff": "IFD0"}.get(kind, kind)


# ─────────────────────────────────────────────────────────────────────────────
# 6. CMYK JPEG（四分量）
# ─────────────────────────────────────────────────────────────────────────────

def _check_cmyk(container: Container, findings: list[dict[str, Any]]) -> None:
    """四分量 JPEG → `warning: cmyk_jpeg`（收窄口径见模块 docstring / `plan/06` D19）。"""
    if container.kind != "jpeg":
        return
    info = container.image_info
    components = info.color_type if info is not None else None
    if components != 4:
        return

    app14 = next((s for s in container.segments if s.name == "APP14"), None)
    transform = None
    offset = 0
    if app14 is not None and app14.raw_data.startswith(b"Adobe") and len(app14.raw_data) >= 12:
        transform = app14.raw_data[11]
        offset = app14.offset

    findings.append(
        _finding(
            "cmyk_jpeg",
            message=(
                f"four-channel JPEG (components={components}, APP14 transform={transform}); "
                "CMYK/YCCK JPEGs do not render consistently across browsers"
            ),
            location={"container": "jpeg", "chunk": "APP14" if app14 else "SOF", "offset": offset},
            facts={"components": components, "app14_transform": transform},
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. 默认假设表
# ─────────────────────────────────────────────────────────────────────────────

def _report_defaults(
    container: Container, findings: list[dict[str, Any]], markers: dict[str, Any] | None
) -> None:
    """把 7 行默认假设表逐行带出（表体在顶层 `default_assumptions`）。"""
    facts: dict[str, Any] = {"rows": len(DEFAULT_ASSUMPTIONS)}
    if markers is not None:
        facts.update(
            {
                "iccp": markers["iccp"],
                "srgb": markers["srgb"],
                "gama": markers["gama"],
                "chrm": markers["chrm"],
            }
        )
    findings.append(
        _finding(
            "color_default_assumption",
            message=(
                f"{len(DEFAULT_ASSUMPTIONS)} default colour assumptions for {container.kind} "
                "are listed row-by-row in the report (each row carries its own source)"
            ),
            location={"container": container.kind, "chunk": None, "offset": 0},
            facts=facts,
        )
    )


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
    entry: dict[str, Any] = {
        "module": "color",
        "code": code,
        "severity": severity,
        "confidence": confidence,
        "risk": RISK_BY_SEVERITY[severity],
        "message": message,
        "facts": facts or {},
        "evidence": {"spec": clause.id, "quote": clause.quote, "location": location},
    }
    return entry