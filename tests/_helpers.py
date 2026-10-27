# -*- coding: utf-8 -*-
"""测试用的 CLI 调用辅助。

两件事：
1. 子进程环境统一（`PYTHONPATH` 指到 `src/`、UTF-8 强制、不继承用户环境里的怪东西）
2. **显式 `encoding="utf-8"`** —— Windows 默认代码页会让中文输出解码失败
   （实测：`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc9`）
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def cli_env() -> dict[str, str]:
    return {
        "PYTHONPATH": str(SRC),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "SYSTEMROOT": "C:\\Windows",
        "PATH": "",
        "TEMP": ".",
        "TMP": ".",
    }


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """跑 `python -m imageoracle <args>`（不装包也能跑）。"""
    argv = [sys.executable, "-m", "imageoracle", *args]
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(ROOT),
        shell=False,
    )


def run_script(rel: str, *args: str) -> subprocess.CompletedProcess[str]:
    """跑仓库内的脚本（生成器等）。"""
    argv = [sys.executable, str(ROOT / rel), *args]
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(ROOT),
        shell=False,
    )
