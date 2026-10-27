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

    consumers = document.get("consumers") or []
    if consumers:
        matrix = document.get("matrix") or {}
        columns = matrix.get("columns") or []
        lines.append("-" * 64)
        lines.append(
            f"consumers matrix: {matrix.get('rows', len(consumers))} rows × {len(columns) or 6} columns"
            f" · snapshot {matrix.get('snapshot_date', '?')}"
        )
        lines.append(
            f"{'consumer':16} {'orient':9} {'icc':8} {'dbl':8} {'frame':20} {'conf':13} drops"
        )
        for row in consumers:
            drops = ",".join(row.get("dropped_chunks") or []) or "-"
            lines.append(
                f"{row.get('consumer', '?'):16} {row.get('applies_orientation', '?'):9} "
                f"{row.get('applies_icc', '?'):8} {row.get('double_rotate_risk', '?'):8} "
                f"{row.get('frame_duration', '?'):20} {row.get('confidence', '?'):13} {drops}"
            )
        active = matrix.get("active_risks") or []
        lines.append(f"risks applying to this file: {', '.join(active) if active else '(none)'}")

    summary = document.get("summary", {})
    lines.append("-" * 64)
    lines.append(" ".join(f"{k}={v}" for k, v in summary.items()))
    return "\n".join(lines)


def selftest_evidence_complete(document: dict[str, Any]) -> list[str]:
    """M6 硬验收：任何没有 `evidence` 的行即判失败。

    覆盖两个面：

    1. `findings` —— 每条都要 `evidence.spec` + `evidence.quote`（M2–M6 一律适用）；
    2. `consumers` / `risks` / `process_diffs` —— **每行**要有 `evidence`，且
       `kind ∈ {spec, tool-doc, hn-quote}`；`tool-doc` / `hn-quote` 必须带 URL（`plan/03` §五）；
       `consumers` / `risks` 还要 `confidence ∈ {certain, single-source, gray}`。

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

    problems.extend(_rows_evidence_problems(document.get("consumers") or [], "consumers", require_confidence=True))
    problems.extend(_rows_evidence_problems(document.get("risks") or [], "risks", require_confidence=True))
    problems.extend(
        _rows_evidence_problems(document.get("process_diffs") or [], "process_diffs", require_confidence=False)
    )
    return problems


#: 证据形态 / 置信度词表（唯一定义处 `data/README.md` §8.9；呈现层只做形态校验，不查语义）
ROW_EVIDENCE_KINDS = frozenset({"spec", "tool-doc", "hn-quote"})
ROW_CONFIDENCES = frozenset({"certain", "single-source", "gray"})
_URL_EVIDENCE_KINDS = frozenset({"tool-doc", "hn-quote"})


def _rows_evidence_problems(
    rows: list[dict[str, Any]],
    label: str,
    *,
    require_confidence: bool,
) -> list[str]:
    problems: list[str] = []
    for index, row in enumerate(rows):
        marker = row.get("consumer") or row.get("command") or row.get("id") or "?"
        where = f"{label}[{index}] ({marker})"
        evidence = row.get("evidence")
        if not isinstance(evidence, dict) or not evidence:
            problems.append(f"{where} 缺 evidence")
            continue
        kind = evidence.get("kind")
        if kind not in ROW_EVIDENCE_KINDS:
            problems.append(f"{where} evidence.kind={kind!r} 不在 {sorted(ROW_EVIDENCE_KINDS)}")
        if not evidence.get("quote"):
            problems.append(f"{where} 缺 evidence.quote")
        if kind in _URL_EVIDENCE_KINDS and not evidence.get("url"):
            problems.append(f"{where} evidence.kind={kind} 必须带 URL")
        if kind == "spec" and not evidence.get("spec"):
            problems.append(f"{where} evidence.kind=spec 必须带条款 ID")
        if require_confidence and row.get("confidence") not in ROW_CONFIDENCES:
            problems.append(f"{where} confidence={row.get('confidence')!r} 不在 {sorted(ROW_CONFIDENCES)}")
    return problems
