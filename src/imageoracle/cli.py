# -*- coding: utf-8 -*-
"""CLI：子命令分派 + **退出码唯一出口**。

退出码口径（`data/README.md` §8.5）：
  0 无 warning / error（可能有 info）
  1 存在 warning
  2 存在 error，或存在 unknown（不可判项）
  3 输入不可解析（不是"判决失败"，是"读不了"）

规则：`exit_code_for()` 是**唯一**实现。任何子命令都只调它，不得自己 `sys.exit(数字)`。
优先级 3 > 2 > 1 > 0；3 不参与判决计数（`plan/03` §0.3）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION, TOOL_NAME, __version__
from . import modules
from .readers import UnsupportedFormat, read as read_container
from .report import (
    DEFAULT_GENERATED_AT,
    make_header,
    render_json,
    render_text,
    selftest_evidence_complete,
    summarize,
)

EXIT_CLEAN = 0
EXIT_WARNING = 1
EXIT_ERROR = 2
EXIT_UNPARSABLE = 3

#: 命令面（`--json` 统一；未实现的子命令不注册，见 modules.PLANNED）
COMMANDS = ("orientation", "double-rotate", "color", "container", "consumers")


def exit_code_for(findings: list[dict[str, Any]]) -> int:
    """**退出码唯一出口**。优先级 3 > 2 > 1 > 0（3 由调用方直接返回，不在 findings 里）。"""
    severities = {f.get("severity") for f in findings}
    if "error" in severities or "unknown" in severities:
        return EXIT_ERROR
    if "warning" in severities:
        return EXIT_WARNING
    return EXIT_CLEAN


def _resolve_generated_at(value: str | None) -> str:
    """不读时钟：显式参数 > SOURCE_DATE_EPOCH > 固定默认串。"""
    if value:
        return value
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        # 由 epoch 秒转 ISO-8601 UTC（纯算术，不用 datetime.now）
        import datetime as _dt

        return _dt.datetime.fromtimestamp(int(epoch), tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return DEFAULT_GENERATED_AT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="图像呈现预言机：只读字节，预言各软件会把它显示成什么样。",
        epilog="退出码：0 无风险 / 1 有 warning / 2 有 error 或不可判 / 3 输入不可解析",
    )
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {__version__} (schema {SCHEMA_VERSION})")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    for name in modules.IMPLEMENTED:
        p = sub.add_parser(name, help=_help_for(name))
        _add_common_args(p)

    # 未实现的子命令：**显式拒绝**并给出里程碑，而不是"未知命令"
    for name, (milestone, doc) in modules.PLANNED.items():
        p = sub.add_parser(name, help=f"（未实现，计划于 {milestone}）")
        _add_common_args(p)

    return parser


def _help_for(name: str) -> str:
    return {
        "orientation": "读取 EXIF/XMP 方向并给出 8 元变换矩阵与有效宽高",
        "double-rotate": "预言会被转两次的组合（IFD1 不同步 / XMP 残留 / 大边启发式）",
        "color": "ICC 体检 + 色彩标记 + 位深 + CMYK，并列出无 profile 时的默认假设表",
        "container": "校验 PNG/APNG/WebP/GIF/JPEG 的容器结构，并把帧时长归一化到整数 ms",
        "consumers": "给出 9 个消费者的方向/ICC/丢 chunk/双重旋转/帧时长矩阵 + 加工命令 diff",
    }.get(name, name)


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("files", nargs="+", metavar="FILE", help="输入文件（只读）")
    p.add_argument("--json", action="store_true", help="输出机读 JSON（默认人读）")
    p.add_argument("--out", metavar="DIR", help="把报告写到该目录（不写回源文件）")
    p.add_argument("--generated-at", metavar="ISO8601", help=f"报告时间戳（默认 {DEFAULT_GENERATED_AT}）")
    p.add_argument("--selftest-evidence", action="store_true", help="额外断言每条 finding 都带 evidence")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return EXIT_CLEAN

    if args.command in modules.PLANNED:
        milestone, doc = modules.PLANNED[args.command]
        print(
            f"imageoracle: 子命令 {args.command!r} 尚未实现（计划于 {milestone}）。契约见 {doc}",
            file=sys.stderr,
        )
        return EXIT_UNPARSABLE

    module = modules.IMPLEMENTED[args.command]
    generated_at = _resolve_generated_at(args.generated_at)

    worst = EXIT_CLEAN
    for raw_path in args.files:
        code, payload = _run_one(module, args.command, raw_path, generated_at, args)
        worst = max(worst, code) if code != EXIT_UNPARSABLE else EXIT_UNPARSABLE
        if payload is None:
            continue
        text = render_json(payload) if args.json else render_text(payload)
        if args.out:
            out_dir = Path(args.out)
            out_dir.mkdir(parents=True, exist_ok=True)
            stem = Path(raw_path).name
            suffix = ".json" if args.json else ".txt"
            (out_dir / f"{stem}{suffix}").write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
    return worst


def _run_one(module, command: str, raw_path: str, generated_at: str, args) -> tuple[int, dict[str, Any] | None]:
    path = Path(raw_path)
    try:
        container = read_container(path)
    except FileNotFoundError:
        print(f"imageoracle: 输入不可解析: {raw_path}: file not found", file=sys.stderr)
        return EXIT_UNPARSABLE, None
    except (UnsupportedFormat, ValueError) as exc:
        print(f"imageoracle: 输入不可解析: {raw_path}: {exc}", file=sys.stderr)
        return EXIT_UNPARSABLE, None

    result = module.analyze(container)  # type: ignore[attr-defined]
    findings = result.get("findings", [])

    payload: dict[str, Any] = make_header(
        input_path=raw_path,
        input_size=container.size,
        input_sha256=_sha256(container.path),
        generated_at=generated_at,
        extra={
            "command": command,
            "container": {
                "kind": container.kind,
                "image_info": _image_info_dict(container),
                "notes": sorted(container.notes),
            },
        },
    )
    payload["findings"] = findings
    payload["summary"] = summarize(findings)

    if command == "orientation":
        payload["sources"] = result.get("sources", [])
        payload["primary"] = result.get("primary")
        payload["effective_size"] = result.get("effective_size")

    if command == "double-rotate":
        payload["condition_hits"] = result.get("condition_hits", [])
        payload["certain"] = result.get("certain", [])
        payload["heuristic"] = result.get("heuristic", [])
        payload["verdicts"] = result.get("verdicts", [])
        payload["sources"] = result.get("sources", [])
        payload["primary"] = result.get("primary")
        payload["effective_size"] = result.get("effective_size")

    if command == "color":
        payload["icc"] = result.get("icc")
        payload["color_markers"] = result.get("color_markers")
        payload["default_assumptions"] = result.get("default_assumptions", [])

    if command == "container":
        payload["frames"] = result.get("frames", [])
        payload["container_facts"] = result.get("container_facts")

    if command == "consumers":
        payload["matrix"] = result.get("matrix")
        payload["consumers"] = result.get("consumers", [])
        payload["risks"] = result.get("risks", [])
        payload["process_diffs"] = result.get("process_diffs", [])

    if args.selftest_evidence:
        problems = selftest_evidence_complete(payload)
        if problems:
            for problem in problems:
                print(f"imageoracle: evidence 缺失: {problem}", file=sys.stderr)
            return EXIT_ERROR, payload

    return exit_code_for(findings), payload


def _image_info_dict(container) -> dict[str, Any] | None:
    info = container.image_info
    if info is None:
        return None
    return {
        "width": info.width,
        "height": info.height,
        "bit_depth": info.bit_depth,
        "color_type": info.color_type,
        "precision": info.precision,
        "progressive": info.progressive,
    }


def _sha256(path: str) -> str:
    """读一次源文件算摘要（独立句柄，不影响容器解析的只读语义）。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


if __name__ == "__main__":
    sys.exit(main())
