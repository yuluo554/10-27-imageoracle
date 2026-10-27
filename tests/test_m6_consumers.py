# -*- coding: utf-8 -*-
"""M6 的硬验收：`plan/05` §二 M6 出口门逐条对标（consumers 矩阵 + 风险 + 加工 diff）。

五层判据：

1. **台账层**：`specs/` 里 M6 条款原文与 `data/README.md` §1.13 表**逐字**一致；
   §8.9 的矩阵 / 风险 / diff 三张表与 `modules/consumers.py` 的表体逐格一致
   （解析表格对账，不在测试里另抄一份）。
2. **矩阵层**：9 行 × 6 列齐；每行 `evidence.kind ∈ {spec, tool-doc, hn-quote}`；
   `tool-doc` 行有 URL + 原文片段；`confidence ∈ {certain, single-source, gray}`。
3. **风险层**：每条有 `consumer/risk/severity/trigger/confidence/evidence`；severity 走 risk 词表。
4. **diff 层**：≥4 条加工命令，且必须含 `oxipng --strip safe` / `oxipng --strip all` /
   `sharp.rotate()` / `exiftran`；`--strip safe` 的保留集**不含** `gAMA`/`cHRM`。
5. **运行时层**：54 份样本逐个跑真 CLI —— 全部 exit 0（只出 info）、`selftest_evidence_complete` 全绿、
   按字节事实命中对应风险（APNG → `--strip all`；gAMA → `--strip safe`；IFD1 → jpegtran；XMP → sharp）。

诚实口径：全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**。
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

from imageoracle import cli as cli_module  # noqa: E402
from imageoracle import modules  # noqa: E402
from imageoracle.modules import consumers  # noqa: E402
from imageoracle.report import render_json, render_text, selftest_evidence_complete  # noqa: E402
from imageoracle.specs import CLAUSES, known_ids  # noqa: E402

import gen_all  # noqa: E402

DATA_README = ROOT / "data" / "README.md"

#: M6 在 §1.13 里登记的条款（唯一定义处），测试逐字对账
M6_CLAUSE_IDS = {
    "OXIPNG-STRIP-SAFE",
    "OXIPNG-STRIP-ALL",
    "OXIPNG-FIX",
    "SHARP-AUTOORIENT-REMOVE",
    "IMAGEMAGICK-AUTOORIENT-RESET",
    "EXIFTRAN-ROTATE",
    "HN-ORIENTATION-PNG",
    "HN-ICC-RENDER",
    "HN-SOFTWARE-EITHER",
    "HN-COLOR-IGNORED",
    "CONSUMER-MATRIX",
}

#: 出口门点名的四条加工命令（`plan/03` §五 第 3 项）
REQUIRED_COMMANDS = ("oxipng --strip safe", "oxipng --strip all", "sharp.rotate()", "exiftran")


# ─────────────────────────────────────────────────────────────────────────────
# Markdown 表解析（与 test_m5 同一套手法：锚标题行，不在测试里另抄表）
# ─────────────────────────────────────────────────────────────────────────────

def _tables_under(text: str, heading_needle: str) -> list[list[list[str]]]:
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("#") and heading_needle in line),
        None,
    )
    if start is None:
        raise AssertionError(f"data/README.md 里找不到标题: {heading_needle}")
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            if set(line) <= set("|-: "):
                continue        # 表头分隔行 `|---|---|` 不算断表（否则每张表会被切成两半）
            current.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def _table(tables: list[list[list[str]]], *header: str) -> list[list[str]]:
    for table in tables:
        if [cell.strip("`* ") for cell in table[0][: len(header)]] == list(header):
            return table[1:]
    raise AssertionError(f"找不到表头为 {header} 的表；已有表头: {[t[0] for t in tables]}")


def _plain(cell: str) -> str:
    return cell.replace("**", "").replace("`", "").strip()


def _leading(cell: str) -> str:
    """取一格里的首个取值 token（`partial（…）` → `partial`；`**high**` → `high`）。"""
    return re.split(r"[（(；;，,\s]", _plain(cell), maxsplit=1)[0].strip()


# ─────────────────────────────────────────────────────────────────────────────
# 1. 台账层：§1.13 条款逐字
# ─────────────────────────────────────────────────────────────────────────────

class TestClausesMatchDataReadme(unittest.TestCase):
    def test_clause_quotes_equal_readme_table(self) -> None:
        tables = _tables_under(DATA_README.read_text(encoding="utf-8"), "consumers 的条款依据")
        rows = _table(tables, "条款 ID")
        parsed = {row[0].strip("`"): row[1] for row in rows if row and row[0].strip("`") in CLAUSES}
        self.assertEqual(set(parsed), M6_CLAUSE_IDS, f"§1.13 表解析异常: {parsed}")
        for clause_id, quote in parsed.items():
            with self.subTest(clause=clause_id):
                self.assertEqual(
                    CLAUSES[clause_id].quote, _plain(quote), f"{clause_id} 的 quote 与 §1.13 不一致"
                )

    def test_clauses_are_registered_specs(self) -> None:
        for clause_id in M6_CLAUSE_IDS:
            with self.subTest(clause=clause_id):
                self.assertIn(clause_id, known_ids())

    def test_oxipng_safe_retained_set_excludes_gama(self) -> None:
        """`--strip safe` 的保留集原文里**没有** gAMA/cHRM —— 这是 D3 的判据面。"""
        kept = CLAUSES["OXIPNG-STRIP-SAFE"].quote
        self.assertIn("iCCP", kept)
        self.assertNotIn("gAMA", kept)
        self.assertNotIn("cHRM", kept)

    def test_strip_all_warns_about_apng(self) -> None:
        self.assertIn("convert APNGs to standard PNGs", CLAUSES["OXIPNG-STRIP-ALL"].quote)

    def test_fix_does_not_validate_crc(self) -> None:
        self.assertIn("Do not perform checksum validation", CLAUSES["OXIPNG-FIX"].quote)


# ─────────────────────────────────────────────────────────────────────────────
# 2. 矩阵层：§8.9 表 ↔ modules.consumers.MATRIX_ROWS
# ─────────────────────────────────────────────────────────────────────────────

class TestMatrixMatchesDataReadme(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = _tables_under(
            DATA_README.read_text(encoding="utf-8"), "consumers 矩阵、风险清单与加工命令 diff"
        )

    def test_row_order_matches(self) -> None:
        rows = _table(self.tables, "consumer")
        self.assertEqual([row[0].strip("`") for row in rows], list(consumers.CONSUMERS))

    def test_each_cell_matches_table(self) -> None:
        rows = _table(self.tables, "consumer")
        by_name = {row[0].strip("`"): row for row in rows}
        for spec in consumers.MATRIX_ROWS:
            row = by_name[spec["consumer"]]
            with self.subTest(consumer=spec["consumer"]):
                self.assertEqual(row[1], spec["kind"])
                self.assertEqual(_leading(row[2]), spec["applies_orientation"])
                self.assertEqual(_leading(row[3]), spec["applies_icc"])
                self.assertEqual(json.loads(row[4]), list(spec["dropped_chunks"]))
                self.assertEqual(_leading(row[5]), spec["double_rotate_risk"])
                self.assertEqual(_leading(row[6]), spec["frame_duration"])
                self.assertEqual(_leading(row[7]), spec["confidence"])

    def test_evidence_column_names_the_clause(self) -> None:
        rows = _table(self.tables, "consumer")
        by_name = {row[0].strip("`"): row for row in rows}
        for spec in consumers.MATRIX_ROWS:
            cell = by_name[spec["consumer"]][8]
            with self.subTest(consumer=spec["consumer"]):
                self.assertIn(spec["evidence"]["spec"], cell)
                self.assertIn(f"`{spec['evidence']['kind']}`", cell)
                if spec["evidence"]["kind"] == "tool-doc":
                    self.assertIn(spec["evidence"]["url"], cell)


class TestMatrixShape(unittest.TestCase):
    def test_nine_rows_six_columns(self) -> None:
        self.assertEqual(len(consumers.MATRIX_ROWS), 9)
        self.assertEqual(len(consumers.COLUMNS), 5)   # + evidence = 6
        for spec in consumers.MATRIX_ROWS:
            with self.subTest(consumer=spec["consumer"]):
                for column in consumers.COLUMNS:
                    self.assertIn(column, spec, f"{spec['consumer']} 缺列 {column}")
                self.assertIn("evidence", spec)

    def test_values_are_in_vocabulary(self) -> None:
        for spec in consumers.MATRIX_ROWS:
            with self.subTest(consumer=spec["consumer"]):
                for column, allowed in consumers.VALUE_VOCAB.items():
                    self.assertIn(spec[column], allowed, f"{column}={spec[column]!r} 不在词表")
                self.assertIsInstance(spec["dropped_chunks"], list)

    def test_every_row_has_evidence(self) -> None:
        for spec in consumers.MATRIX_ROWS:
            evidence = spec["evidence"]
            with self.subTest(consumer=spec["consumer"]):
                self.assertIn(evidence["kind"], consumers.EVIDENCE_KINDS)
                self.assertTrue(evidence["quote"].strip())
                self.assertIn(evidence["spec"], known_ids(), "evidence.spec 必须是已登记条款（K8）")
                if evidence["kind"] in ("tool-doc", "hn-quote"):
                    self.assertTrue(evidence["url"].startswith("https://"), "tool-doc/hn-quote 必须带 URL")

    def test_tool_doc_rows_have_url_and_excerpt(self) -> None:
        tool_docs = [s for s in consumers.MATRIX_ROWS if s["evidence"]["kind"] == "tool-doc"]
        self.assertGreaterEqual(len(tool_docs), 1, "至少要有一行 tool-doc（否则该形态无实物）")
        for spec in tool_docs:
            with self.subTest(consumer=spec["consumer"]):
                self.assertTrue(spec["evidence"]["url"])
                self.assertGreater(len(spec["evidence"]["quote"]), 10)

    def test_confidence_vocabulary_and_gray_rows(self) -> None:
        gray = [s for s in consumers.MATRIX_ROWS if s["confidence"] == "gray"]
        self.assertGreaterEqual(len(gray), 3, "取不到第一方文档的行必须显式标 gray")
        for spec in consumers.MATRIX_ROWS:
            with self.subTest(consumer=spec["consumer"]):
                self.assertIn(spec["confidence"], consumers.CONFIDENCES)
        for spec in gray:
            unknown_cells = [
                column for column in consumers.COLUMNS
                if spec[column] == "unknown"
            ]
            self.assertGreaterEqual(len(unknown_cells), 2, "gray 行必须有 ≥2 个 unknown 格（§8.9）")


# ─────────────────────────────────────────────────────────────────────────────
# 3. 风险层
# ─────────────────────────────────────────────────────────────────────────────

class TestRisksMatchDataReadme(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = _tables_under(
            DATA_README.read_text(encoding="utf-8"), "consumers 矩阵、风险清单与加工命令 diff"
        )

    def test_risk_rows_match_table(self) -> None:
        rows = _table(self.tables, "#", "consumer")
        self.assertEqual(len(rows), len(consumers.RISKS))
        for row, risk in zip(rows, consumers.RISKS):
            with self.subTest(risk=risk["id"]):
                self.assertEqual(f"R{int(_leading(row[0])):02d}", risk["id"])
                self.assertEqual(row[1].strip("`"), risk["consumer"])
                self.assertEqual(_leading(row[3]), risk["severity"])
                self.assertEqual(_leading(row[4]).strip("`"), risk["trigger"])
                self.assertEqual(_leading(row[5]), risk["confidence"])
                self.assertIn(risk["evidence"]["spec"], row[6])

    def test_risk_shape(self) -> None:
        consumers_in_matrix = set(consumers.CONSUMERS)
        extra_consumers = {"jpegtran", "oxipng"}   # 加工命令侧的工具，不是矩阵行
        for risk in consumers.RISKS:
            with self.subTest(risk=risk["id"]):
                for key in ("consumer", "risk", "severity", "trigger", "confidence", "evidence"):
                    self.assertTrue(risk.get(key), f"缺字段 {key}")
                self.assertIn(risk["consumer"], consumers_in_matrix | extra_consumers)
                self.assertIn(risk["severity"], consumers.RISK_LEVELS)
                self.assertIn(risk["trigger"], consumers.TRIGGERS)
                self.assertIn(risk["confidence"], consumers.CONFIDENCES)
                self.assertIn(risk["evidence"]["spec"], known_ids())

    def test_severity_is_risk_vocabulary_not_finding_vocabulary(self) -> None:
        """风险清单用 high/medium/low/unknown；误用 error/warning 会让"不折进退出码"失守。"""
        for risk in consumers.RISKS:
            with self.subTest(risk=risk["id"]):
                self.assertNotIn(risk["severity"], {"error", "warning", "info", "suspicion"})


# ─────────────────────────────────────────────────────────────────────────────
# 4. 加工命令 diff 层
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessDiffs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = _tables_under(
            DATA_README.read_text(encoding="utf-8"), "consumers 矩阵、风险清单与加工命令 diff"
        )

    def test_at_least_four_commands_including_required(self) -> None:
        self.assertGreaterEqual(len(consumers.PROCESS_DIFFS), 4)
        commands = {diff["command"] for diff in consumers.PROCESS_DIFFS}
        for required in REQUIRED_COMMANDS:
            with self.subTest(command=required):
                self.assertIn(required, commands, f"出口门点名的 {required} 缺席")

    def test_diff_rows_match_table(self) -> None:
        rows = _table(self.tables, "#", "命令")
        self.assertEqual(len(rows), len(consumers.PROCESS_DIFFS))
        for row, diff in zip(rows, consumers.PROCESS_DIFFS):
            with self.subTest(command=diff["command"]):
                first_backtick = re.search(r"`([^`]+)`", row[1])
                self.assertIsNotNone(first_backtick, f"命令格里没有行内代码: {row[1]}")
                self.assertEqual(first_backtick.group(1), diff["command"])
                self.assertIn(diff["evidence"]["spec"], row[5])

    def test_each_diff_declares_losses_and_changes(self) -> None:
        for diff in consumers.PROCESS_DIFFS:
            with self.subTest(command=diff["command"]):
                self.assertIsInstance(diff["loses"], list)
                self.assertIsInstance(diff["keeps"], list)
                self.assertTrue(diff["changes"], "必须给 '哪些字段变'")
                self.assertIn(diff["evidence"]["kind"], consumers.EVIDENCE_KINDS)
                self.assertIn(diff["evidence"]["spec"], known_ids())

    def test_strip_safe_drops_gama_keeps_iccp(self) -> None:
        diff = next(d for d in consumers.PROCESS_DIFFS if d["command"] == "oxipng --strip safe")
        self.assertIn("gAMA", diff["loses"])
        self.assertIn("cHRM", diff["loses"])
        self.assertIn("iCCP", diff["keeps"])
        self.assertNotIn("gAMA", diff["keeps"])

    def test_strip_all_mentions_apng_flattening(self) -> None:
        diff = next(d for d in consumers.PROCESS_DIFFS if d["command"] == "oxipng --strip all")
        self.assertTrue(any("APNG" in change for change in diff["changes"]))


# ─────────────────────────────────────────────────────────────────────────────
# 5. 运行时层：54 份样本逐个跑真 CLI
# ─────────────────────────────────────────────────────────────────────────────

_RUNS: dict[str, tuple[int, dict | None]] = {}


def _runs() -> dict[str, tuple[int, dict | None]]:
    if _RUNS:
        return _RUNS
    with tempfile.TemporaryDirectory() as tmp:
        for name, (data, _triggers) in gen_all.build_all().items():
            path = Path(tmp) / name
            path.write_bytes(data)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                code = cli_module.main(["consumers", "--json", str(path)])
            _RUNS[name] = (code, None if code == 3 else json.loads(buffer.getvalue()))
    return _RUNS


def _payload(name: str) -> dict:
    runs = _runs()
    if name not in runs:
        raise AssertionError(f"缺样本 {name}")
    code, payload = runs[name]
    if code != 0:
        raise AssertionError(f"{name} 预期 exit 0（只出 info），实际 {code}")
    assert payload is not None
    return payload


class TestRuntimeOnAllSamples(unittest.TestCase):
    def test_every_sample_exits_zero_and_passes_selftest(self) -> None:
        for name, (code, payload) in _runs().items():
            with self.subTest(fixture=name):
                self.assertEqual(code, 0, "consumers 只出 info，不应改变退出码")
                self.assertIsNotNone(payload)
                assert payload is not None
                self.assertEqual(selftest_evidence_complete(payload), [])

    def test_matrix_block_is_complete(self) -> None:
        for name, (_code, payload) in _runs().items():
            assert payload is not None
            matrix = payload["matrix"]
            with self.subTest(fixture=name):
                self.assertEqual(matrix["rows"], 9)
                self.assertEqual(matrix["columns"][-1], "evidence")
                self.assertEqual(len(matrix["columns"]), 6)
                self.assertEqual(matrix["snapshot_date"], consumers.SNAPSHOT_DATE)
                self.assertEqual(len(payload["consumers"]), 9)
                self.assertEqual(len(payload["risks"]), len(consumers.RISKS))
                self.assertEqual(len(payload["process_diffs"]), len(consumers.PROCESS_DIFFS))

    def test_findings_reference_known_specs(self) -> None:
        for name, (_code, payload) in _runs().items():
            assert payload is not None
            for finding in payload["findings"]:
                with self.subTest(fixture=name, code=finding["code"]):
                    self.assertIn(finding["evidence"]["spec"], known_ids())
                    self.assertEqual(finding["severity"], "info")

    def test_apng_triggers_strip_all_risk(self) -> None:
        active = _payload("m5_frames_100ms.apng")["matrix"]["active_risks"]
        self.assertIn("R07", active)

    def test_gama_png_triggers_strip_safe_risk(self) -> None:
        active = _payload("m5_png_gama_after_idat.png")["matrix"]["active_risks"]
        self.assertIn("R06", active)

    def test_ifd1_jpeg_triggers_jpegtran_risk(self) -> None:
        active = _payload("m3_ifd1_unsynced.jpg")["matrix"]["active_risks"]
        self.assertIn("R05", active)

    def test_xmp_jpeg_triggers_sharp_risk(self) -> None:
        active = _payload("m3_xmp_residual.jpg")["matrix"]["active_risks"]
        self.assertIn("R02", active)

    def test_png_exif_triggers_chrome_risk(self) -> None:
        active = _payload("m2_orient6_exif.png")["matrix"]["active_risks"]
        self.assertIn("R03", active)

    def test_png_iccp_triggers_safari_risk(self) -> None:
        active = _payload("m4_iccp_srgb_conflict.png")["matrix"]["active_risks"]
        self.assertIn("R04", active)

    def test_gif_does_not_trigger_png_risks(self) -> None:
        risk_ids = _payload("m5_frames_100ms.gif")["matrix"]["active_risks"]
        for png_only in ("R03", "R04", "R06", "R07"):
            with self.subTest(risk=png_only):
                self.assertNotIn(png_only, risk_ids)

    def test_diff_hits_are_file_specific(self) -> None:
        gama = _payload("m5_png_gama_after_idat.png")
        safe = next(f for f in gama["findings"] if f["facts"].get("command") == "oxipng --strip safe")
        self.assertIn("gAMA", safe["facts"]["hits"])

        apng = _payload("m5_frames_100ms.apng")
        strip_all = next(f for f in apng["findings"] if f["facts"].get("command") == "oxipng --strip all")
        self.assertEqual(strip_all["facts"]["hits"], ["all-ancillary"])

    def test_selftest_flag_passes_on_real_cli(self) -> None:
        data, _ = gen_all.build_all()["m5_frames_100ms.apng"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.apng"
            path.write_bytes(data)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                code = cli_module.main(["consumers", "--json", "--selftest-evidence", str(path)])
        self.assertEqual(code, 0, " --selftest-evidence 在 consumers 上必须通过")

    def test_json_is_byte_identical_across_runs(self) -> None:
        payload = _payload("m5_frames_100ms.apng")
        self.assertEqual(render_json(payload), render_json(_payload("m5_frames_100ms.apng")))

    def test_text_output_renders_matrix(self) -> None:
        text = render_text(_payload("m5_frames_100ms.apng"))
        self.assertIn("consumers matrix: 9 rows × 6 columns", text)
        for consumer_name in consumers.CONSUMERS:
            with self.subTest(consumer=consumer_name):
                self.assertIn(consumer_name, text)


class TestSelftestCatchesMissingEvidence(unittest.TestCase):
    """反证：把一行 evidence 拿掉，`selftest_evidence_complete` 必须红（否则判据是空的）。"""

    def _document(self) -> dict:
        return {
            "findings": [],
            "consumers": [dict(row) for row in consumers.MATRIX_ROWS],
            "risks": [dict(risk) for risk in consumers.RISKS],
            "process_diffs": [dict(diff) for diff in consumers.PROCESS_DIFFS],
        }

    def test_clean_document_passes(self) -> None:
        self.assertEqual(selftest_evidence_complete(self._document()), [])

    def test_consumer_row_without_evidence_fails(self) -> None:
        document = self._document()
        document["consumers"][4].pop("evidence")
        self.assertTrue(selftest_evidence_complete(document), "缺 evidence 的行必须被判失败")

    def test_tool_doc_without_url_fails(self) -> None:
        document = self._document()
        sharp_row = next(row for row in document["consumers"] if row["consumer"] == "sharp")
        sharp_row["evidence"].pop("url")
        self.assertTrue(selftest_evidence_complete(document), "tool-doc 缺 URL 必须被判失败")

    def test_bad_confidence_fails(self) -> None:
        document = self._document()
        document["risks"][0]["confidence"] = "probably"
        self.assertTrue(selftest_evidence_complete(document), "confidence 不在词表必须被判失败")


# ─────────────────────────────────────────────────────────────────────────────
# 6. 接线层：IMPLEMENTED / PLANNED / CLI
# ─────────────────────────────────────────────────────────────────────────────

class TestWiring(unittest.TestCase):
    def test_consumers_is_implemented_and_not_planned(self) -> None:
        self.assertIn("consumers", modules.IMPLEMENTED)
        self.assertNotIn("consumers", modules.PLANNED)

    def test_no_planned_modules_left_after_m6(self) -> None:
        self.assertEqual(modules.PLANNED, {}, "M6 之后不应再有占位模块（末棒清空 PLANNED）")

    def test_cli_exposes_consumers_payload_keys(self) -> None:
        payload = _payload("m5_frames_100ms.apng")
        for key in ("matrix", "consumers", "risks", "process_diffs"):
            with self.subTest(key=key):
                self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
