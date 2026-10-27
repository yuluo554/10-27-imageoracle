# -*- coding: utf-8 -*-
"""M1 生成器（container 族）：对应 M5 的验收样本（`plan/03-模块详设.md` §四）。

每类**两例**（PNG 顺序 / CRC / APNG / WebP / GIF / JPEG），外加 100 ms 三格式归一化样本。
突变点都落在"工具**读得到**的字段"上（chunk 顺序、CRC、声明长度、序号、单位换算），
不依赖任何像素解码。

CLI: `py -3.12 fixtures/gen_container.py [--check]`（manifest 由 `gen_all.py` 汇写）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))
sys.path.insert(0, str(ROOT / "src"))

from build import (  # noqa: E402
    actl,
    anmf_payload,
    anim_payload,
    anim_payload_swapped,
    build_app14,
    build_gif,
    build_jpeg_segments,
    build_png,
    fctl,
    fdat,
    gama,
    idat,
    ihdr,
    png_chunk,
    riff_chunk,
    riff_chunk_raw,
    riff_webp,
    sof_payload,
    sos_payload,
    text_payload,
    vp8x,
)
from generator import emit  # noqa: E402

BASE_W, BASE_H = 64, 48
DQT_ONE_TABLE = bytes([0x00]) + bytes([1] * 64)          # 一条全 1 量化表（确定性）
DHT_ONE_TABLE = bytes([0x00]) + bytes([0] * 16) + bytes([0x00])


def _ihdr_chunk() -> bytes:
    return png_chunk("IHDR", ihdr(BASE_W, BASE_H))


def build_all() -> dict[str, tuple[bytes, list[dict]]]:
    items: dict[str, tuple[bytes, list[dict]]] = {}

    # ── PNG chunk 顺序（2 例）───────────────────────────────────────────────
    # 1) gAMA 出现在 IDAT 之后（PNG-3 Table 7：gAMA 必须在 IDAT 前）
    items["m5_png_gama_after_idat.png"] = (
        build_png(width=BASE_W, height=BASE_H, after_idat=[png_chunk("gAMA", gama())]),
        [{"module": "M5", "code": "png_chunk_order", "expected": {"severity": "error", "chunk": "gAMA", "rule": "before IDAT"}}],
    )
    # 2) 两个 IDAT 不连续（中间夹 tEXt）
    items["m5_png_idat_nonconsecutive.png"] = (
        build_png(
            chunks=[
                _ihdr_chunk(),
                png_chunk("IDAT", idat()),
                png_chunk("tEXt", text_payload("Comment", "gap")),
                png_chunk("IDAT", idat()),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "png_idat_nonconsecutive",
                "expected": {"severity": "error", "quote": "Multiple IDAT chunks shall be consecutive"},
            }
        ],
    )

    # ── PNG CRC（2 例）──────────────────────────────────────────────────────
    # 3) CRC 值坏（gAMA 的 CRC 写 0）
    items["m5_png_bad_crc.png"] = (
        build_png(
            chunks=[
                _ihdr_chunk(),
                png_chunk("gAMA", gama(), crc=0),
                png_chunk("IDAT", idat()),
            ]
        ),
        [{"module": "M5", "code": "png_crc_mismatch", "expected": {"severity": "error", "chunk": "gAMA"}}],
    )
    # 4) CRC 缺失（截掉 IEND 的 4 字节 CRC）
    items["m5_png_missing_crc.png"] = (
        build_png(width=BASE_W, height=BASE_H, include_iend_crc=False),
        [
            {
                "module": "M5",
                "code": "png_crc_missing",
                "expected": {"severity": "error", "chunk": "IEND", "quote": "The CRC is always present"},
            }
        ],
    )

    # ── APNG（2 例）────────────────────────────────────────────────────────
    # 5) acTL.num_frames=3，实际只有 2 个 fcTL
    items["m5_apng_numframes.png"] = (
        build_png(
            chunks=[
                _ihdr_chunk(),
                png_chunk("acTL", actl(3, 0)),
                png_chunk("fcTL", fctl(0, BASE_W, BASE_H)),
                png_chunk("IDAT", idat()),
                png_chunk("fcTL", fctl(1, BASE_W, BASE_H)),
                png_chunk("fdAT", fdat(2)),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "apng_num_frames_mismatch",
                "expected": {"severity": "error", "declared": 3, "actual": 2},
            }
        ],
    )
    # 6) 序号跳号：0 → 3（缺 1、2）
    items["m5_apng_seq_gap.png"] = (
        build_png(
            chunks=[
                _ihdr_chunk(),
                png_chunk("acTL", actl(2, 0)),
                png_chunk("fcTL", fctl(0, BASE_W, BASE_H)),
                png_chunk("IDAT", idat()),
                png_chunk("fcTL", fctl(3, BASE_W, BASE_H)),
                png_chunk("fdAT", fdat(4)),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "apng_sequence_gap",
                "expected": {"severity": "error", "sequence": [0, 3], "quote": "no gaps or duplicates"},
            }
        ],
    )

    # ── WebP（2 例）────────────────────────────────────────────────────────
    # 7) ANMF 声明长度超出剩余字节
    items["m5_webp_anmf_truncated.webp"] = (
        riff_webp(
            [
                riff_chunk(b"VP8X", vp8x(BASE_W, BASE_H, animation=True)),
                riff_chunk(b"ANIM", anim_payload(0)),
                riff_chunk_raw(b"ANMF", 4096, anmf_payload(width=BASE_W, height=BASE_H, duration=100)),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "webp_anmf_truncated",
                "expected": {"severity": "error", "chunk": "ANMF", "declared": 4096},
            }
        ],
    )
    # 8) ANIM 字段错位：Loop Count 写成 u32 并放在 Background 之前 → 载荷 8 字节（应为 6）
    #    注：旧版 `anim_payload_swapped` 产出 6 字节、且 loop=0 时与正确形态**逐字节相同**，
    #    无法被任何判定器区分（M5 实测发现）。这里改成宽度错，判据是**长度**这一结构事实。
    items["m5_webp_anim_loop_swap.webp"] = (
        riff_webp(
            [
                riff_chunk(b"VP8X", vp8x(BASE_W, BASE_H, animation=True)),
                riff_chunk(b"ANIM", anim_payload_swapped(0)),
                riff_chunk(b"ANMF", anmf_payload(width=BASE_W, height=BASE_H, duration=100)),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "webp_anim_structure",
                "expected": {"severity": "error", "chunk": "ANIM", "fields": "Background/Loop swapped"},
            }
        ],
    )

    # ── GIF（2 例）─────────────────────────────────────────────────────────
    # 9) disposal=4（GIF89a 原文 "To be defined"）
    items["m5_gif_dispose4.gif"] = (
        build_gif(frames=[(4, 10)]),
        [
            {
                "module": "M5",
                "code": "gif_disposal_undefined",
                "expected": {"severity": "warning", "disposal": 4, "quote": "To be defined"},
            }
        ],
    )
    # 10) 100 ms 按 ms 误写：delay 写成 100（正确应为 10）→ 10× 量级错
    items["m5_gif_delay_ms.gif"] = (
        build_gif(frames=[(0, 100)]),
        [
            {
                "module": "M5",
                "code": "unit_mismatch",
                "expected": {"severity": "warning", "raw": 100, "raw_unit": "1/100s", "ms": 1000, "expected_ms": 100, "factor": 10},
            }
        ],
    )

    # ── 跨格式帧时长归一化：同一 100 ms（3 例）──────────────────────────────
    items["m5_frames_100ms.gif"] = (
        build_gif(frames=[(0, 10)]),
        [{"module": "M5", "code": "frame_duration_normalized", "expected": {"ms": 100, "raw": 10, "raw_unit": "1/100s"}}],
    )
    items["m5_frames_100ms.apng"] = (
        build_png(
            chunks=[
                _ihdr_chunk(),
                png_chunk("acTL", actl(2, 0)),
                png_chunk("fcTL", fctl(0, BASE_W, BASE_H, delay_num=10, delay_den=100)),
                png_chunk("IDAT", idat()),
                png_chunk("fcTL", fctl(1, BASE_W, BASE_H, delay_num=10, delay_den=100)),
                png_chunk("fdAT", fdat(2)),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "frame_duration_normalized",
                "expected": {"ms": 100, "delay_num": 10, "delay_den": 100, "raw_unit": "num/den"},
            }
        ],
    )
    items["m5_frames_100ms.webp"] = (
        riff_webp(
            [
                riff_chunk(b"VP8X", vp8x(BASE_W, BASE_H, animation=True)),
                riff_chunk(b"ANIM", anim_payload(0)),
                riff_chunk(b"ANMF", anmf_payload(width=BASE_W, height=BASE_H, duration=100)),
            ]
        ),
        [{"module": "M5", "code": "frame_duration_normalized", "expected": {"ms": 100, "raw": 100, "raw_unit": "ms"}}],
    )

    # ── JPEG 段顺序（2 例）──────────────────────────────────────────────────
    # 14) progressive：SOS 出现在 SOF2 **之前**（段序违规）
    items["m5_jpeg_progressive_mixed.jpg"] = (
        build_jpeg_segments(
            [
                (0xDB, DQT_ONE_TABLE),
                (0xC4, DHT_ONE_TABLE),
                (0xDA, sos_payload(3)),
                (0xC2, sof_payload(BASE_W, BASE_H, 3)),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "jpeg_segment_order",
                "expected": {"severity": "error", "before": "SOS", "after": "SOF2"},
            }
        ],
    )
    # 15) APP14 出现在 SOS **之后**
    items["m5_jpeg_app14_pos.jpg"] = (
        build_jpeg_segments(
            [
                (0xDB, DQT_ONE_TABLE),
                (0xC0, sof_payload(BASE_W, BASE_H, 3)),
                (0xC4, DHT_ONE_TABLE),
                (0xDA, sos_payload(3)),
                (0xEE, build_app14(0)),
            ]
        ),
        [
            {
                "module": "M5",
                "code": "jpeg_app14_position",
                "expected": {"severity": "error", "segment": "APP14", "after": "SOS"},
            }
        ],
    )

    return items


def _extra_self_check(items: dict[str, tuple[bytes, list[dict]]]) -> None:
    for name in ("m5_frames_100ms.gif", "m5_frames_100ms.apng", "m5_frames_100ms.webp"):
        assert name in items, f"缺 100 ms 归一化样本 {name}"
    assert len(items) >= 15, f"M5 样本数 {len(items)} 少于预期（每类两例）"
    # WebP 错位样本必须与好样本**字节不同**，否则判定器无法区分（M5 实测过的坑）
    assert items["m5_webp_anim_loop_swap.webp"][0] != items["m5_frames_100ms.webp"][0], (
        "ANIM 错位样本与 100 ms 好样本逐字节相同：不可判"
    )


def main(argv: list[str] | None = None) -> int:
    return emit(
        "container 族（M5 验收样本）",
        build_all,
        generators=["fixtures/gen_container.py"],
        extra=_extra_self_check,
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
