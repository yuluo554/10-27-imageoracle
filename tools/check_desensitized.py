#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脱敏门：入库文本里不得出现本机痕迹。

四条规则：
  R1 absolute-session-path  盘符绝对路径（C:\\Users\\... / D:/ProgramData/...）
  R2 msys-user-path         /c/Users/<name>/ 这类 MSYS 路径
  R3 local-username         本机用户名（默认 ASUS，可由环境变量 IMAGEORACLE_USERNAME 覆盖）
  R4 loopback-proxy         回环/私网代理端点（127.0.0.1:port、localhost:port、10./192.168./172.16-31.）

口径（每条都对应一次实测假红）：
  · 占位符必须放行：`C:\\Users\\<user>\\…`、`<repo>`、`<local-proxy>` 是脱敏后的**正确**写法。
  · 公开镜像/文档 URL 不是私有端点：只认回环与私网段，不认公网域名。
  · 门要豁免自己（它必须写出被判据禁止的字面量）。
  · 扫描面 = 仓库内容（.gitignore 声明的本地产物目录必须收编到 SKIP_DIRS）。
  · 按 `文件:行: [规则] 原文` 点名。

CLI:  py -3.12 tools/check_desensitized.py [--root <dir>]
退出码：0 无命中 / 1 有命中 / 2 用法错误。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_HIT = 1
EXIT_USAGE = 2

# 本门自身必须写出规则字面量，整份豁免（SELF 是"文件集合"，不是单个文件名）
SELF = {"tools/check_desensitized.py", "tools/verify_gates.py"}
SELF_SIZE = len(SELF)

SKIP_DIRS = {
    ".git", "node_modules", "build", "dist", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".venv", "venv", "env", ".tox", "out", "fixtures/out",
    ".mimosa", ".idea", ".vscode", "htmlcov", ".hypothesis", "site-packages",
}
SKIP_SUFFIXES = (".egg-info", ".dist-info")

# 只扫文本类文件（二进制图像不入扫描面，它们由 .gitignore 排除）
TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".toml", ".cfg", ".ini", ".yml", ".yaml", ".json",
    ".js", ".mjs", ".cjs", ".ts", ".sh", ".ps1", ".html", ".css", ".rst",
}

USERNAME = os.environ.get("IMAGEORACLE_USERNAME", "ASUS")

RULES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "absolute-session-path",
        # 盘符后跟用户目录 / ProgramData；占位符 <…> 放行
        re.compile(r"(?<![<\w])[A-Za-z]:[\\/](?:Users|ProgramData|Documents and Settings)[\\/](?!<)[^\s`'\"|)]*"),
        "把本机绝对路径换成相对路径或 <repo>/<user> 占位符",
    ),
    (
        "msys-user-path",
        re.compile(r"/[a-z]/Users/(?!<)[^\s`'\"|)]+"),
        "把 MSYS 路径换成相对路径",
    ),
    (
        "local-username",
        re.compile(rf"(?<![\w<-]){re.escape(USERNAME)}(?![\w>-])"),
        "本机用户名不应出现在入库文本里（改用 <user>）",
    ),
    (
        "loopback-proxy",
        re.compile(
            r"\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0)(?::\d{2,5})?\b"
            r"|\b(?:10\.\d{1,3}|192\.168\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"
        ),
        "本机代理/回环端点不应出现在入库文本里（改用 <local-proxy>）",
    ),
]


def iter_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if any(part.endswith(SKIP_SUFFIXES) for part in rel_parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        found.append(path)
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="脱敏门")
    parser.add_argument("--root", default=None, help="仓库根目录（默认取本文件的上一级）")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print(f"用法错误：--root 不是目录: {root}", file=sys.stderr)
        return EXIT_USAGE

    files = iter_files(root)
    hits: list[str] = []
    skipped_self = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel in SELF:
            skipped_self += 1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            hits.append(f"{rel}:0: [read-error] {exc}")
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern, _hint in RULES:
                m = pattern.search(line)
                if m:
                    hits.append(f"{rel}:{lineno}: [{name}] {m.group(0)}")

    print("脱敏门 · 扫描面 = 仓库文本内容")
    print("=" * 64)
    print(
        f"扫了 {len(files)} 份文本文件，豁免自身 {skipped_self} 份（SELF={SELF_SIZE}）"
    )
    for hit in hits:
        print(f"FAIL  {hit}")
    print("=" * 64)
    print(f"结论: {'全绿' if not hits else f'{len(hits)} 处命中'}")
    return EXIT_OK if not hits else EXIT_HIT


if __name__ == "__main__":
    sys.exit(main())
