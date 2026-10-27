# -*- coding: utf-8 -*-
"""呈现层：报告装配（人读 + 机读同源）。

**零判定**：本层只吃 `Container` / `Finding`，不 import `readers/`，不推断"应该显示成什么样"。

确定性三条：
  · JSON `sort_keys=True` + 固定 `separators` + `ensure_ascii=False`
  · 集合先排序；不输出浮点（帧时长一律整数 ms）
  · `generated_at` 由调用方传入，默认固定串——**不读时钟**
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from .. import SCHEMA_VERSION, TOOL_NAME, __version__

#: 默认时间戳：固定串，保证双跑逐字节相等（`plan/06` D15）。
DEFAULT_GENERATED_AT = "1970-01-01T00:00:00Z"


def make_header(
    *,
    input_path: str,
    input_size: int,
    input_sha256: str,
    generated_at: str = DEFAULT_GENERATED_AT,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """报告头。路径按**入参原样**输出，不 abspath（否则报告带本机路径，脱敏门会红）。"""
    header: dict[str, Any] = {
        "tool": {"name": TOOL_NAME, "version": __version__},
        "schema": SCHEMA_VERSION,
        "generated_at": generated_at,
        "input": {"path": input_path, "size": input_size, "sha256": input_sha256},
    }
    if extra:
        header.update(extra)
    return header


def summarize(findings: Iterable[dict[str, Any]]) -> dict[str, int]:
    """按 severity 计数。固定键序由输出层的 sort_keys 保证。"""
    counts = {"error": 0, "warning": 0, "info": 0, "unknown": 0, "suspicion": 0}
    for f in findings:
        sev = f.get("severity", "info")
        if sev in counts:
            counts[sev] += 1
    return counts


def render_json(document: dict[str, Any]) -> str:
    """机读输出。**唯一**的 JSON 序列化入口——不要在别处另写一份。"""
    return json.dumps(
        document,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def render_text(document: dict[str, Any]) -> str:
    """人读输出。与 JSON 同源（同一份 document），不额外查询任何东西。"""
    lines: list[str] = []
    tool = document.get("tool", {})
    lines.append(f"{tool.get('name', TOOL_NAME)} {tool.get('version', '?')} · schema {document.get('schema', '?')}")
    inp = document.get("input", {})
    lines.append(f"input: {inp.get('path', '?')} ({inp.get('size', 0)} bytes)")
    lines.append(f"generated_at: {document.get('generated_at', '?')}")
    lines.append("-" * 64)

    findings = document.get("findings", [])
    if not findings:
        lines.append("(no findings)")
    for f in findings:
        conf = f.get("confidence", "")
        loc = f.get("evidence", {}).get("location", {})
        where = loc.get("chunk") or loc.get("carrier") or ""
        offset = loc.get("offset")
        at = f"{where}@{offset}" if where and offset is not None else (where or "")
        lines.append(
            f"[{f.get('severity', '?'):9}] {f.get('code', '?'):32} {at}  (confidence={conf})"
        )
        if f.get("message"):
            lines.append(f"            {f['message']}")
        ev = f.get("evidence") or {}
        if ev.get("spec"):
            lines.append(f"            evidence: {ev['spec']} — {ev.get('quote', '')[:90]}")

    summary = document.get("summary", {})
    lines.append("-" * 64)
    lines.append(" ".join(f"{k}={v}" for k, v in summary.items()))
    return "\n".join(lines)


def selftest_evidence_complete(document: dict[str, Any]) -> list[str]:
    """M6 硬验收：任何没有 `evidence` 的 finding 即判失败。

    返回问题列表（空 = 通过）。**不抛异常**：调用方决定是报错还是打印。
    """
    problems: list[str] = []
    for i, f in enumerate(document.get("findings", [])):
        ev = f.get("evidence")
        if not ev or not ev.get("spec"):
            problems.append(f"findings[{i}] code={f.get('code')!r} 缺 evidence.spec")
            continue
        if not ev.get("quote"):
            problems.append(f"findings[{i}] code={f.get('code')!r} 缺 evidence.quote")
    return problems
