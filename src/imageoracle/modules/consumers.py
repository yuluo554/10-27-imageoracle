# -*- coding: utf-8 -*-
"""判决层：`consumers`（题目 M5）—— **契约占位，M6 实现**。

契约（详见 `plan/03-模块详设.md` §五）：

行 = Chrome / Safari / Firefox / macOS Preview / Windows 照片 / ImageMagick / libvips / sharp / exiftran；
列 = 会应用方向? / 会应用 ICC? / 会丢哪些 chunk? / 双重旋转风险 / 动画帧时长解读 / 依据。

硬验收：
- 每行 `evidence.kind ∈ {spec, tool-doc, hn-quote}`，`tool-doc` 必须 URL + 原文片段
- `confidence ∈ {certain, single-source, gray}`
- **无 evidence 的行让 `report.selftest_evidence_complete` 失败**
- ≥4 条加工命令 diff：`oxipng --strip safe` / `oxipng --strip all` / `sharp.rotate()` / `exiftran`
- 矩阵内容来自 `data/README.md` 台账，不来自运行时猜测；报告头写工具版本与星数快照日期

本文件存在但未接线：`modules.IMPLEMENTED` 里没有它。
"""

from __future__ import annotations

from typing import Any

from ..model import Container

MILESTONE = "M6"

#: 消费者矩阵的行（固定顺序，报告里按此渲染）
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

#: 至少要给的"加工命令 diff"
PROCESS_COMMANDS: tuple[str, ...] = (
    "oxipng --strip safe",
    "oxipng --strip all",
    "sharp.rotate()",
    "exiftran",
)


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "consumers 尚未实现（计划于 M6）：契约见 plan/03-模块详设.md §五"
    )
