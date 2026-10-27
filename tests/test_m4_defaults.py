# -*- coding: utf-8 -*-
"""M4 硬验收之一：**默认假设表 7 行，逐行带 `source`**（`plan/05` §二 M4 出口门）。

三层判据：

1. **表体层**：`color.DEFAULT_ASSUMPTIONS` 恰好 7 行；每行 `id`/`situation`/`assumed`/`source` 四字段非空；
   `id` 唯一。
2. **台账层**：表的唯一定义处是 `data/README.md` §8.7 —— 测试**解析该表**逐字对账
   （不在测试里另抄一份，与 M2/M3 同款做法）。
3. **报告层**：跑**真 CLI**，`--json` 里 `default_assumptions` 逐行出现且每行带 `source`。

另外守住 D2 的那条纪律：表里不得出现"大家都假设 sRGB"这类**笼统**措辞——
libvips 那行的原文恰恰说"**不**假设 sRGB"，这张表就是为打破这句话而存在的。

诚实口径：全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**。
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

from imageoracle.modules import color  # noqa: E402

import gen_icc  # noqa: E402
from build import build_png  # noqa: E402

DATA_README = ROOT / "data" / "README.md"
SCHEMA_OF_ROW = ("id", "situation", "assumed", "source")
#: D2 纪律：不得用"都/一律"把各软件的不同默认抹平（libvips 那行正是不假设 sRGB）
BANNED_PHRASINGS = ("大家都假设", "都假设", "一律假设")


def _markdown_table(text: str, heading_needle: str) -> list[list[str]]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("#") and heading_needle in line), None)
    if start is None:
        raise AssertionError(f"data/README.md 里找不到标题: {heading_needle}")
    rows: list[list[str]] = []
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        if line.startswith("|") and not set(line) <= set("|-: "):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


class TestDefaultAssumptionTable(unittest.TestCase):
    """表体层 + 台账层（§8.7 是唯一定义处）。"""

    def test_table_has_exactly_seven_rows(self) -> None:
        rows = color.DEFAULT_ASSUMPTIONS
        self.assertEqual(len(rows), 7, f"默认假设表必须是 7 行，实际 {len(rows)}")

    def test_every_row_has_all_four_fields(self) -> None:
        for i, row in enumerate(color.DEFAULT_ASSUMPTIONS):
            with self.subTest(row=i):
                for field in SCHEMA_OF_ROW:
                    self.assertIn(field, row, f"第 {i} 行缺字段 {field}")
                    self.assertTrue(row[field].strip(), f"第 {i} 行的 {field} 为空")

    def test_ids_are_unique(self) -> None:
        ids = [row["id"] for row in color.DEFAULT_ASSUMPTIONS]
        self.assertEqual(len(ids), len(set(ids)), f"默认假设表 id 有重复: {ids}")

    def test_rows_equal_data_readme_8_7(self) -> None:
        """逐行对账 `data/README.md` §8.7（含 source 一栏）。"""
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "默认假设表（**唯一定义处**")
        parsed = {}
        for row in rows:
            if not row or row[0] in {"id", ""}:
                continue
            parsed[row[0]] = {"situation": row[1], "assumed": row[2], "source": row[3]}
        self.assertEqual(len(parsed), 7, f"§8.7 表解析异常: {parsed}")
        self.assertEqual(
            set(parsed),
            {row["id"] for row in color.DEFAULT_ASSUMPTIONS},
            "§8.7 的 id 集合与代码里的表不一致",
        )
        for row in color.DEFAULT_ASSUMPTIONS:
            with self.subTest(row=row["id"]):
                expected = parsed[row["id"]]
                for field in ("situation", "assumed", "source"):
                    self.assertEqual(row[field], expected[field], f"{row['id']} 的 {field} 与 §8.7 不一致")

    def test_no_vague_all_assume_srgb_wording(self) -> None:
        """D2：不得把各软件的不同默认抹平成"大家都假设 sRGB"。"""
        for row in color.DEFAULT_ASSUMPTIONS:
            joined = row["situation"] + row["assumed"]
            for banned in BANNED_PHRASINGS:
                with self.subTest(row=row["id"], banned=banned):
                    self.assertNotIn(banned, joined, f"{row['id']} 用了笼统措辞 {banned!r}（D2）")

    def test_libvips_row_says_not_srgb(self) -> None:
        """第 6 行（libvips）必须写明"**不**假设 sRGB"——这是 D2 的硬证据。"""
        row = next(r for r in color.DEFAULT_ASSUMPTIONS if r["id"] == "libvips-icc-import-missing")
        self.assertIn("不假设 sRGB", row["assumed"])
        # 该行的依据=libvips 原话，条款库里的 ICC-DEFAULTS 逐字取自 §1.11 / §3
        from imageoracle.specs import CLAUSES

        self.assertIn("built-in profiles", CLAUSES["ICC-DEFAULTS"].quote)


class TestDefaultAssumptionInReport(unittest.TestCase):
    """报告层：跑真 CLI，7 行逐行出现且每行带 source。"""

    def _runs(self) -> dict[str, dict]:
        from imageoracle import cli as cli_module

        runs: dict[str, dict] = {}
        with tempfile.TemporaryDirectory() as tmp:
            for name, (data, _triggers) in gen_icc.build_all().items():
                path = Path(tmp) / name
                path.write_bytes(data)
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                    code = cli_module.main(["color", "--json", str(path)])
                if code != 3:
                    runs[name] = json.loads(buffer.getvalue())
        return runs

    def test_seven_rows_appear_in_report(self) -> None:
        runs = self._runs()
        self.assertTrue(runs, "color 族没有产出可解析的样本")
        for name, payload in runs.items():
            with self.subTest(fixture=name):
                rows = payload.get("default_assumptions", [])
                self.assertEqual(len(rows), 7, f"{name}: 报告里默认假设表不是 7 行")
                for row in rows:
                    self.assertTrue(row.get("source", "").strip(), f"{name}: 某行缺 source")

    def test_default_assumption_finding_has_evidence(self) -> None:
        payload = self._runs()["m4_lr0_form.png"]
        entry = next(f for f in payload["findings"] if f["code"] == "color_default_assumption")
        self.assertEqual(entry["severity"], "info")
        self.assertEqual(entry["facts"]["rows"], 7)
        self.assertIn(entry["evidence"]["spec"], color.CODES_SPEC.values())

    def test_lr0_form_facts_reproduce_shape(self) -> None:
        """lr0 形态：iCCP present / sRGB absent / gAMA+cHRM present 三项都出现在 facts 里。"""
        payload = self._runs()["m4_lr0_form.png"]
        entry = next(f for f in payload["findings"] if f["code"] == "color_default_assumption")
        self.assertTrue(entry["facts"]["iccp"])
        self.assertFalse(entry["facts"]["srgb"])
        self.assertTrue(entry["facts"]["gama"])
        self.assertTrue(entry["facts"]["chrm"])

    def test_png_without_color_chunks_reports_absent_markers(self) -> None:
        """反向样本：没有任何色彩 chunk 的 PNG → 四个标记全 False（不是"没报"）。"""
        from imageoracle import cli as cli_module

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.png"
            path.write_bytes(build_png())
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                cli_module.main(["color", "--json", str(path)])
        payload = json.loads(buffer.getvalue())
        entry = next(f for f in payload["findings"] if f["code"] == "color_markers")
        self.assertFalse(entry["facts"]["iccp"])
        self.assertFalse(entry["facts"]["srgb"])
        self.assertFalse(entry["facts"]["gama"])
        self.assertFalse(entry["facts"]["chrm"])


if __name__ == "__main__":
    unittest.main()