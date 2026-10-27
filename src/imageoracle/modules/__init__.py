# -*- coding: utf-8 -*-
"""判决层：模块注册表。

CLI 只挂 `IMPLEMENTED` 里的模块；`PLANNED` 是"M 里程碑尚未开工"的显式登记
（与布局门的 PENDING_TOOLS 同一种三态语义：在位 / 待里程碑 / 缺失，不允许"看着像有"）。

**本层禁止 import `report/`**（判定与呈现分家，AST 守门断言）。
"""

from __future__ import annotations

from . import color, consumers, container, double_rotate, orientation

#: 已实现：name -> analyze(container) -> dict
IMPLEMENTED: dict[str, object] = {
    "orientation": orientation,
    "double-rotate": double_rotate,
    "color": color,
    "container": container,
    "consumers": consumers,
}

#: 未实现：name -> (里程碑, 契约位置)。CLI 不挂它们；测试断言它们确实会抛 NotImplementedError。
#: M6 之后**本表为空**（五个模块全部落地）——空表本身就是"没有占位了"的断言面，
#: 见 `tests/test_cli_contract.py::TestModuleRegistration::test_no_planned_modules_left`。
PLANNED: dict[str, tuple[str, str]] = {}

__all__ = [
    "IMPLEMENTED",
    "PLANNED",
    "color",
    "consumers",
    "container",
    "double_rotate",
    "orientation",
]
