#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门自证：逐条变异 → 门**必须变红**；还原 → 复绿。

为什么需要这个：一条门"跑了且绿"不等于"门里每条判据都被证伪过一次"。
本脚本按「判据有几条就覆盖几条」组织（`references/methodology-binding.md` §二）：

  布局门（check_sprint_layout.py）
    L1  删 AGENTS.md                        → LAYOUT.FILES 红
    L2  删一份 plan/04                      → LAYOUT.FILES 红（计划套件不齐）
    L3  删 plan/00 顶部装订行               → LAYOUT.BINDING_HEAD 红
    L4  删 HANDOFF-M1                       → LAYOUT.HANDOFFS 红
    L5  删 HANDOFF 的一节标题               → LAYOUT.HANDOFFS 红
    L6  在**一个副本**里把 ✅ 翻成 ⬜        → LAYOUT.STATUS 红（跨副本不一致）
    L8  往缺口格写已 ✅ 的里程碑号          → LAYOUT.GAPS 红
    L9  往台账某条挂 ⬜ 待 M<已✅>           → LAYOUT.LEDGER 红
    L10 文档点名一个不存在的 tools/ 脚本    → LAYOUT.DOC_TOOLS 红
    L11 把发布里程碑翻 ✅ 但不写留档         → LAYOUT.RELEASE 红
    L12 删某一节的必需小节关键词             → LAYOUT.SECTIONS 红

  脱敏门（check_desensitized.py）
    D1  写入盘符绝对路径                    → absolute-session-path 红
    D2  写 MSYS 形式 /c/Users/<name>/        → msys-user-path 红
    D3  写本机用户名                        → local-username 红
    D4  写 127.0.0.1:7897                   → loopback-proxy 红
    D5  写占位符 C:\\Users\\<user>\\…        → **必须绿**（阴性对照：放行是对的）

**变异必须断言"字节真的变了"**（假变异三连第①条）：替换前 assert marker 存在，
替换后 assert 文件已变，还原后 assert 字节一致。全部走 try/finally。

**实现选择**：本脚本**不 spawn 子进程**，而是直接 import 两个门模块并调用其 `main()`，
用 `contextlib.redirect_stdout` 抓输出。理由有三：① 少一个进程边界，退出码语义更直接；
② 不引入任何命令拼装面（安全工具也不必担心）；③ 门模块的 `main()` 本来就是纯函数式入口
（参数从 argv 解析、读仓库内文件、返回 int），进程内调用与命令行调用行为等价。

CLI:  py -3.12 tools/verify_gates.py [--only layout|desens]
退出码：0 全部符合预期 / 1 有门未如期变红（假门） / 2 用法错误
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path
from types import ModuleType

EXIT_OK = 0
EXIT_BAD = 1
EXIT_USAGE = 2

ROOT = Path(__file__).resolve().parent.parent

#: 允许调用的门模块白名单（不接受任意外部输入作为模块名）
GATE_MODULES = ("check_sprint_layout", "check_desensitized")


def load_gate(name: str) -> ModuleType:
    """按白名单加载 tools/<name>.py（不执行 __main__ 分支）。"""
    if name not in GATE_MODULES:
        raise ValueError(f"不是白名单里的门模块: {name}")
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_gate_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载门模块: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_gate(name: str) -> tuple[int, str]:
    """在**进程内**跑门，返回 (退出码, 合并输出)。"""
    module = load_gate(name)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = module.main([])
    return code, buffer.getvalue()


class Mutation:
    """一个文件的一次文本变异（可还原）。"""

    def __init__(self, rel: str, old: str, new: str) -> None:
        self.rel = rel
        self.old = old
        self.new = new
        self.original = ""

    def apply(self) -> None:
        path = ROOT / self.rel
        self.original = path.read_text(encoding="utf-8")
        assert self.old in self.original, f"变异 marker 不在 {self.rel} 里: {self.old!r}"
        mutated = self.original.replace(self.old, self.new, 1)
        assert mutated != self.original, f"变异没有改变字节: {self.rel}"
        path.write_text(mutated, encoding="utf-8")

    def restore(self) -> None:
        path = ROOT / self.rel
        path.write_text(self.original, encoding="utf-8")
        assert path.read_text(encoding="utf-8") == self.original, f"还原失败: {self.rel}"


