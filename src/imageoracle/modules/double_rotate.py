# -*- coding: utf-8 -*-
"""判决层：`double-rotate`（题目 M2）—— **契约占位，M3 实现**。

契约（详见 `plan/03-模块详设.md` §二）：

判决条件（三条件取或，命中即报，报出命中了几条）

| # | 条件 | confidence |
|---|---|---|
| 1 | `IFD1.orientation != IFD0.orientation` | `certain` |
| 2 | XMP `tiff:Orientation` 与 EXIF tag 274 冲突（值不同；或一方存在且非 1 而另一方缺失） | `certain` |
| 3 | 声明方向与容器自带宽高的"大边位置"启发式不符 | `gray-heuristic`（只出 `suspicion`） |

输出：`{condition_hits, certain, heuristic, verdicts:[{consumer, trigger_chain, consequence, evidence}]}`。
`certain` 与 `heuristic` **必须分列**，不得混在同一得分里。

复用约定：本模块读 `modules.orientation.analyze()` 产出的 `sources`，**不重复实现 XMP 正则**
（`orientation.read_xmp_orientation` 是唯一实现）。

本文件存在但未接线：`modules.IMPLEMENTED` 里没有它，CLI 不会暴露 `double-rotate` 子命令。
"""

from __future__ import annotations

from typing import Any

from ..model import Container

MILESTONE = "M3"


def analyze(container: Container, **kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "double-rotate 尚未实现（计划于 M3）：契约见 " + "plan/03-模块详设.md §二"
    )
