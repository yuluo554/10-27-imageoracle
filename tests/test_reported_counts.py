# -*- coding: utf-8 -*-
"""自述测试数守门：文档里写的条数必须等于**真实跑出来的**条数。

为什么要有这一条（本仓第二轮实测）：`222` 这个数字在 README / `plan/RELEASE-M6.md` /
CHANGELOG 里共 6 处，此刻**全部正确**，但 `grep -rn "222" tests/ tools/` 命中 0 ——
也就是说没有任何门守着它。下一棒加一条测试，这 6 处就会同时过期，而它们会随
`git archive` 进 Release 附件（本仓发布物 = 源码包），读者拿到的是错的数字。

三条判据（正好 3 条，见 `update/01-迭代路线.md` B3-2）：

  ① `test_documented_test_count_matches_reality`
     真跑一次 `unittest discover`（**子进程**，不复用本进程结果），从 stderr 解析
     `Ran (\\d+) tests`，再扫文档里每一处"当前条数"声明，全部必须等于实测。
  ② `test_no_stale_count_strings`
     守门上线前的旧值（`222`）不得再出现在扫描面上——它是"改了文档没改真值"的化石。
  ③ `test_count_gate_finds_the_docs`
     阴性对照：把目标文本读成空串时，① 与 ② 必须**失败**（否则说明判据根本没扫到东西）。

**扫描面为什么是"当前声明"而不是"全部历史"**（实测得来的口径，不是猜）：

1. `CHANGELOG.md` 的每个里程碑小节都写着**当时的**真实条数（`47 项` / `65 项` / `79 项` /
   `104 项` / `146 项` / `178 项` / `222 项`）。按字面"扫整份 CHANGELOG"会在线第一秒假红；
   把历史改成今天的条数等于篡改历史（`plan/RELEASE-M6.md` §二 明写"已公开的历史不删不改写"）。
   ⇒ 只扫**最新顶层版本段**。
2. `plan/RELEASE-M6.md` §一 是**带日期的时点事实表**（"本机实测，2026-10-27"），里面的 222
   是 v0.5.0 tag 时点的真值，不是今天的声明。⇒ 只扫**编号最大的那份** `plan/RELEASE-M*.md`。
3. `plan/HANDOFF-*` 是那一棒的交接单，天然是历史。⇒ 不入扫描面。

注意这与"放宽口径"无关：判据面是"当前对读者做的数量承诺"，历史段不属于这个集合；
占位符判据（`LAYOUT.RELEASE_PLACEHOLDER`）仍然扫**全部** `RELEASE-M*.md`，因为历史留档
里也不许有未回填的占位符。

**递归防护**（实测必须处理）：① 用子进程跑全量 discover，而本文件就在这套用例里 ——
子进程会再次发现本测试并再开一个子进程，形成无限递归。解法：给子进程注入
`IMAGEORACLE_COUNT_PROBE=1`，本测试检测到该变量时**直接返回**（此时它仍是一条
测试，只是不做断言）——这样父进程数到的条数与子进程数到的条数完全一致。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 全文扫描的文件（当前声明）
SCAN_FULL = ("README.md",)
#: 只扫最新顶层版本段的文件（历史小节保留当时的真值）
SCAN_LATEST_SECTION = ("CHANGELOG.md",)

#: 「当前条数」的声明形态。三条都要覆盖：
#:   全量测试（225 项，零依赖）      → `（\d+ 项`
#:   `unittest`（225 项）           → `（\d+ 项`
#:   全量 **225 项** `unittest` 绿   → `\*\*\d+ 项\*\*`
#:   → **Ran 225 tests** / Ran 225 tests
COUNT_CLAIM = re.compile(r"(?:（|\*\*)(\d+)\s*项|Ran\s+(\d+)\s+tests")

#: 守门上线前的旧值（本仓第二轮前实测 222）。它一旦重新出现，说明有人回滚了文档
#: 或新加了一条测试却没同步数字。
STALE_COUNT = "222"

#: 子进程标记：带它运行时本测试不做断言（防无限递归）
PROBE_ENV = "IMAGEORACLE_COUNT_PROBE"


def _latest_section(text: str) -> str:
    """取 CHANGELOG 最新的顶层版本段（第一个 `## [` 到下一个 `## ` 之间）。"""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("## [")), None)
    if start is None:
        return ""
    end = next(
        (i for i, line in enumerate(lines[start + 1:], start=start + 1) if line.startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end])


def _live_release_parts(text: str) -> str:
    """从发布留档里只取「tag 后追加」这一栏（活的那部分）。

    为什么不是整份：`## 一、tag 前事实` 是**带日期冻结**的时点表（"本机实测，2026-10-27"），
    里面的条数是那个 tag 时点的真值，不该被今天的条数追着改。`## 二、tag 后追加` 才是
    发布后持续回填的活文档，当前的数量承诺落在这里。
    """
    idx = text.find("## 二、tag 后追加")
    return text[idx:] if idx >= 0 else ""


def latest_release() -> str | None:
    """编号最大的 `plan/RELEASE-M<k>.md`（相对路径）。"""
    best: tuple[int, str] | None = None
    for path in sorted((ROOT / "plan").glob("RELEASE-M*.md")):
        m = re.search(r"RELEASE-M(\d+)\.md$", path.name)
        if not m:
            continue
        n = int(m.group(1))
        if best is None or n > best[0]:
            best = (n, f"plan/{path.name}")
    return best[1] if best else None


def scan_texts(overrides: dict[str, str] | None = None) -> dict[str, str]:
    """读扫描面文本。`overrides` 用于阴性对照（传空串模拟"什么都没读到"）。"""
    overrides = overrides or {}
    texts: dict[str, str] = {}
    for rel in SCAN_FULL:
        texts[rel] = overrides.get(rel, (ROOT / rel).read_text(encoding="utf-8"))
    for rel in SCAN_LATEST_SECTION:
        if rel in overrides:
            texts[rel] = overrides[rel]
        else:
            texts[rel] = _latest_section((ROOT / rel).read_text(encoding="utf-8"))
    rel = latest_release()
    if rel is not None:
        if rel in overrides:
            texts[rel] = overrides[rel]
        else:
            texts[rel] = _live_release_parts((ROOT / rel).read_text(encoding="utf-8"))
    return texts


def count_violations(actual: int, texts: dict[str, str]) -> list[str]:
    """每一处"当前条数"声明与实测不符 → 一条违规。"""
    bad: list[str] = []
    for rel, text in texts.items():
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in COUNT_CLAIM.finditer(line):
                documented = int(m.group(1) or m.group(2))
                if documented != actual:
                    bad.append(f"{rel}:{lineno} 写 {documented}，实测 {actual} —— {line.strip()[:70]}")
    return bad


def stale_violations(texts: dict[str, str]) -> list[str]:
    """「当前条数」声明里出现守门上线前的旧值。

    判据**锚 `COUNT_CLAIM` 这种结构化声明**，不做裸字符串搜索。

    为什么（实测撞出来的）：裸 `"222" in line` 会命中两类**正确**的文本——
      · `data/README` 那类星数/计数（`2228★`，虽然不在扫描面内，但换一份文档就会中）；
      · 本仓 CHANGELOG 0.5.2 段那句"条数从 222 → 226"的正确历史叙述。
    这正是假门族「扫自由文本」：判据要落在**结构位置**（"文档声称当前是多少条"），
    而不是"这句话里出现过 222 这个数字"。收窄后 ② 与 ① 共用同一套声明形态，
    差别只在 ① 拿实测值比、② 拿旧值比（即使实测恰好退回 222，② 仍会指认它是化石）。
    """
    bad: list[str] = []
    for rel, text in texts.items():
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in COUNT_CLAIM.finditer(line):
                documented = m.group(1) or m.group(2)
                if documented == STALE_COUNT:
                    bad.append(f"{rel}:{lineno} 当前条数仍声明为旧值 {STALE_COUNT} —— {line.strip()[:70]}")
    return bad


def claimed_count(texts: dict[str, str]) -> int:
    """扫描面上"当前条数"声明的数量（阴性对照用：0 = 判据空跑）。"""
    return sum(len(list(COUNT_CLAIM.finditer(t))) for t in texts.values())


def measure_actual() -> int:
    """真跑一次全量 discover，返回 `Ran N tests` 里的 N。"""
    env = dict(os.environ)
    env[PROBE_ENV] = "1"          # 防递归：子进程里的本测试直接返回
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = "src"
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    m = re.search(r"^Ran (\d+) tests? in ", proc.stderr, re.MULTILINE)
    if m is None:
        raise AssertionError(
            "子进程里读不到 `Ran N tests`（判据无法取证）：\n"
            f"rc={proc.returncode}\nstdout={proc.stdout[-800:]}\nstderr={proc.stderr[-800:]}"
        )
    if proc.returncode != 0:
        raise AssertionError(f"子进程跑测试不绿（rc={proc.returncode}）：\n{proc.stderr[-1500:]}")
    return int(m.group(1))


class TestReportedCounts(unittest.TestCase):
    def test_documented_test_count_matches_reality(self) -> None:
        if os.environ.get(PROBE_ENV):
            return  # 子进程递归防护（见模块 docstring）
        texts = scan_texts()
        actual = measure_actual()
        self.assertGreater(
            claimed_count(texts), 0,
            f"扫描面上 0 处条数声明——判据空跑（扫了 {list(texts)}）",
        )
        problems = count_violations(actual, texts)
        self.assertEqual(problems, [], "文档里的测试条数与实测不符：\n" + "\n".join(problems))

    def test_no_stale_count_strings(self) -> None:
        if os.environ.get(PROBE_ENV):
            return
        problems = stale_violations(scan_texts())
        self.assertEqual(problems, [], "文档里还有守门上线前的旧条数：\n" + "\n".join(problems))

    def test_count_gate_finds_the_docs(self) -> None:
        """阴性对照：两项判据都必须真的扫到东西，而不是恒绿。

        两个方向一起验：
          · 目标文本读成空 → ① 的"扫到 0 处声明"守卫必须报警（判据空跑要被抓住）；
          · 把旧值写回一行 → ② 必须报出来（否则 ② 是假判据）。
        """
        blank = {rel: "" for rel in SCAN_FULL + SCAN_LATEST_SECTION}
        texts = scan_texts(blank)
        self.assertEqual(claimed_count(texts), 0, "空文本仍读出条数声明 → 正则有误")
        self.assertEqual(count_violations(999, texts), [], "空文本不该产生违规（它确实没扫到东西）")
        # 空文本下"0 处声明"由 ① 的 assertGreater 捕获 → 判据会红而不是静默通过。
        with self.assertRaises(AssertionError):
            self.assertGreater(claimed_count(texts), 0, "扫描面上 0 处条数声明——判据空跑")

        planted = {rel: f"全量测试（{STALE_COUNT} 项，零依赖）\n" for rel in SCAN_FULL}
        self.assertTrue(stale_violations(planted), "写回旧值后仍无违规 → ② 是假判据")
        # 反向：把旧值写进**叙述**（不是当前条数声明）时 ② 不许误伤——
        # "条数从 222 → 226" 是正确的历史叙述，裸字符串搜索会把它判红（实测撞过）。
        narration = {rel: f"条数从 {STALE_COUNT} → 226（历史叙述，不是当前声明）\n" for rel in SCAN_FULL}
        self.assertEqual(stale_violations(narration), [], "叙述里的旧值被误判 → ② 收窄得过头或过宽")


if __name__ == "__main__":
    unittest.main()
