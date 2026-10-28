#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""布局门（方法论装订第②件）：把"项目还长在方法论上"变成可跑红的断言。

判据一律落**仓库内文件**（不读 git 元数据——浅克隆下 git tag / 历史深度会翻转）。

CLI:  py -3.12 tools/check_sprint_layout.py [--root <dir>]
退出码：0 全绿 / 1 有 FAIL / 2 用法错误。

判据集（每条都配了变异组，见 tools/verify_gates.py）：
  LAYOUT.FILES        必备件存在
  LAYOUT.BINDING_HEAD plan/00 顶部装订行（三锚点同现）
  LAYOUT.SECTIONS     各文档必需小节
  LAYOUT.STATUS       里程碑状态在多处副本上一致 + 每副本命中行数可见 + 合计 0 行即空跑
  LAYOUT.HANDOFFS     每个 ✅ 里程碑有七节交接单
  LAYOUT.GAPS         缺口表不得再提已成 ✅ 的里程碑
  LAYOUT.LEDGER       承诺-证据台账不得挂已 ✅ 里程碑的未完成标记
  LAYOUT.RELEASE      发布留档（仅在发布里程碑 ✅ 后要求；未完成时报"不适用"）
  LAYOUT.RELEASE_PLACEHOLDER 发布留档里不得残留尖括号版本占位符（`<v0.5.1>` 这类）
  LAYOUT.DOC_TOOLS    文档点名的 tools/ 脚本必须有实物
  LAYOUT.GATE_SELFTEST 本次运行确实读过文件（非空跑自证）

设计纪律（来自 ai-tool-project-sprint references/methodology-binding.md）：
  · 真值不取自任何一个副本（逐副本采集，任一不一致即 FAIL）
  · 判据锚标题行 / 表格行，不扫自由文本
  · 被检查对象不存在时报 FAIL 并继续，绝不抛异常逃逸
  · 扫描面在注释里写明起止
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


# ─────────────────────────────────────────────────────────────────────────────
# 配置区（项目特有；判据本身不要改）
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "pyproject.toml",
    "data/README.md",
    ".github/workflows/ci.yml",
    "plan/00-README总览.md",
    "plan/01-题目文档.md",
    "plan/02-架构与技术选型.md",
    "plan/03-模块详设.md",
    "plan/04-数据计划.md",
    "plan/05-里程碑与发布.md",
    "plan/06-交付对标与决策.md",
    "tools/check_sprint_layout.py",
    "tools/check_desensitized.py",
]

# 装订行：三个锚点必须**同现于一行**（顺序无关，用前瞻；写死顺序会假红）
BINDING_LINE = re.compile(
    r"^>(?=.*ai-tool-project-sprint)(?=.*check_sprint_layout)(?=.*20\d{2}-\d{2}-\d{2}).*$",
    re.MULTILINE,
)

REQUIRED_SECTIONS = {
    "plan/00-README总览.md": ["文档索引", "决策记录", "承诺-证据台账", "里程碑"],
    "plan/01-题目文档.md": ["任务要求", "评分表", "边界与非目标"],
    "plan/02-架构与技术选型.md": ["分层", "构建"],
    "plan/03-模块详设.md": ["公共契约", "退出码"],
    "plan/04-数据计划.md": ["数据清单", "真值纪律", "数值口径"],
    "plan/05-里程碑与发布.md": ["里程碑状态表", "已知未验证项", "发布动作序列"],
    "plan/06-交付对标与决策.md": ["评分对标", "缺口表", "风险登记"],
    "data/README.md": ["三态总览", "规范事实台账", "数值口径"],
    "README.md": ["状态", "安装"],
}

# 状态副本：同一里程碑在这几处的状态必须互相一致。
# 只认"表格行且首格是里程碑号"，散文状态行不参与判定（防张冠李戴假红）。
STATUS_COPIES = [
    "plan/00-README总览.md",
    "plan/05-里程碑与发布.md",
    "README.md",
]
#: 只认「首格**恰好**是 M<k>（可加粗）」的表格行。
#:
#: 为什么这么严（本项目首个门自证就抓到的真缺陷）：`plan/05` §一 有一张
#: 「里程碑映射表」，行首是 `| M2 orientation 判定器 | **M1** … |`——宽判据
#: `^\|\s*\*{0,2}M(\d+)\b` 会把这种**标识符行**读成状态行（无 ⬜ → 判成 done），
#: 于是 M1–M6 全被读成"已完成"，STATUS / HANDOFFS / GAPS / RELEASE 四条判据同时假红。
#: 这正是方法论里的假门族「标识符撞了状态 token」：判据要收窄到**状态行的唯一形态**。
STATUS_LINE = re.compile(r"^\|\s*\*{0,2}M(\d+)\*{0,2}\s*\|")
PENDING_MARKERS = ("⬜", "🟡", "未开始", "未执行", "待执行", "待确认", "待 M")

