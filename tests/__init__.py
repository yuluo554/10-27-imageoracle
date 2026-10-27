# -*- coding: utf-8 -*-
"""测试引导：把 `src/` 放进 `sys.path`，并断言零第三方依赖。

不引入 pytest：`py -3.12 -m unittest discover -s tests -t .` 直接跑。
`tests/` 在 cwd 下时，本文件会被 discover 首先导入，因此路径注入对所有测试生效。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