class Deletion:
    """删掉一个文件（先备份到临时目录）。"""

    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.backup: Path | None = None
        self.tmpdir: tempfile.TemporaryDirectory | None = None

    def apply(self) -> None:
        src = ROOT / self.rel
        assert src.is_file(), f"要删的文件不存在: {self.rel}"
        self.tmpdir = tempfile.TemporaryDirectory()
        self.backup = Path(self.tmpdir.name) / src.name
        shutil.copy2(src, self.backup)
        src.unlink()
        assert not src.exists(), "删除没有生效"

    def restore(self) -> None:
        assert self.backup is not None and self.backup.is_file()
        shutil.copy2(self.backup, ROOT / self.rel)
        assert (ROOT / self.rel).is_file(), "还原失败"
        if self.tmpdir:
            self.tmpdir.cleanup()


class CompoundMutation:
    """把多个变异当成一个原子操作（apply 全做、restore 全还原）。

    为什么需要（本项目的真缺陷）：`LAYOUT.HANDOFFS` 只对**已 ✅** 的里程碑查交接单，
    而 M0 已声明豁免、M1 尚未完成 → 直接删 `HANDOFF-M1.md` **门不会红**（判据根本没读到它）。
    照原样写变异会得出"门是假门"的错误结论。正解 = 先把 M1 在三处副本里翻成 ✅
    （让判据激活），再动交接单；**判据面一条不减**，且两条分支都断言字节真的变了。
    """

    def __init__(self, *mutations) -> None:
        self.mutations = mutations

    def apply(self) -> None:
        applied = []
        try:
            for mutation in self.mutations:
                mutation.apply()
                applied.append(mutation)
        except Exception:
            for mutation in reversed(applied):
                mutation.restore()
            raise

    def restore(self) -> None:
        for mutation in reversed(self.mutations):
            mutation.restore()


def activate_milestone(milestone: int, copies: tuple[str, ...]) -> CompoundMutation:
    """把某里程碑在**全部**状态副本里翻成 ✅（让 HANDOFF 判据激活）。"""
    mutations = []
    for rel in copies:
        line = _status_line_for(rel, milestone)
        assert line is not None, f"{rel} 里找不到 M{milestone} 的状态行"
        assert "⬜" in line, f"{rel} 的 M{milestone} 行不是 ⬜（当前: {line.strip()[:60]}）"
        mutations.append(Mutation(rel, line, line.replace("⬜", "✅")))
    return CompoundMutation(*mutations)


def expect(
    gate: str,
    mutation,
    *,
    note: str,
    want_red: bool = True,
    fail_id: str | None = None,
) -> tuple[bool, str]:
    """对一次变异断言门的**退出码**，并（可选）断言**到底是哪条判据**红了。

    `fail_id` 不是可选项而是纪律：skill 明确点名"断言张冠李戴"这一形态——
    把淘汰赛写成"命中列表为空"等于同时断言了所有判据。例如"发布里程碑 ✅ 但无留档"
    若只改一个副本，`LAYOUT.STATUS` 会先红，看起来像 RELEASE 判据生效，其实不是。
    传了 `fail_id` 就只认那一条：目标判据没红 = 这条变异没验到东西。
    """
    mutation.apply()
    try:
        rc, out = run_gate(gate)
    finally:
        mutation.restore()
    ok = (rc != 0) if want_red else (rc == 0)
    detail = f"rc={rc}"
    if ok and fail_id:
        red_ids = [line.split()[1] for line in out.splitlines() if line.startswith("FAIL  ")]
        if fail_id not in red_ids:
            ok = False
            detail += f", 但 {fail_id} 未红（红的是 {red_ids or '无'}）"
        else:
            detail += f", {fail_id} 已红"
    return ok, f"{'OK' if ok else 'FALSE-GATE'}  {note}  ({detail})"


def _status_line_for(rel: str, milestone: int) -> str | None:
    path = ROOT / rel
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(rf"^\|\s*\*{{0,2}}M{milestone}\b", line):
            return line
    return None


def _first_done_status_line(rel: str) -> str | None:
    path = ROOT / rel
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\|\s*\*{0,2}M\d+\b", line) and "✅" in line:
            return line
    return None


