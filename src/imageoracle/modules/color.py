# -*- coding: utf-8 -*-
"""判决层：`color`（题目 M3）—— **契约占位，M4 实现**。

契约（详见 `plan/03-模块详设.md` §三）：

1. ICC 存在性（JPEG APP2 多段拼接 + 段号 `i/n` 连续；PNG `iCCP`；WebP `ICCP`；TIFF tag 34675）
2. 128B 头逐字段（`ProfileFileSignature@36 == "acsp"`、`ProfileSize` vs 载体长度、
   `ProfileClass@12`、`ColorSpaceData@16`、`ProfileConnectionSpace@20`、`RenderingIntent@64`）
3. PNG `iCCP` ↔ `sRGB` 并存 → `warning: iccp_srgb_conflict`（PNG-3 原文是 should not）
4. `gAMA` / `cHRM` 有无组合
5. CMYK JPEG（APP14 `transform`）→ `warning: cmyk_jpeg`
6. 位深（不解码能读到才报，否则 `unknown`）
7. **默认假设表 7 行，逐行带 `source`**

纪律：不做颜色变换、不引 lcms；风险只出 `risk: high/medium/low/unknown` + 依据，**绝不出色值**；
PNG `iCCP` 压缩流首期**不解压** → `unknown: compressed_profile_not_inspected`（`plan/00` D9）。

本文件存在但未接线：`modules.IMPLEMENTED` 里没有它。
"""

from __future__ import annotations

from typing import Any

from ..model import Container

MILESTONE = "M4"


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "color 尚未实现（计划于 M4）：契约见 plan/03-模块详设.md §三"
    )
