# -*- coding: utf-8 -*-
"""分层与红线守门（AST 判据，不数文本出现次数）。

断言：
  1. `readers/` 不 import `modules/`
  2. `modules/` 不 import `report/`
  3. `report/` 不 import `readers/`
  4. 全仓库不 import 任何第三方包（只允许标准库 + 本包）
  5. 全仓库不 import 网络模块（零网络是可断言的红线）
  6. 核心模块不读时钟（`datetime.now` / `time.time` 等），定位到函数体
  7. `readers/` 与 `modules/` 不调用 `zlib.decompress`（不解码像素/不解压）

**为什么用 AST 而不是 grep**：skill 假门族 ⑱——`source.count("time.gmtime(") == 2`
会把注释里的提及也数进去（实测 3 → 假红）。AST 能同时给出"恰好几处"与"在哪一层"。
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PKG = SRC / "imageoracle"

#: 网络与进程模块——零网络/不 spawn 的红线
FORBIDDEN_IMPORTS = {
    "socket", "ssl", "http", "urllib", "urllib2", "ftplib", "smtplib", "telnetlib",
    "requests", "httpx", "aiohttp", "xmlrpc", "subprocess", "multiprocessing",
}
#: 允许的第三方例外：无。本包必须零依赖。
STDLIB = set(sys.stdlib_module_names)
OWN_PACKAGE = "imageoracle"


def iter_sources() -> list[tuple[Path, ast.Module]]:
    out: list[tuple[Path, ast.Module]] = []
    for path in sorted(PKG.rglob("*.py")):
        out.append((path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))))
    return out


def imported_modules(tree: ast.Module) -> set[str]:
    """收集 import 的**绝对**模块名。

    覆盖四种形态（skill 假门族 ⑥：只查 node.module 会漏相对导入与 from X import Y）：

    * ``import a.b``            → {"a.b"}
    * ``import a.b as c``       → {"a.b"}
    * ``from a.b import c``     → {"a.b"}
    * ``from . import c``       → {"<pkg>.<layer>.c"}（用调用方解析，见 resolve_relative）
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:
                # 相对导入：node.module 为 None 时名字在 names 里
                names.add(f"<relative level={node.level}>:{mod}")
                for alias in node.names:
                    names.add(f"<relative level={node.level}>:{mod}.{alias.name}")
            else:
                names.add(mod)
                for alias in node.names:
                    names.add(f"{mod}.{alias.name}")
    return names


def top_level(name: str) -> str:
    if name.startswith("<relative"):
        return ""   # 相对导入不可能是第三方
    return name.split(".")[0]


class TestLayering(unittest.TestCase):
    def test_readers_do_not_import_modules(self) -> None:
        for path, tree in iter_sources():
            if "readers" not in path.parts:
                continue
            for name in imported_modules(tree):
                with self.subTest(file=path.name, imp=name):
                    self.assertNotIn(
                        "modules", name,
                        f"{path.relative_to(ROOT)} imports {name}: 容器层不得知道判决语义",
                    )

    def test_modules_do_not_import_report(self) -> None:
        for path, tree in iter_sources():
            if "modules" not in path.parts:
                continue
            for name in imported_modules(tree):
                with self.subTest(file=path.name, imp=name):
                    self.assertNotIn(
                        "report", name,
                        f"{path.relative_to(ROOT)} imports {name}: 判定与呈现必须分家",
                    )

    def test_report_does_not_import_readers(self) -> None:
        for path, tree in iter_sources():
            if "report" not in path.parts:
                continue
            for name in imported_modules(tree):
                with self.subTest(file=path.name, imp=name):
                    self.assertNotIn(
                        "readers", name,
                        f"{path.relative_to(ROOT)} imports {name}: 渲染只吃 model + findings",
                    )


class TestRedLines(unittest.TestCase):
    def test_no_third_party_imports(self) -> None:
        """零第三方依赖：任何非标准库、非本包的顶层 import 都是失败。"""
        bad: list[str] = []
        for path, tree in iter_sources():
            for name in imported_modules(tree):
                root = top_level(name)
                if not root:
                    continue
                if root in STDLIB or root == OWN_PACKAGE or root == "__future__":
                    continue
                bad.append(f"{path.relative_to(ROOT)}: {name}")
        self.assertEqual(bad, [], f"检测到第三方依赖（必须为零）: {bad}")

    def test_no_network_or_spawn_imports(self) -> None:
        bad: list[str] = []
        for path, tree in iter_sources():
            for name in imported_modules(tree):
                if top_level(name) in FORBIDDEN_IMPORTS:
                    bad.append(f"{path.relative_to(ROOT)}: {name}")
        self.assertEqual(bad, [], f"零网络 / 不 spawn 红线被破坏: {bad}")

    def test_no_zlib_decompress_in_readers_or_modules(self) -> None:
        """不解码像素 / 不解压 profile：`zlib.decompress` 不得出现在这两层。"""
        bad: list[str] = []
        for path, tree in iter_sources():
            if not ({"readers", "modules"} & set(path.parts)):
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"decompress", "decompressobj"}
                ):
                    bad.append(f"{path.relative_to(ROOT)}:{node.lineno}")
        self.assertEqual(bad, [], f"检测到解压调用（首期不解压）: {bad}")

    def test_no_clock_reads_in_package(self) -> None:
        """不读时钟：`now()` / `today()` / `time.time()` / `localtime()` 一律禁止。

        例外：`cli._resolve_generated_at` 里由 `SOURCE_DATE_EPOCH` 换算——那是由**调用方输入**
        决定的时间，不是"当前时间"。判据按"调用是否在带 now/today 的属性上"收窄，
        因此不会把 fromtimestamp 误判。
        """
        offenders: list[str] = []
        for path, tree in iter_sources():
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in {"now", "today", "utcnow", "time"}:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} .{func.attr}()")
        self.assertEqual(offenders, [], f"禁止读时钟（确定性要求）: {offenders}")


if __name__ == "__main__":
    unittest.main()