def layout_cases(results: list[tuple[bool, str]]) -> None:
    gate = "check_sprint_layout"

    results.append(expect(gate, Deletion("AGENTS.md"), note="L1 删 AGENTS.md → FILES 红", fail_id="LAYOUT.FILES"))
    results.append(expect(gate, Deletion("plan/04-数据计划.md"), note="L2 删 plan/04 → FILES 红", fail_id="LAYOUT.FILES"))

    results.append(
        expect(
            gate,
            Mutation(
                "plan/00-README总览.md",
                "> 方法论：`ai-tool-project-sprint`（装订 2026-10-27）",
                "> 方法论：本项目自定",
            ),
            note="L3 删 plan/00 顶部装订行 → BINDING_HEAD 红", fail_id="LAYOUT.BINDING_HEAD",
        )
    )

    results.append(
        expect(
            gate,
            Mutation("plan/02-架构与技术选型.md", "## 二、分层", "## 二、结构"),
            note="L12 删必需小节关键词 → SECTIONS 红", fail_id="LAYOUT.SECTIONS",
        )
    )

    # L4 / L5：靶子是"仓库里有这么一件东西"（HANDOFF 已落盘），不依赖项目进度。
    # **关键**：HANDOFF 判据只对已 ✅ 的里程碑生效，而 M1 尚未完成 → 必须先把 M1
    # 在三处副本里翻成 ✅ 让判据激活，再动交接单（否则变异恒绿 = 假门结论）。
    STATUS_COPY_FILES = (
        "plan/00-README总览.md",
        "plan/05-里程碑与发布.md",
        "README.md",
    )
    handoff_rel = "plan/HANDOFF-M1.md"
    handoff = ROOT / handoff_rel
    if handoff.is_file():
        text = handoff.read_text(encoding="utf-8")
        section = next((s for s in ("## 三、下一棒待办", "## 三、待办") if s in text), None)
        if section:
            results.append(
                expect(
                    gate,
                    CompoundMutation(
                        activate_milestone(1, STATUS_COPY_FILES),
                        Mutation(handoff_rel, section, "## 三、后续"),
                    ),
                    note="L5 删 HANDOFF 必需节关键词（M1 已激活）→ HANDOFFS 红", fail_id="LAYOUT.HANDOFFS",
                )
            )
        else:
            results.append((False, "SKIP-L5  HANDOFF-M1 里找不到可用的节标题"))
        results.append(
            expect(
                gate,
                CompoundMutation(activate_milestone(1, STATUS_COPY_FILES), Deletion(handoff_rel)),
                note="L4 删 HANDOFF-M1（M1 已激活）→ HANDOFFS 红", fail_id="LAYOUT.HANDOFFS",
            )
        )
    else:
        results.append((False, "SKIP-L4/L5  HANDOFF-M1.md 尚不存在"))

    # L6：两态探测——找 ✅ 行翻成 ⬜（不依赖"还有待办里程碑"，永不过期）
    status_line = _first_done_status_line("README.md")
    if status_line:
        results.append(
            expect(
                gate,
                Mutation("README.md", status_line, status_line.replace("✅", "⬜")),
                note="L6 单副本翻状态 → STATUS 红（跨副本不一致）", fail_id="LAYOUT.STATUS",
            )
        )
    else:
        results.append((False, "SKIP-L6  README.md 里找不到 ✅ 状态行"))

    results.append(
        expect(
            gate,
            Mutation(
                "plan/06-交付对标与决策.md",
                "| 跨解释器字节哈希一致 | 不承诺（zlib 版本差异） |",
                "| M0 归档 | 已关闭 | 不适用 |\n| 跨解释器字节哈希一致 | 不承诺（zlib 版本差异） |",
            ),
            note="L8 缺口格写入已 ✅ 的 M0 → GAPS 红", fail_id="LAYOUT.GAPS",
        )
    )

    results.append(
        expect(
            gate,
            Mutation(
                "plan/00-README总览.md",
                "| $3,000 悬赏 | margelo/react-native-vision-camera#1891 | ✅ |",
                "| $3,000 悬赏 | margelo/react-native-vision-camera#1891 | ⬜ 待 M0 |",
            ),
            note="L9 台账挂已 ✅ 里程碑的未完成标记 → LEDGER 红", fail_id="LAYOUT.LEDGER",
        )
    )

    results.append(
        expect(
            gate,
            Mutation(
                "AGENTS.md",
                "python tools/check_sprint_layout.py    # 布局门（方法论装订）；必须绿，红了先修布局再干活",
                "python tools/check_sprint_layout.py    # 布局门\npython tools/not_implemented_gate.py   # 故意点名一个不存在的脚本",
            ),
            note="L10 文档点名不存在的 tools/ 脚本 → DOC_TOOLS 红", fail_id="LAYOUT.DOC_TOOLS",
        )
    )

    # L11：发布里程碑在**全部副本**翻 ✅ 但没有留档 → 只应 RELEASE 红（STATUS 不该红）
    release_milestone = 6
    release_doc = ROOT / "plan" / f"RELEASE-M{release_milestone}.md"
    if release_doc.is_file():
        results.append((True, "SKIP-L11  留档已存在，本条不适用"))
    else:
        try:
            results.append(
                expect(
                    gate,
                    activate_milestone(release_milestone, STATUS_COPY_FILES),
                    note="L11 发布里程碑全副本翻 ✅ 但无留档 → RELEASE 红",
                    fail_id="LAYOUT.RELEASE",
                )
            )
        except AssertionError as exc:
            results.append((False, f"SKIP-L11  构造不出靶子: {exc}"))


