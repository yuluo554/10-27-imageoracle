# -*- coding: utf-8 -*-
"""`python -m imageoracle` 入口。

`pyproject.toml` 的 `[project.scripts]` 指向 `imageoracle.cli:main`；
本文件只为"不安装也能跑"提供同一入口（README 首条命令用的就是它）。
"""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