HANDOFF_SECTIONS = ["当前进度", "当前事实", "待办", "既定口径", "环境坑", "DoD", "命令速查"]
EXEMPT_MILESTONES = {0}  # 本仓已声明：M0（计划与骨架）不单出交接单，收尾记录 = 计划套件本身
HANDOFF_FORMAT_FROM = 1  # 从 M1 起必须七节齐
HANDOFF_EXEMPT_LAST = False  # 末棒也要交接单（写成"收官交接单"）

RELEASE_MILESTONE = 6  # 本项目的发布里程碑；未 ✅ 时报"尚不适用"

#: 发布留档里的**尖括号版本占位符**（`<v0.5.1>` / `<0.5.2>` / `< 1.2.3 >`）。
#:
#: 为什么单独一条判据（本项目已发生的真缺陷）：`plan/RELEASE-M6.md` 第 33/34 行的提交号
#: 从未回填，而本仓的发布物 = `git archive`（留档逐字节进附件）⇒ 占位符随 tag 树与
#: Release 附件一起发了出去。`LAYOUT.RELEASE` 只判"两栏 / 覆盖对账小节 / 三态行数"，
#: 对占位符完全无感。注意**不能**把 `<https://…>` 之类链接误判：正则要求尖括号内
#: 只有一个版本号。
RELEASE_PLACEHOLDER = re.compile(r"<\s*v?\d+\.\d+\.\d+\s*>")
RELEASE_GLOB = "RELEASE-M*.md"


# ─────────────────────────────────────────────────────────────────────────────
# 运行框架
# ─────────────────────────────────────────────────────────────────────────────

class Gate:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.checks: list[dict] = []
        self.read_count = 0

    def add(self, cid: str, ok: bool, detail: str) -> None:
        self.checks.append({"id": cid, "ok": ok, "detail": detail})

    def read(self, rel: str) -> str | None:
        path = self.root / rel
        if not path.is_file():
            return None
        self.read_count += 1
        return path.read_text(encoding="utf-8", errors="replace")


def check_required_files(g: Gate) -> None:
    missing = [rel for rel in REQUIRED_FILES if not (g.root / rel).is_file()]
    g.add(
        "LAYOUT.FILES",
        not missing,
        f"缺: {', '.join(missing)}" if missing else f"{len(REQUIRED_FILES)} 份齐备",
    )


def check_binding_head(g: Gate) -> None:
    text = g.read("plan/00-README总览.md") or ""
    ok = bool(BINDING_LINE.search(text))
    g.add(
        "LAYOUT.BINDING_HEAD",
        ok,
        "plan/00 顶部有装订行（三锚点齐）"
        if ok
        else "plan/00 顶部缺装订行（需同现：ai-tool-project-sprint + check_sprint_layout + 日期）",
    )


def _headings(text: str) -> list[str]:
    """抽出所有标题行（`#` 开头），供小节判据使用。"""
    return [line for line in text.splitlines() if re.match(r"^#{1,6}\s", line)]


def _has_section(text: str, needle: str) -> bool:
    """小节判据：**必须锚到标题行**，不做全文包含。

    为什么（本项目门自证抓出的真假门）：首版用 `needle in text`，于是
    `plan/02` 正文里那句"四层，依赖单向向下"让"分层"恒命中——把标题 `## 二、分层`
    整节删掉后门**仍然绿**。这正是方法论里的「扫自由文本」假门族（⑤）：
    判据要落在**结构位置**（标题行），不是"文本里出现过这个词"。
    变异验证 D/L12 现在能真的打红。
    """
    return any(needle in heading for heading in _headings(text))


def check_sections(g: Gate) -> None:
    bad: list[str] = []
    for rel, needles in REQUIRED_SECTIONS.items():
        text = g.read(rel)
        if text is None:
            bad.append(f"{rel}: 文件缺失")
            continue
        missing = [n for n in needles if not _has_section(text, n)]
        if missing:
            bad.append(f"{rel}: 缺 {'/'.join(missing)}")
    g.add(
        "LAYOUT.SECTIONS",
        not bad,
        "；".join(bad) if bad else f"{len(REQUIRED_SECTIONS)} 份小节齐备",
    )


