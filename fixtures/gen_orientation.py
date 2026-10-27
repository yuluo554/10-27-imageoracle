# -*- coding: utf-8 -*-
"""M1 生成器（orientation 族）：对应 M2 的验收样本。

**不使用任何外部 CLI**：字节全部由 `fixtures/lib/build.py` 构造。
**无随机、无时间戳** → 同一输入必得同一字节（`--check` 会逐条核对）。

CLI:
  py -3.12 fixtures/gen_orientation.py            # 写本族产物到 fixtures/out/
  py -3.12 fixtures/gen_orientation.py --check    # 只核对本族（退出码 1 = 漂移）

manifest 由**聚合器** `fixtures/gen_all.py` 汇写（四族共用一份 `fixtures/manifest.json`）。
`--check` 两层断言（`plan/04` §二.3）：
  第一层 重新生成（内存）→ 与 fixtures/manifest.json 的 sha256 逐条比对
  第二层 fixtures/out/ 里若存在冻结产物 → 与其字节逐字节比对（不存在则显式 SKIP，不冒充通过）
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))
sys.path.insert(0, str(ROOT / "src"))

from build import (  # noqa: E402
    EXIF_PREFIX,
    build_jpeg,
    build_png,
    icc_profile,  # noqa: F401  (M4 生成器复用同一 build 面；此处保留导入以便同源)
    iccp_chunk,   # noqa: F401
    png_chunk,
    riff_chunk,
    tiff_with_orientation,
    tiff_with_wrong_type_orientation,
)
from generator import emit  # noqa: E402

#: 非正方形基线（否则 5/6/7/8 的宽高交换不可观测；`data/README` §7.3）
BASE_W, BASE_H = 64, 48


# ─────────────────────────────────────────────────────────────────────────────
# WebP（RIFF）最小构造：只造 VP8X + EXIF，够 M2 读 EXIF 用
# ─────────────────────────────────────────────────────────────────────────────

def _build_webp_exif(exif_bytes: bytes, *, with_prefix: bool, width: int = BASE_W, height: int = BASE_H) -> bytes:
    """VP8X（带 EXIF 标志）+ EXIF chunk。`with_prefix` 控制 EXIF 是否带 `Exif\\0\\0`（D10）。"""
    # VP8X: flags(1) reserved(3) canvasWidth-1(3) canvasHeight-1(3)
    flags = 0x08  # EXIF present
    vp8x = bytes([flags, 0, 0, 0]) + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    payload = EXIF_PREFIX + exif_bytes if with_prefix else exif_bytes
    body = riff_chunk(b"VP8X", vp8x) + riff_chunk(b"EXIF", payload)
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WEBP" + body


# ─────────────────────────────────────────────────────────────────────────────
# 样本表
# ─────────────────────────────────────────────────────────────────────────────

def build_all() -> dict[str, tuple[bytes, list[dict]]]:
    """返回 {相对路径: (bytes, triggers)}。**顺序固定**（dict 保序），保证 manifest 稳定。"""
    items: dict[str, tuple[bytes, list[dict]]] = {}

    # 1) 8 个 orientation 值（JPEG，非正方形）
    for n in range(1, 9):
        tiff = tiff_with_orientation(n, width=BASE_W, height=BASE_H)
        data = build_jpeg(width=BASE_W, height=BASE_H, exif=tiff)
        items[f"m2_orient{n}_portrait.jpg"] = (
            data,
            [
                {"module": "M2", "code": "orientation", "expected": {"exif.ifd0.orientation": n}},
            ],
        )

    # 2) 大端 TIFF：证明 274 按头字节序读，不固定小端（R1）
    for n in (6, 8):
        data = tiff_with_orientation(n, byte_order="MM", width=BASE_W, height=BASE_H)
        items[f"m2_orient{n}_be.tif"] = (
            data,
            [
                {"module": "M2", "code": "orientation", "expected": {"exif.ifd0.orientation": n}},
            ],
        )

    # 3) PNG eXIf（无 Exif\0\0 前缀——PNG 规范如此，D10 正向）
    tiff6 = tiff_with_orientation(6, width=BASE_W, height=BASE_H)
    items["m2_orient6_exif.png"] = (
        build_png(width=BASE_W, height=BASE_H, before_idat=[png_chunk("eXIf", tiff6)]),
        [
            {"module": "M2", "code": "orientation", "expected": {"exif.ifd0.orientation": 6}},
            {"module": "M2", "code": "orientation_missing_prefix_ok", "expected": {}},
        ],
    )

    # 3b) PNG eXIf 带前缀（非规范但确有编码器这么写；工具记录事实而不错判）
    items["m2_orient6_exif_prefixed.png"] = (
        build_png(width=BASE_W, height=BASE_H, before_idat=[png_chunk("eXIf", EXIF_PREFIX + tiff6)]),
        [
            {"module": "M2", "code": "orientation", "expected": {"exif.ifd0.orientation": 6}},
            {"module": "M2", "code": "note_exif_prefix", "expected": {}},
        ],
    )

    # 4) WebP EXIF：带前缀 / 不带前缀（D10 双向验证）
    items["m2_orient6_prefix.webp"] = (
        _build_webp_exif(tiff6, with_prefix=True),
        [{"module": "M2", "code": "orientation", "expected": {"exif.ifd0.orientation": 6}}],
    )
    items["m2_orient6_noprefix.webp"] = (
        _build_webp_exif(tiff6, with_prefix=False),
        [{"module": "M2", "code": "orientation", "expected": {"exif.ifd0.orientation": 6}}],
    )

    # 5) absent：与 "=1" 必须分列（R3）
    items["m2_absent.jpg"] = (
        build_jpeg(width=BASE_W, height=BASE_H),
        [
            {
                "module": "M2",
                "code": "orientation_absent",
                "expected": {"state": "absent", "distinct_from_value_1": True},
            }
        ],
    )

    # 6) 越界：0 与 9（int16u 合法但语义越界）
    for bad in (0, 9):
        data = build_jpeg(width=BASE_W, height=BASE_H, exif=tiff_with_orientation(bad))
        items[f"m2_orient{bad}_oor.jpg"] = (
            data,
            [{"module": "M2", "code": "orientation_out_of_range", "expected": {"value": bad}}],
        )

    # 7) 类型错：方向 tag 写成 LONG → orientation_not_int16u
    items["m2_orient6_wrongtype.jpg"] = (
        build_jpeg(width=BASE_W, height=BASE_H, exif=tiff_with_wrong_type_orientation(6)),
        [{"module": "M2", "code": "orientation_not_int16u", "expected": {"tiff_type": 4}}],
    )

    # 8) 镜像族：2/4/5/7 必须同时给 flip 与 rotate（M2 硬验收）
    for n in (2, 4, 5, 7):
        data = build_jpeg(width=BASE_W, height=BASE_H, exif=tiff_with_orientation(n))
        items[f"m2_orient{n}_mirror.jpg"] = (
            data,
            [
                {
                    "module": "M2",
                    "code": "orientation",
                    "expected": {"exif.ifd0.orientation": n, "mirror_family": True},
                }
            ],
        )

    return items


# ─────────────────────────────────────────────────────────────────────────────
# 自检 / CLI（外壳与 manifest 读写都走 fixtures/lib 的唯一实现）
# ─────────────────────────────────────────────────────────────────────────────

def _extra_self_check(items: dict[str, tuple[bytes, list[dict]]]) -> None:
    for n in (2, 4, 5, 7):
        assert f"m2_orient{n}_mirror.jpg" in items, f"缺镜像族样本 {n}"


def main(argv: list[str] | None = None) -> int:
    return emit(
        "orientation 族（M2 验收样本）",
        build_all,
        generators=["fixtures/gen_orientation.py"],
        extra=_extra_self_check,
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
