# -*- coding: utf-8 -*-
"""退出码与确定性（工程交付 20 分里最容易被写字面糊弄的两格）。

- 退出码：0/1/2/3 **优先级**逐位断言（3 > 2 > 1 > 0），且"唯一出口"只有一处实现
- 确定性：同一输入双跑 → JSON **逐字节**相等（不出现运行时钟、无浮点、key 有序）
- 只读：跑完全部子命令后源文件 sha256 与 mtime 不变
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

from imageoracle.cli import (  # noqa: E402
    COMMANDS,
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_UNPARSABLE,
    EXIT_WARNING,
    exit_code_for,
)
from imageoracle import modules  # noqa: E402
from imageoracle.report import render_json, selftest_evidence_complete  # noqa: E402

from build import build_jpeg, png_chunk, build_png, tiff_with_orientation  # noqa: E402
from tests._helpers import run_cli  # noqa: E402


def _finding(severity: str) -> dict:
    return {
        "module": "orientation",
        "code": "x",
        "severity": severity,
        "confidence": "certain",
        "message": "m",
        "evidence": {"spec": "EXIF-TAG274", "quote": "q", "location": {"offset": 0}},
    }


class TestExitCodes(unittest.TestCase):
    def test_clean(self) -> None:
        self.assertEqual(exit_code_for([]), EXIT_CLEAN)
        self.assertEqual(exit_code_for([_finding("info")]), EXIT_CLEAN)

    def test_warning(self) -> None:
        self.assertEqual(exit_code_for([_finding("warning")]), EXIT_WARNING)

    def test_error_beats_warning(self) -> None:
        self.assertEqual(
            exit_code_for([_finding("warning"), _finding("error")]), EXIT_ERROR
        )

    def test_unknown_counts_as_error(self) -> None:
        """不可判（unknown）也是 exit 2——不许静默降级成 0。"""
        self.assertEqual(exit_code_for([_finding("unknown")]), EXIT_ERROR)

    def test_unparsable_is_separate(self) -> None:
        """3 不参与判决计数；它与"判决失败"是两个语义。"""
        self.assertEqual(EXIT_UNPARSABLE, 3)
        self.assertNotIn(EXIT_UNPARSABLE, {EXIT_CLEAN, EXIT_WARNING, EXIT_ERROR})

    def test_unparsable_input_returns_three(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bogus = Path(tmp) / "not-an-image.bin"
            bogus.write_bytes(b"this is not an image at all")
            proc = run_cli("orientation", "--json", str(bogus))
            self.assertEqual(proc.returncode, EXIT_UNPARSABLE, proc.stderr)


class TestExitCodeSingleSource(unittest.TestCase):
    def test_exit_code_has_one_definition(self) -> None:
        """`exit_code_for` 只能有一处定义（防两套口径漂移）。"""
        definitions: list[str] = []
        for path in (ROOT / "src").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "exit_code_for":
                    definitions.append(str(path.relative_to(ROOT)))
        self.assertEqual(definitions, ["src\\imageoracle\\cli.py"] if sys.platform == "win32" else ["src/imageoracle/cli.py"])


class TestModuleRegistration(unittest.TestCase):
    """K15：`IMPLEMENTED` / `PLANNED` 必须与 CLI **实际暴露面**一致。

    这条判据是本棒补的实物——`plan/HANDOFF-M3.md` §三.6 点名"登记一致性绿"，
    在该判据存在之前那句话无实物可依（skill：文档点名的判据必须有落点）。
    判据面从**真 CLI**（`build_parser()`）采，而不是从两个 dict 互相比：
    两边同错就恒绿，等于没判据。
    """

    def test_registry_matches_parser_surface(self) -> None:
        import argparse

        from imageoracle.cli import build_parser

        parser = build_parser()
        subparsers = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        exposed = set(subparsers.choices)
        self.assertEqual(
            exposed,
            set(modules.IMPLEMENTED) | set(modules.PLANNED),
            "CLI 暴露的命令面与 IMPLEMENTED|PLANNED 登记不符",
        )

    def test_implemented_and_planned_are_disjoint(self) -> None:
        overlap = set(modules.IMPLEMENTED) & set(modules.PLANNED)
        self.assertEqual(overlap, set(), f"同一模块同时登记在两表: {overlap}")

    def test_registry_covers_all_commands(self) -> None:
        self.assertEqual(
            set(modules.IMPLEMENTED) | set(modules.PLANNED),
            set(COMMANDS),
            "`cli.COMMANDS` 与模块登记表不同步",
        )

    def test_planned_modules_raise_not_implemented(self) -> None:
        """登记在 `PLANNED` 的模块必须确实抛 `NotImplementedError`（不许'看着像有'）。

        M6 之后 `PLANNED` 为空（五个模块全部落地），本循环退化为空跑——**这不是判据**，
        而是"占位面"的守门器；末棒状态由下面两条显式断言（`test_no_planned_modules_left`）。
        """
        from imageoracle.model import Container

        dummy = Container(kind="jpeg", path="x", size=0)
        for name, (milestone, doc) in modules.PLANNED.items():
            with self.subTest(module=name):
                self.assertRegex(milestone, r"^M\d+$")
                self.assertTrue(doc.strip(), f"{name} 的契约位置为空")
                module = __import__(f"imageoracle.modules.{name.replace('-', '_')}", fromlist=["analyze"])
                with self.assertRaises(NotImplementedError):
                    module.analyze(dummy)

    def test_double_rotate_is_wired(self) -> None:
        """M3 出口：`double-rotate` 在 `IMPLEMENTED` 里，且**不在** `PLANNED` 里。"""
        self.assertIn("double-rotate", modules.IMPLEMENTED)
        self.assertNotIn("double-rotate", modules.PLANNED)

    def test_consumers_is_wired(self) -> None:
        """M6 出口：`consumers` 在 `IMPLEMENTED` 里，且**不在** `PLANNED` 里。"""
        self.assertIn("consumers", modules.IMPLEMENTED)
        self.assertNotIn("consumers", modules.PLANNED)

    def test_no_planned_modules_left(self) -> None:
        """末棒：`PLANNED` 必须为空——留着占位就是"文档说没做完"。"""
        self.assertEqual(modules.PLANNED, {})


class TestDeterminism(unittest.TestCase):
    def test_json_is_byte_identical_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.jpg"
            path.write_bytes(
                build_jpeg(exif=tiff_with_orientation(6, width=64, height=48))
            )
            first = _run(path)
            second = _run(path)
            self.assertEqual(
                first,
                second,
                "同一输入双跑输出必须逐字节相同（不得读时钟、不得有集合顺序抖动）",
            )

    def test_json_has_no_floats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.jpg"
            path.write_bytes(build_jpeg(exif=tiff_with_orientation(6)))
            payload = json.loads(_run(path))
            self.assert_has_no_floats(payload)

    def assert_has_no_floats(self, node, path: str = "$") -> None:
        if isinstance(node, float):
            self.fail(f"{path} 是浮点（统计量一律整数/定点）")
        if isinstance(node, dict):
            for k, v in node.items():
                self.assert_has_no_floats(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                self.assert_has_no_floats(v, f"{path}[{i}]")

    def test_generated_at_default_is_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.jpg"
            path.write_bytes(build_jpeg(exif=tiff_with_orientation(6)))
            payload = json.loads(_run(path))
            self.assertEqual(payload["generated_at"], "1970-01-01T00:00:00Z")


class TestReadOnly(unittest.TestCase):
    def test_source_file_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.jpg"
            data = build_jpeg(exif=tiff_with_orientation(6))
            path.write_bytes(data)
            before_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            before_mtime = path.stat().st_mtime_ns
            _run(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before_hash)
            self.assertEqual(path.stat().st_mtime_ns, before_mtime)

    def test_out_dir_does_not_touch_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.jpg"
            data = build_jpeg(exif=tiff_with_orientation(6))
            path.write_bytes(data)
            out = Path(tmp) / "reports"
            run_cli("orientation", "--json", "--out", str(out), str(path))
            self.assertEqual(path.read_bytes(), data, "源文件被写回了")
            self.assertTrue((out / "a.jpg.json").is_file(), "--out 没有写出报告")


class TestEvidenceContract(unittest.TestCase):
    def test_missing_evidence_is_detected(self) -> None:
        document = {"findings": [{"code": "x", "severity": "error"}]}
        self.assertTrue(selftest_evidence_complete(document))

    def test_complete_evidence_passes(self) -> None:
        document = {"findings": [_finding("error")]}
        self.assertEqual(selftest_evidence_complete(document), [])

    def test_every_real_finding_has_evidence(self) -> None:
        """真实运行产出的每条 finding 都必须带 evidence.spec + quote。"""
        with tempfile.TemporaryDirectory() as tmp:
            for name, data in (
                ("ok.jpg", build_jpeg(exif=tiff_with_orientation(6))),
                ("oor.jpg", build_jpeg(exif=tiff_with_orientation(9))),
                ("absent.jpg", build_jpeg()),
                ("ok.png", build_png(before_idat=[png_chunk("eXIf", tiff_with_orientation(6))])),
            ):
                path = Path(tmp) / name
                path.write_bytes(data)
                payload = json.loads(_run(path))
                with self.subTest(file=name):
                    self.assertEqual(selftest_evidence_complete(payload), [])


def _run(path: Path) -> str:
    proc = run_cli("orientation", "--json", str(path))
    if proc.returncode == 3:
        raise AssertionError(f"输入不可解析: {proc.stderr}")
    return proc.stdout


class TestRenderJson(unittest.TestCase):
    def test_render_is_stable(self) -> None:
        doc = {"b": 1, "a": [3, 2, 1], "c": {"z": 1, "y": 2}}
        self.assertEqual(render_json(doc), render_json(dict(reversed(list(doc.items())))))


if __name__ == "__main__":
    unittest.main()