def collect_states(g: Gate) -> tuple[dict[int, set[str]], dict[str, int]]:
    """逐副本采集状态：{k: {done|pending}}。真值不取自任何单一副本。"""
    states: dict[int, set[str]] = {}
    rows_by_copy: dict[str, int] = {}
    for rel in STATUS_COPIES:
        text = g.read(rel)
        if text is None:
            continue
        rows = 0
        for line in text.splitlines():
            m = STATUS_LINE.match(line)
            if not m:
                continue
            rows += 1
            pending = any(mark in line for mark in PENDING_MARKERS)
            states.setdefault(int(m.group(1)), set()).add("pending" if pending else "done")
        rows_by_copy[rel] = rows
    return states, rows_by_copy


def check_status(g: Gate, states: dict[int, set[str]], rows_by_copy: dict[str, int]) -> None:
    conflicts = [
        f"M{k} 在副本间状态不一致（{' vs '.join(sorted(v))}）"
        for k, v in sorted(states.items())
        if len(v) > 1
    ]
    total = sum(rows_by_copy.values())
    per_copy = " ".join(
        f"{Path(rel).stem}:{rows}" for rel, rows in sorted(rows_by_copy.items())
    )
    if total == 0:
        g.add("LAYOUT.STATUS", False, f"所有副本合计 0 行状态行（判据空跑）：{per_copy}")
        return
    g.add(
        "LAYOUT.STATUS",
        not conflicts,
        "；".join(conflicts)
        if conflicts
        else f"{len(rows_by_copy)} 处副本 × {len(states)} 个里程碑 状态全一致（行数 {per_copy}）",
    )


def check_handoffs(g: Gate, done: list[int], all_milestones: list[int]) -> None:
    last = max(all_milestones) if all_milestones else 0
    problems: list[str] = []
    scanned = 0
    for k in sorted(done):
        if k in EXEMPT_MILESTONES:
            continue
        if HANDOFF_EXEMPT_LAST and k == last:
            continue
        rel = f"plan/HANDOFF-M{k}.md"
        text = g.read(rel)
        if text is None:
            hint = "（末棒要么写收官交接单，要么置 HANDOFF_EXEMPT_LAST 并在 AGENTS.md 说明）" if k == last else ""
            problems.append(f"{rel} 缺失{hint}")
            continue
        scanned += 1
        if k < HANDOFF_FORMAT_FROM:
            continue
        # 判据锚**标题行**（不做全文包含：全文匹配会让正文里的同名话题把缺失的节掩盖掉）
        lack = [n for n in HANDOFF_SECTIONS if not _has_section(text, n)]
        if lack:
            problems.append(f"{rel} 缺节: {'/'.join(lack)}")
    g.add(
        "LAYOUT.HANDOFFS",
        not problems,
        "；".join(problems)
        if problems
        else f"{scanned} 份交接单齐（M0 已声明豁免{'；末棒已豁免' if HANDOFF_EXEMPT_LAST else ''}）",
    )


def check_gaps(g: Gate, done: list[int]) -> None:
    """扫描面 = plan/06 里首格含『缺口』的表头 → 第一张表结束（首条非表格行即止）。

    **判据扫整行所有单元格**（不只最后一列）。为什么（本项目门自证抓出的真假门）：
    首版只取**最后一列**（`len(cells) - 2`）去匹配里程碑号，于是"往**缺口格**里写
    一个已 ✅ 的里程碑"这类真实故障恒绿——而缺口格恰恰是第一列。这正是假门族 ②
    "按表头定位列"的反向误用：列定位是为了取**对的那一格**，而"这一行是否还挂着
    已完成的里程碑"这个判据本来就该看**整行**。
    行内代码与文件名先剥掉（假门族 ⑥：`plan/RELEASE-M6.md` 里的 `M6` 是文件名不是状态）。
    """
    text = g.read("plan/06-交付对标与决策.md")
    if text is None:
        g.add("LAYOUT.GAPS", False, "plan/06 缺失，无法核对缺口表")
        return
    lines = text.splitlines()
    header_idx = next(
        (i for i, line in enumerate(lines) if line.startswith("|") and "缺口" in line),
        -1,
    )
    if header_idx < 0:
        g.add("LAYOUT.GAPS", False, "plan/06 找不到含『缺口』表头的表（判据表搬走了？）")
        return
    stale: list[str] = []
    scanned_rows = 0
    for line in lines[header_idx + 2:]:
        if not line.startswith("|"):
            break
        scanned_rows += 1
        row = line
        # ⑥：先剥"证据在哪份文件"（行内代码 + 文件名/路径），剩下的才是"状态引用"
        row = re.sub(r"`[^`]*`", " ", row)
        row = re.sub(r"[\w./-]+\.(?:md|py|mjs|js|json|toml|txt|yml|yaml)", " ", row)
        for k in done:
            if re.search(rf"(^|[^0-9A-Za-z])M{k}([^0-9]|$)", row):
                stale.append(f"缺口行仍提 M{k}: {row.strip()[:70]}")
    g.add(
        "LAYOUT.GAPS",
        not stale,
        "；".join(stale)
        if stale
        else f"缺口列扫了 {scanned_rows} 行，无已 ✅ 里程碑",
    )


