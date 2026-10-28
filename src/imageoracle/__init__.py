# -*- coding: utf-8 -*-
"""ImageOracle：图像呈现预言机。

**只读字节**：不解码像素、不做颜色变换、不联网、不写回源文件。
数值口径（变换矩阵 / ICC 校验项 / 帧单位 / gray 条件 / 退出码）只在 `data/README.md` §8 定义一次。
"""

from __future__ import annotations

__all__ = ["__version__", "TOOL_NAME", "SCHEMA_VERSION"]

# 版本号唯一定义处之一；另一处是 pyproject.toml 的 [project].version。
# tools + tests 断言两处一致（plan/06 D12）。
__version__ = "0.5.2"

TOOL_NAME = "imageoracle"

#: 报告 schema 版本。判决口径变动（旧报告失效）时才 +1，与产品版本是两条时间线。
SCHEMA_VERSION = "1"
