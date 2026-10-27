# -*- coding: utf-8 -*-
"""判决层：`container`（题目 M4）—— **契约占位，M5 实现**。

契约（详见 `plan/03-模块详设.md` §四）：

| # | 检查 | 依据 |
|---|---|---|
| 1 | PNG chunk 顺序（IHDR 首 / IEND 末 / PLTE / tRNS / 色彩 chunk / acTL,eXIf,pHYs,sPLT / fcTL / fdAT） | `PNG3-T7` |
| 2 | CRC = `chunk type + data`（**不含 length**），每个 chunk 都要有 | `PNG3-CRC` / `PNG3-CRC-PRESENT` |
| 3 | IDAT 连续 | `PNG3-T7` |
| 4 | APNG `num_frames == fcTL count`、首序号 0、无缺口/重复、`delay_den==0→100`、`acTL` 在首 IDAT 前 | `APNG-SEQ` / `APNG-DELAY` |
| 5 | WebP `ANIM`（BGRA、Loop u16=0 无限）、`ANMF` duration 24-bit ms、内部边界 | `WEBP-ANIM` / `WEBP-ANMF` |
| 6 | GIF disposal 4–7、delay 1/100 s、GCE 位置与帧序 | `GIF89A-GCE` |
| 7 | JPEG 段顺序、多 SOS 与 progressive 一致、APP14 位置 | ITU T.81 结构 |
| 8 | 跨格式帧时长归一化到 ms + `unit_mismatch`（10× / 1×） | `data/README` §8.3 |

CRC 已知向量单测：`crc32(b"IEND") == 0xAE426082`（`tests/test_m5_crc.py`）。

本文件存在但未接线：`modules.IMPLEMENTED` 里没有它。
"""

from __future__ import annotations

from typing import Any

from ..model import Container

MILESTONE = "M5"


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "container 尚未实现（计划于 M5）：契约见 plan/03-模块详设.md §四"
    )