def check_ledger(g: Gate, done: list[int]) -> None:
    """承诺-证据台账是第四份状态副本，按它自己的表头定位。"""
    text = g.read("plan/00-README总览.md")
    if text is None:
        g.add("LAYOUT.LEDGER", False, "plan/00 缺失，无法核对台账")
        return
    lines = text.splitlines()
    header_idx = next(
        (
            i
            for i, line in enumerate(lines)
            if line.startswith("|") and "承诺" in line and "状态" in line
        ),
        -1,
    )
    if header_idx < 0:
        g.add("LAYOUT.LEDGER", False, "plan/00 找不到『承诺-证据台账』表头（承诺项 + 状态列）")
        return
    bad: list[str] = []
    rows = 0
    for line in lines[header_idx + 2:]:
        if not line.startswith("|"):
            break
        rows += 1
        cells = [c.strip() for c in line.split("|")]
        status = cells[-2] if len(cells) >= 2 else ""
        if not re.search(r"[⬜🟡]|未开始|待 M\d|待开工", status):
            continue
        for k in done:
            if re.search(rf"(^|[^0-9A-Za-z])M{k}([^0-9]|$)", status, re.IGNORECASE):
                bad.append(f"台账行仍挂未完成: {status[:60]}")
    g.add(
        "LAYOUT.LEDGER",
        not bad and rows > 0,
        "台账表 0 行——判据空跑"
        if rows == 0
        else ("；".join(bad) if bad else f"台账 {rows} 行，已成 ✅ 的里程碑无未完成标记"),
    )


def check_release(g: Gate, done: list[int], all_milestones: list[int]) -> None:
    if RELEASE_MILESTONE == 0 or RELEASE_MILESTONE not in done:
        scanned = len(done)
        g.add(
            "LAYOUT.RELEASE",
            True,
            f"发布里程碑 M{RELEASE_MILESTONE} 未完成，收尾记录尚不适用（已扫 {scanned} 个 ✅ 里程碑）",
        )
        return
    release = g.read(f"plan/RELEASE-M{RELEASE_MILESTONE}.md")
    wrapup = g.read(f"plan/WRAPUP-M{RELEASE_MILESTONE}.md")
    if release is None and wrapup is None:
        g.add(
            "LAYOUT.RELEASE",
            False,
            f"缺 plan/RELEASE-M{RELEASE_MILESTONE}.md 或 plan/WRAPUP-M{RELEASE_MILESTONE}.md",
        )
        return
    if release is not None:
        cols = bool(
            re.search(r"^##\s*一、tag 前事实", release, re.MULTILINE)
            and re.search(r"^##\s*二、tag 后追加", release, re.MULTILINE)
        )
        heading = bool(re.search(r"^#{2,3}.*覆盖对账", release, re.MULTILINE))
        rows = len(re.findall(r"^\|.*(实现|不适用|待首推).*\|$", release, re.MULTILINE))
        g.add(
            "LAYOUT.RELEASE",
            cols and heading and rows >= 3,
            f"两栏:{cols} 覆盖对账小节:{heading} 三态行数:{rows}",
        )
        return
    g.add("LAYOUT.RELEASE", True, "WRAPUP 形态")


def check_release_placeholder(g: Gate) -> None:
    """发布留档里不得残留尖括号版本占位符。

    扫描面 = `plan/RELEASE-M*.md`（**不依赖**里程碑是否 ✅：v0.5.1 的教训是"留档写了、
    里头的提交号没回填"，而当时状态副本已经全 ✅ 了，`LAYOUT.RELEASE` 依然全绿）。
    逐文件逐行找，命中即 FAIL 并点名 `文件:行`。
    """
    paths = sorted(g.root.glob(f"plan/{RELEASE_GLOB}"))
    if not paths:
        g.add(
            "LAYOUT.RELEASE_PLACEHOLDER",
            False,
            f"扫到 0 份 plan/{RELEASE_GLOB}——判据空跑（留档搬走了？）",
        )
        return
    hits: list[str] = []
    for path in paths:
        rel = path.relative_to(g.root).as_posix()
        text = g.read(rel) or ""
        for lineno, line in enumerate(text.splitlines(), start=1):
            m = RELEASE_PLACEHOLDER.search(line)
            if m:
                hits.append(f"{rel}:{lineno} {m.group(0)}")
    g.add(
        "LAYOUT.RELEASE_PLACEHOLDER",
        not hits,
        "；".join(hits) if hits else f"{len(paths)} 份发布留档，0 处版本占位符",
    )


