# -*- coding: utf-8 -*-
"""M1 生成器（ICC/color 族）：对应 M4 的验收样本（`plan/03-模块详设.md` §三）。

**范围限定（`plan/04` §二 / R5）**：PNG `iCCP` 首期**不解压** → PNG 侧一律
`unknown: compressed_profile_not_inspected`。因此三类损坏各造**两份**：
  · `.png`（承载在 `iCCP`）—— 证明"不解压 → unknown"
  · `.jpg`（承载在 APP2）—— 证明"不解压路径上三段错误码确实能被触发"
两条都造，才不是"把漏实现说成范围限定"。

CLI: `py -3.12 fixtures/gen_icc.py [--check]`（manifest 由 `gen_all.py` 汇写）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))
sys.path.insert(0, str(ROOT / "src"))

from build import (  # noqa: E402
    build_app14,
    build_jpeg,
    build_png,
    chrm_bt709,
    gama,
    icc_app2_payload,
    icc_profile,
    iccp_chunk,
    png_chunk,
    tiff_with_icc,
)
from generator import emit  # noqa: E402

#: lr0 案原始报的是 `chunk iCCP at offset 0x00025, length 5147`；此处按该**声明长度**造 profile
LR0_DECLARED_LENGTH = 5147


def _icc_jpeg(profile: bytes, **kwargs) -> bytes:
    """把 ICC 分片挂在 JPEG APP2 上（`ICC_PROFILE\\0` + seq/total + 分片）。"""
    return build_jpeg(extra_segments=[(0xE2, icc_app2_payload(profile))], **kwargs)


def _icc_jpeg_multi(profile: bytes, *, total: int, seqs: tuple[int, ...]) -> bytes:
    """多段 APP2：按给定的段号列表切分 profile（用于连续性正/反两支）。

    `seqs` 决定每段声明的段号；切分点由段数均分，末段吃掉余数。声明总数统一记为 `total`。
    """
    count = len(seqs)
    size = max(1, len(profile) // count)
    pieces = [profile[i * size:(i + 1) * size] for i in range(count - 1)]
    pieces.append(profile[(count - 1) * size:])
    return build_jpeg(
        extra_segments=[
            (0xE2, icc_app2_payload(piece, seq=seq, total=total))
            for seq, piece in zip(seqs, pieces)
        ]
    )


def build_all() -> dict[str, tuple[bytes, list[dict]]]:
    items: dict[str, tuple[bytes, list[dict]]] = {}

    ok_profile = icc_profile(declared_length=256)                    # size/签名/class 全合法
    truncated = icc_profile(declared_length=256)[:100]               # 解压/拼接后 < 128
    size_bad = icc_profile(size_override=2000, declared_length=1500)  # 头内 size ≠ 实际长度
    acsp_bad = icc_profile(signature=b"acsq", declared_length=256)    # @36 != "acsp"
    lr0_profile = icc_profile(declared_length=LR0_DECLARED_LENGTH)    # 正常 RGB 显示 profile

    # 1) 正常基线：PNG（不解压 → unknown）与 JPEG（可读 → info）两条
    items["m4_icc_ok.png"] = (
        build_png(before_idat=[iccp_chunk(ok_profile)]),
        [
            {"module": "M4", "code": "icc_present", "expected": {"carrier": "iCCP", "severity": "info"}},
            {
                "module": "M4",
                "code": "compressed_profile_not_inspected",
                "expected": {"carrier": "iCCP", "severity": "unknown"},
            },
        ],
    )
    items["m4_icc_ok.jpg"] = (
        _icc_jpeg(ok_profile),
        [{"module": "M4", "code": "icc_present", "expected": {"carrier": "APP2", "severity": "info"}}],
    )

    # 2) 截断（<128B）
    items["m4_icc_truncated.png"] = (
        build_png(before_idat=[iccp_chunk(truncated)]),
        [
            {
                "module": "M4",
                "code": "compressed_profile_not_inspected",
                "expected": {"carrier": "iCCP", "severity": "unknown"},
            }
        ],
    )
    items["m4_icc_truncated.jpg"] = (
        _icc_jpeg(truncated),
        [{"module": "M4", "code": "icc_header_truncated", "expected": {"severity": "error", "length": 100}}],
    )

    # 3) ProfileSize 与载体长度不符
    items["m4_icc_size_bad.png"] = (
        build_png(before_idat=[iccp_chunk(size_bad)]),
        [
            {
                "module": "M4",
                "code": "compressed_profile_not_inspected",
                "expected": {"carrier": "iCCP", "severity": "unknown"},
            }
        ],
    )
    items["m4_icc_size_bad.jpg"] = (
        _icc_jpeg(size_bad),
        [
            {
                "module": "M4",
                "code": "icc_size_mismatch",
                "expected": {"severity": "error", "declared": 2000, "actual": 1500},
            }
        ],
    )

    # 4) `acsp` 签名坏
    items["m4_icc_acsp_bad.png"] = (
        build_png(before_idat=[iccp_chunk(acsp_bad)]),
        [
            {
                "module": "M4",
                "code": "compressed_profile_not_inspected",
                "expected": {"carrier": "iCCP", "severity": "unknown"},
            }
        ],
    )
    items["m4_icc_acsp_bad.jpg"] = (
        _icc_jpeg(acsp_bad),
        [{"module": "M4", "code": "icc_bad_signature", "expected": {"severity": "error", "signature": "acsq"}}],
    )

    # 5) lr0 形态：iCCP 在 + 无 sRGB + 有 gAMA/cHRM → 复现"各软件默认不同"的现场
    items["m4_lr0_form.png"] = (
        build_png(
            before_idat=[
                iccp_chunk(lr0_profile),
                png_chunk("gAMA", gama()),
                png_chunk("cHRM", chrm_bt709()),
            ]
        ),
        [
            {"module": "M4", "code": "icc_present", "expected": {"carrier": "iCCP", "severity": "info"}},
            {
                "module": "M4",
                "code": "compressed_profile_not_inspected",
                "expected": {"carrier": "iCCP", "severity": "unknown"},
            },
            {
                "module": "M4",
                "code": "color_default_assumption",
                "expected": {"severity": "info", "rows": 7, "gama": True, "chrm": True, "srgb": False},
            },
        ],
    )

    # 6) `iCCP` 与 `sRGB` 并存（PNG-3 原文是 should not → warning，不升格为 error）
    items["m4_iccp_srgb_conflict.png"] = (
        build_png(before_idat=[iccp_chunk(ok_profile), png_chunk("sRGB", bytes([0]))]),
        [
            {
                "module": "M4",
                "code": "iccp_srgb_conflict",
                "expected": {"severity": "warning", "quote_says": "should not"},
            }
        ],
    )

    # 7) CMYK JPEG：APP14 transform=0 + SOF0 四通道
    items["m4_cmyk_app14.jpg"] = (
        build_jpeg(components=4, app14=build_app14(0)),
        [{"module": "M4", "code": "cmyk_jpeg", "expected": {"severity": "warning", "app14_transform": 0, "components": 4}}],
    )

    # 8) 多段 APP2 拼接：2 段、段号 1/2 连续 → 拼接成功 + 头合法（不报 gap）
    multi_profile = icc_profile(declared_length=300)
    items["m4_icc_multi_segment.jpg"] = (
        _icc_jpeg_multi(multi_profile, total=2, seqs=(1, 2)),
        [
            {"module": "M4", "code": "icc_present", "expected": {"carrier": "APP2", "segments": 2, "profile_length": 300}},
        ],
    )

    # 9) 多段 APP2 段号缺口：声明 3 段却缺第 2 段（seq=1,3）→ `icc_segment_gap`(error)
    items["m4_icc_segment_gap.jpg"] = (
        _icc_jpeg_multi(multi_profile, total=3, seqs=(1, 3)),
        [
            {"module": "M4", "code": "icc_segment_gap", "expected": {"severity": "error", "carrier": "APP2"}},
        ],
    )

    # 10) TIFF tag 34675 载体：ICC 的四种载体之一（`data/README` §1.11）
    items["m4_icc_tiff34675.tif"] = (
        tiff_with_icc(icc_profile(declared_length=256)),
        [
            {"module": "M4", "code": "icc_present", "expected": {"carrier": "tag34675", "severity": "info"}},
        ],
    )

    return items


def _extra_self_check(items: dict[str, tuple[bytes, list[dict]]]) -> None:
    """三类损坏必须**双承载**齐（PNG 走 unknown / JPEG 走 error）——R5 的判据面。"""
    for case in ("truncated", "size_bad", "acsp_bad"):
        for ext in ("png", "jpg"):
            name = f"m4_icc_{case}.{ext}"
            assert name in items, f"缺 {name}（三类损坏要双承载，才能同时证明 unknown 与 error）"
    # 多段拼接的正/反两支都要在：否则 `icc_segment_gap` 无样本可依
    for name in ("m4_icc_multi_segment.jpg", "m4_icc_segment_gap.jpg"):
        assert name in items, f"缺 {name}（多段 APP2 拼接的连续性判据要有样本证明）"
    assert "m4_icc_tiff34675.tif" in items, "缺 TIFF tag 34675 载体样本（四种载体之一）"


def main(argv: list[str] | None = None) -> int:
    return emit(
        "ICC/color 族（M4 验收样本）",
        build_all,
        generators=["fixtures/gen_icc.py"],
        extra=_extra_self_check,
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
