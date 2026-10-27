# -*- coding: utf-8 -*-
"""M1 生成器（double-rotate 族）：对应 M3 的验收样本（`plan/03-模块详设.md` §二）。

三个判决条件各一份**真字节**样本（不使用任何外部 CLI）：
  1. `m3_ifd1_unsynced.jpg`      —— 主图 IFD0=6、缩略图 IFD1 未同步=1（`jpegtran -copy all -rotate 90` 形态）
  2. `m3_xmp_residual.jpg`       —— EXIF 已归 1、XMP `tiff:Orientation=6` 残留（sharp #4585 形态）
  3. `m3_bigedge_mismatch.jpg`   —— 声明 6 但容器宽>高（大边在水平）→ 只出 `suspicion`

CLI: `py -3.12 fixtures/gen_double_rotate.py [--check]`（manifest 由 `gen_all.py` 汇写）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))
sys.path.insert(0, str(ROOT / "src"))

from build import build_jpeg, tiff_with_orientation, xmp_packet  # noqa: E402
from generator import emit  # noqa: E402

BASE_W, BASE_H = 64, 48


def build_all() -> dict[str, tuple[bytes, list[dict]]]:
    items: dict[str, tuple[bytes, list[dict]]] = {}

    # 1) 缩略图未同步：主图 6 / IFD1 1（jpegtran `-copy all` 时 "Thumbnails are copied as-is"）
    items["m3_ifd1_unsynced.jpg"] = (
        build_jpeg(
            width=BASE_W,
            height=BASE_H,
            exif=tiff_with_orientation(6, width=BASE_W, height=BASE_H, ifd1_orientation=1),
        ),
        [
            {
                "module": "M3",
                "code": "double_rotate_ifd1_unsynced",
                "expected": {
                    "condition": 1,
                    "confidence": "certain",
                    "exif.ifd0.orientation": 6,
                    "exif.ifd1.orientation": 1,
                },
            }
        ],
    )

    # 2) XMP 残留：EXIF 已归 1、XMP 仍写 6 → 下游读 XMP 的再转一次（sharp #4585）
    items["m3_xmp_residual.jpg"] = (
        build_jpeg(
            width=BASE_W,
            height=BASE_H,
            exif=tiff_with_orientation(1, width=BASE_W, height=BASE_H),
            xmp=xmp_packet(6),
        ),
        [
            {
                "module": "M3",
                "code": "double_rotate_xmp_conflict",
                "expected": {
                    "condition": 2,
                    "confidence": "certain",
                    "exif.ifd0.orientation": 1,
                    "xmp.tiff:Orientation": 6,
                },
            }
        ],
    )

    # 3) 大边启发式：声明 6（应当转 90°）但容器宽>高（大边在水平）→ 只出 suspicion
    #    尺寸特意取 80×40（区别于 m2 基线 64×48），保证样本字节唯一、不与 M2 好样本重名同哈希。
    items["m3_bigedge_mismatch.jpg"] = (
        build_jpeg(width=80, height=40, exif=tiff_with_orientation(6, width=80, height=40)),
        [
            {
                "module": "M3",
                "code": "double_rotate_bigedge_mismatch",
                "expected": {
                    "condition": 3,
                    "confidence": "gray-heuristic",
                    "severity": "suspicion",
                    "exif.ifd0.orientation": 6,
                    "stored": [80, 40],
                },
            }
        ],
    )

    return items


def _extra_self_check(items: dict[str, tuple[bytes, list[dict]]]) -> None:
    for name in ("m3_ifd1_unsynced.jpg", "m3_xmp_residual.jpg", "m3_bigedge_mismatch.jpg"):
        assert name in items, f"缺 M3 样本 {name}"


def main(argv: list[str] | None = None) -> int:
    return emit(
        "double-rotate 族（M3 验收样本）",
        build_all,
        generators=["fixtures/gen_double_rotate.py"],
        extra=_extra_self_check,
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