def check_documented_tools(g: Gate, done: list[int]) -> None:
    """文档点名的 tools/ 脚本必须有实物。三个状态：在位 / 待里程碑（显式登记） / 缺失。

    PENDING_TOOLS 是"还没到该里程碑"的显式登记：登记项在所属里程碑翻 ✅ 后必须删除，
    否则本判据变红。当前项目：M0 已把两道门落地，登记表为空。
    """
    exempt: set[str] = set()
    pending_tools: dict[str, int] = {}

    docs = ["AGENTS.md", "README.md"]
    plan_dir = g.root / "plan"
    if plan_dir.is_dir():
        docs += [f"plan/{p.name}" for p in sorted(plan_dir.glob("*.md"))]

    referenced: set[str] = set()
    for rel in docs:
        text = g.read(rel)
        if text is None:
            continue
        referenced.update(re.findall(r"tools/[\w.-]+\.(?:py|mjs|js|cjs|sh|ps1)", text))

    if not referenced:
        g.add(
            "LAYOUT.DOC_TOOLS",
            False,
            f"扫了 {len(docs)} 份文档，0 处 tools/ 引用——判据是空的（阳性对照失败）",
        )
        return

    missing: list[str] = []
    deferred: list[str] = []
    stale: list[str] = []
    for rel in sorted(referenced):
        if (g.root / rel).is_file() or rel in exempt:
            continue
        milestone = pending_tools.get(rel)
        if milestone is None:
            missing.append(rel)
        elif milestone in done:
            stale.append(f"{rel}（M{milestone} 已 ✅，登记项必须清理）")
        else:
            deferred.append(f"{rel}(M{milestone})")

    problems = missing + stale
    detail = f"{len(referenced)} 个文档点名的 tools/ 脚本"
    if problems:
        detail += f"；问题: {', '.join(problems)}"
    elif deferred:
        detail += f"；{len(deferred)} 个待里程碑落位: {', '.join(deferred)}"
    else:
        detail += " 全部在位"
    g.add("LAYOUT.DOC_TOOLS", not problems, detail)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="布局门（方法论装订）")
    parser.add_argument("--root", default=None, help="仓库根目录（默认取本文件的上一级）")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print(f"用法错误：--root 不是目录: {root}", file=sys.stderr)
        return EXIT_USAGE

    g = Gate(root)

    for fn in (check_required_files, check_binding_head, check_sections):
        try:
            fn(g)
        except Exception as exc:  # 永不崩：报一条 FAIL 并继续
            g.add(fn.__name__, False, f"{type(exc).__name__}: {exc}")

    try:
        states, rows_by_copy = collect_states(g)
    except Exception as exc:
        g.add("LAYOUT.STATUS", False, f"{type(exc).__name__}: {exc}")
        states, rows_by_copy = {}, {}

    done = sorted(k for k, v in states.items() if "done" in v)
    all_milestones = sorted(states)

    for fn in (
        lambda: check_status(g, states, rows_by_copy),
        lambda: check_handoffs(g, done, all_milestones),
        lambda: check_gaps(g, done),
        lambda: check_ledger(g, done),
        lambda: check_release(g, done, all_milestones),
        lambda: check_release_placeholder(g),
        lambda: check_documented_tools(g, done),
    ):
        try:
            fn()
        except Exception as exc:
            g.add("LAYOUT.EXCEPTION", False, f"{type(exc).__name__}: {exc}")

    # 非空跑自证：一条文件都没读到时，"全绿"没有意义
    g.add(
        "LAYOUT.GATE_SELFTEST",
        g.read_count > 0,
        f"本轮读文件 {g.read_count} 次（0 = 判据空跑）",
    )

    failed = [c for c in g.checks if not c["ok"]]
    print("布局门（方法论装订） · 判据只落仓库内文件")
    print("=" * 64)
    for c in g.checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['id']}  {c['detail']}")
    print("=" * 64)
    print(f"结论: {'全绿' if not failed else f'{len(failed)} 项 FAIL'}")
    return EXIT_OK if not failed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