def desens_cases(results: list[tuple[bool, str]]) -> None:
    gate = "check_desensitized"
    probe_rel = "docs/_gate_probe.md"
    target = ROOT / probe_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    backslash = chr(92)

    probes = [
        ("D1 盘符绝对路径", f"path is C:{backslash}Users{backslash}someone{backslash}repo\n", True),
        ("D2 MSYS 用户路径", "/c/Users/someone/repo\n", True),
        ("D3 本机用户名", "owner: ASUS\n", True),
        ("D4 回环代理", "proxy = 127.0.0.1:7897\n", True),
        ("D5 占位符放行（阴性对照）", f"placeholder: C:{backslash}Users{backslash}<user>{backslash}repo\n", False),
    ]
    try:
        for name, content, want_red in probes:
            target.write_text(content, encoding="utf-8")
            rc, _out = run_gate(gate)
            ok = (rc != 0) if want_red else (rc == 0)
            results.append(
                (ok, f"{'OK' if ok else 'FALSE-GATE'}  {name} → {'红' if want_red else '绿'} (rc={rc})")
            )
    finally:
        if target.is_file():
            target.unlink()
        parent = target.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="两道门的变异验证")
    parser.add_argument("--only", choices=["layout", "desens"], default=None)
    args = parser.parse_args(argv)

    results: list[tuple[bool, str]] = []

    gates: list[str] = []
    if args.only in (None, "layout"):
        gates.append("check_sprint_layout")
    if args.only in (None, "desens"):
        gates.append("check_desensitized")

    # 基线：未变异时必须全绿
    for gate in gates:
        rc, _out = run_gate(gate)
        results.append((rc == 0, f"{'OK' if rc == 0 else 'BASELINE-RED'}  基线未变异  {gate}  (rc={rc})"))

    if args.only in (None, "layout"):
        layout_cases(results)
    if args.only in (None, "desens"):
        desens_cases(results)

    width = max((len(note) for _ok, note in results), default=0)
    print("门自证（变异验证）")
    print("=" * (width + 24))
    for ok, note in results:
        print(f"{'PASS' if ok else 'FAIL'}  {note}")
    print("=" * (width + 24))
    failed = [r for r in results if not r[0]]
    print(
        f"结论: {len(results) - len(failed)}/{len(results)} 符合预期"
        + ("" if not failed else f"，{len(failed)} 条不符（假门或变异失效）")
    )

    # 最后再跑一次基线，确认还原干净
    for gate in gates:
        rc, _out = run_gate(gate)
        if rc != 0:
            print(f"FAIL  还原后 {gate} 仍红——变异没有还原干净")
            return EXIT_BAD
    return EXIT_OK if not failed else EXIT_BAD


if __name__ == "__main__":
    sys.exit(main())
