# -*- coding: utf-8 -*-
"""M4 的硬验收：`plan/05` §二 M4 出口门逐条对标 + 双承载行为 + 无误报。

五层判据：

1. **台账层**：`specs/` 里的 M4 条款原文与 `data/README.md` §1.11 表**逐字**一致
   （解析表格对账，不在测试里另抄一份）。
2. **出口门层**：lr0 形态复现（`iCCP present` / `sRGB absent` / `gAMA`,`cHRM`）；
   三类损坏（截断 / `size` 错 / `acsp` 坏）各命中（`plan/05` §二）。
3. **R5 双行为层**：同一类损坏的 PNG 侧走 `unknown: compressed_profile_not_inspected`、
   JPEG APP2 孪生侧走 `error` —— **两条行为都有样本证明**（"范围限定"不退化成"漏实现"）。
4. **级别层**：`iccp_srgb_conflict` / `cmyk_jpeg` 是 `warning`（不升格 error）；`icc_missing` 是 `info`。
5. **无误报层**：M2 的 22 份好样本整族跑 `color`，不得产生 `error`/`warning`。

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
from imageoracle.specs import CLAUSES  # noqa: E402

import gen_icc  # noqa: E402
import gen_orientation  # noqa: E402
from tests._helpers import run_cli  # noqa: E402

DATA_README = ROOT / "data" / "README.md"
MANIFEST = ROOT / "fixtures" / "manifest.json"

#: M4 在 §1.11 里登记的条款（唯一定义处），测试逐字对账
M4_CLAUSE_IDS = {
    "ICC-CARRIERS",
    "ICC-NOT-INSPECTED",
    "ICC-DEFAULTS",
    "CMYK-APP14",
    "PNG-COLOR-CHUNKS",
    "COLOR-BITDEPTH",
}


# ─────────────────────────────────────────────────────────────────────────────
# 台账层：条款原文必须与 data/README §1.11 逐字一致
# ─────────────────────────────────────────────────────────────────────────────

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


def _plain(cell: str) -> str:
    return cell.replace("**", "").strip()


class TestClausesMatchDataReadme(unittest.TestCase):
    """`data/README` §1.11 是 M4 条款原文的**唯一定义处**；这里是机器化对账。"""

    def test_clause_quotes_equal_readme_table(self) -> None:
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "色彩体检的条款依据")
        parsed = {r[0]: r[1] for r in rows if r and r[0] in CLAUSES}
        self.assertEqual(set(parsed), M4_CLAUSE_IDS, f"§1.11 表解析异常: {parsed}")
        for cid, quote in parsed.items():
            with self.subTest(clause=cid):
                self.assertEqual(CLAUSES[cid].quote, _plain(quote), f"{cid} 的 quote 与 §1.11 不一致")

    def test_iccp_srgb_clause_stays_should_not(self) -> None:
        """`iccp_srgb_conflict` 引的条款原文必须是 should not（不得升格成 shall）。"""
        clause = CLAUSES["PNG3-ICCP-SRGB"]
        self.assertIn("should not", clause.quote)
        self.assertEqual(
            color.SEVERITY["iccp_srgb_conflict"][0], "warning",
            "should not 只能报 warning（data/README §1.5）",
        )

    def test_icc_defaults_clause_also_in_original_sections(self) -> None:
        """libvips / @amiantos 原话必须也在 §3 / §4.2 出现——防"只在 §1.11 顺手改写"。"""
        text = DATA_README.read_text(encoding="utf-8")
        self.assertIn(CLAUSES["ICC-DEFAULTS"].quote, text)
        self.assertIn(CLAUSES["CMYK-APP14"].quote, text)


class TestSeverityTableMatchesDataReadme(unittest.TestCase):
    def test_m4_severities_match_readme_8_2(self) -> None:
        """M4 每个结果码的 severity 与 `data/README` §8.2 表逐条一致。"""
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "ICC 校验项（报错级别）")
        declared: dict[str, str] = {}
        for row in rows:
            if len(row) < 3 or not row[2]:
                continue
            # 第三列形如 `error: icc_size_mismatch` / `info: color_markers`
            cell = _plain(row[2]).strip("`")
            if ":" in cell:
                sev, _, code = cell.partition(":")
                declared[code.strip()] = sev.strip()
        for code, (severity, _confidence) in color.SEVERITY.items():
            with self.subTest(code=code):
                self.assertIn(code, declared, f"{code} 未在 §8.2 表里登记级别")
                self.assertEqual(severity, declared[code], f"{code} 的级别与 §8.2 不一致")


# ─────────────────────────────────────────────────────────────────────────────
# 输出层：内存重生成 → 真 CLI
# ─────────────────────────────────────────────────────────────────────────────

_RUNS: dict[str, tuple[int, dict | None]] = {}


def _runs() -> dict[str, tuple[int, dict | None]]:
    if _RUNS:
        return _RUNS
    from imageoracle import cli as cli_module

    with tempfile.TemporaryDirectory() as tmp:
        for name, (data, _triggers) in gen_icc.build_all().items():
            path = Path(tmp) / name
            path.write_bytes(data)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                code = cli_module.main(["color", "--json", str(path)])
            _RUNS[name] = (code, None if code == 3 else json.loads(buffer.getvalue()))
    return _RUNS


def _payload(name: str, *, expected_code: int | None = None) -> dict:
    runs = _runs()
    if name not in runs:
        raise AssertionError(f"缺样本 {name}")
    code, payload = runs[name]
    if expected_code is not None:
        if code != expected_code:
            raise AssertionError(f"{name} 预期 exit {expected_code}，实际 {code}")
    if code == 3:
        raise AssertionError(f"{name} 被判成不可解析")
    assert payload is not None
    return payload


def _find(payload: dict, code: str) -> dict:
    for finding in payload["findings"]:
        if finding["code"] == code:
            return finding
    raise AssertionError(f"输出里没有 {code}: {[f['code'] for f in payload['findings']]}")


# ─────────────────────────────────────────────────────────────────────────────
# 出口门层：lr0 形态 + 三类损坏
# ─────────────────────────────────────────────────────────────────────────────

class TestFixturesAgainstExitGate(unittest.TestCase):
    """`plan/05` §二 M4 出口门 + `HANDOFF-M4.md` §六 DoD 的逐条对标。"""

    def test_lr0_form_reproduced(self) -> None:
        """出口门 #1：lr0 形态复现 —— `iCCP present` / `sRGB absent` / `gAMA`,`cHRM` 有无。"""
        payload = _payload("m4_lr0_form.png")
        markers = _find(payload, "color_markers")
        facts = markers["facts"]
        self.assertTrue(facts["iccp"], "lr0 形态必须有 iCCP")
        self.assertFalse(facts["srgb"], "lr0 形态必须无 sRGB")
        self.assertTrue(facts["gama"], "lr0 形态必须有 gAMA")
        self.assertTrue(facts["chrm"], "lr0 形态必须有 cHRM")
        self.assertGreater(facts["iccp_length"], 0)
        self.assertEqual(markers["severity"], "info")

    def test_lr0_icc_present_message_shape(self) -> None:
        """`iCCP present (len=N)` 的形态必须在报告里出现（题目原文要求）。"""
        payload = _payload("m4_lr0_form.png")
        markers = _find(payload, "color_markers")
        self.assertIn(f"iCCP present (len={markers['facts']['iccp_length']})", markers["message"])
        self.assertIn("sRGB absent", markers["message"])

    def test_three_damage_classes_hit_on_jpeg_app2(self) -> None:
        """出口门 #2：截断 / `size` 错 / `acsp` 坏三类**各命中**（JPEG APP2 侧）。"""
        cases = {
            "m4_icc_truncated.jpg": ("icc_header_truncated", {"length": 100}),
            "m4_icc_size_bad.jpg": ("icc_size_mismatch", {"declared": 2000, "actual": 1500}),
            "m4_icc_acsp_bad.jpg": ("icc_bad_signature", {"signature": "acsq"}),
        }
        for name, (code, facts) in cases.items():
            with self.subTest(fixture=name):
                payload = _payload(name, expected_code=2)
                entry = _find(payload, code)
                self.assertEqual(entry["severity"], "error")
                for key, value in facts.items():
                    self.assertEqual(entry["facts"][key], value)
                self.assertEqual(entry["evidence"]["spec"], "ICC-HEAD")

    def test_ok_sample_is_fully_legal(self) -> None:
        """反向：`m4_icc_ok.jpg` 的 128B 头全字段合法 → 无 error/warning，且 `inspected=True`。"""
        payload = _payload("m4_icc_ok.jpg", expected_code=0)
        header = payload["icc"]["header"]
        self.assertIsNotNone(header)
        self.assertEqual(header["ProfileFileSignature"], "acsp")
        self.assertEqual(header["ProfileSize"], 256)
        self.assertEqual(header["ProfileClass"], "mntr")
        self.assertEqual(header["ColorSpaceData"], "RGB ")
        self.assertEqual(header["ProfileConnectionSpace"], "XYZ ")
        self.assertEqual(header["RenderingIntent"], 0)
        self.assertEqual(payload["summary"]["error"], 0)
        self.assertEqual(payload["summary"]["warning"], 0)


# ─────────────────────────────────────────────────────────────────────────────
# R5 双行为层：PNG 走 unknown / JPEG 孪生走 error
# ─────────────────────────────────────────────────────────────────────────────

class TestDoubleCarrierBehaviour(unittest.TestCase):
    """R5：同一类损坏 PNG 侧只证明 `unknown`、JPEG APP2 侧才证明 `error`。两条都要有样本。"""

    def test_three_damage_classes_hit_on_png_as_unknown(self) -> None:
        for name in ("m4_icc_truncated.png", "m4_icc_size_bad.png", "m4_icc_acsp_bad.png"):
            with self.subTest(fixture=name):
                payload = _payload(name, expected_code=2)
                entry = _find(payload, "compressed_profile_not_inspected")
                self.assertEqual(entry["severity"], "unknown")
                self.assertEqual(entry["confidence"], "gray")
                self.assertEqual(entry["facts"]["carrier"], "iCCP")
                self.assertIsNone(payload["icc"]["header"], "PNG iCCP 不解压 → 头不得被解析")
                self.assertFalse(payload["icc"]["inspected"])
                for error_code in ("icc_header_truncated", "icc_size_mismatch", "icc_bad_signature"):
                    self.assertNotIn(error_code, [f["code"] for f in payload["findings"]])

    def test_jpeg_twins_do_not_report_not_inspected(self) -> None:
        """JPEG 孪生样本**不得**报 `compressed_profile_not_inspected`（它没有压缩流）。"""
        for name in ("m4_icc_truncated.jpg", "m4_icc_size_bad.jpg", "m4_icc_acsp_bad.jpg", "m4_icc_ok.jpg"):
            with self.subTest(fixture=name):
                payload = _payload(name)
                self.assertNotIn(
                    "compressed_profile_not_inspected",
                    [f["code"] for f in payload["findings"]],
                )

    def test_unknown_counts_as_exit_2(self) -> None:
        """`unknown` 计入退出码 2（`data/README` §8.5）：PNG 侧虽只是"不解压"也必须 exit 2。"""
        self.assertEqual(_runs()["m4_icc_ok.png"][0], 2)
        self.assertEqual(_runs()["m4_icc_ok.jpg"][0], 0)

    def test_both_behaviours_present_in_one_family(self) -> None:
        """R5 的形式判据：`unknown` 与 `error` 两条行为在 M4 族里**都**有样本证明。"""
        runs = _runs()
        severities = {
            f["severity"]
            for _code, payload in runs.values()
            if payload is not None
            for f in payload["findings"]
        }
        self.assertIn("unknown", severities, "没有任何样本证明 unknown 行为")
        self.assertIn("error", severities, "没有任何样本证明 error 行为")


# ─────────────────────────────────────────────────────────────────────────────
# 级别层：warning 不升格 / info 不降级
# ─────────────────────────────────────────────────────────────────────────────

class TestSeverityDiscipline(unittest.TestCase):
    def test_iccp_srgb_conflict_is_warning(self) -> None:
        """PNG-3 原文是 should not → warning，**不得**升格为 error（§1.5）。

        退出码是 2 而非 1：该样本的 `iCCP` 是压缩流 → 另有 `unknown`（§8.5：unknown 计入 2，
        优先级 2 > 1）。冲突本身仍是 `warning`，`error` 计数为 0。
        """
        payload = _payload("m4_iccp_srgb_conflict.png", expected_code=2)
        entry = _find(payload, "iccp_srgb_conflict")
        self.assertEqual(entry["severity"], "warning")
        self.assertEqual(entry["facts"]["quote_says"], "should not")
        self.assertEqual(entry["evidence"]["spec"], "PNG3-ICCP-SRGB")
        self.assertEqual(payload["summary"]["error"], 0)
        self.assertEqual(payload["summary"]["warning"], 1)
        self.assertEqual(payload["summary"]["unknown"], 1)

    def test_cmyk_jpeg_is_warning(self) -> None:
        """CMYK JPEG → warning（需求依据 @amiantos 原话在 evidence 里，不作技术依据）。"""
        payload = _payload("m4_cmyk_app14.jpg", expected_code=1)
        entry = _find(payload, "cmyk_jpeg")
        self.assertEqual(entry["severity"], "warning")
        self.assertEqual(entry["facts"]["components"], 4)
        self.assertEqual(entry["facts"]["app14_transform"], 0)
        self.assertEqual(entry["evidence"]["spec"], "CMYK-APP14")
        self.assertEqual(payload["summary"]["error"], 0)

    def test_icc_missing_is_info_not_error(self) -> None:
        """无 ICC 是 `info`（不是 error）：它是"必须列默认假设表"的触发条件（§8.2）。"""
        payload = _payload("m4_cmyk_app14.jpg")
        entry = _find(payload, "icc_missing")
        self.assertEqual(entry["severity"], "info")
        self.assertFalse(payload["icc"]["present"])

    def test_bit_depth_reported_for_jpeg_and_png(self) -> None:
        """位深三支：JPEG SOF / PNG IHDR 读到即报 info。"""
        self.assertEqual(_find(_payload("m4_icc_ok.jpg"), "color_bit_depth")["facts"]["bit_depth"], 8)
        self.assertEqual(_find(_payload("m4_icc_ok.png"), "color_bit_depth")["facts"]["bit_depth"], 8)

    def test_bit_depth_unknown_for_webp(self) -> None:
        """WebP 位深需解包才读到 → `unknown`（§8.4 第 2 条）。"""
        entry = _find(self._run_webp(), "color_bit_depth_unknown")
        self.assertEqual(entry["severity"], "unknown")
        self.assertEqual(entry["facts"]["format"], "webp")

    def _run_webp(self) -> dict:
        from imageoracle import cli as cli_module
        from build import riff_webp, vp8x

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.webp"
            path.write_bytes(riff_webp([vp8x(64, 48)]))
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                cli_module.main(["color", "--json", str(path)])
        return json.loads(buffer.getvalue())


class TestIccCarriers(unittest.TestCase):
    """载体面：APP2 多段拼接连续性（正/反两支）+ TIFF tag 34675（§8.2 #1 / §1.11）。"""

    def test_multi_segment_is_joined_and_clean(self) -> None:
        """2 段 APP2、段号 1/2 连续 → 拼接成功，且**不得**报 `icc_segment_gap`。"""
        payload = _payload("m4_icc_multi_segment.jpg", expected_code=0)
        present = _find(payload, "icc_present")
        self.assertEqual(present["facts"]["segments"], 2)
        self.assertEqual(present["facts"]["profile_length"], 300)
        self.assertNotIn("icc_segment_gap", [f["code"] for f in payload["findings"]])
        self.assertTrue(payload["icc"]["inspected"])

    def test_segment_gap_is_error(self) -> None:
        """声明 3 段却只有 seq=1,3 → `error: icc_segment_gap`（顺序：present 之后再报 gap）。"""
        payload = _payload("m4_icc_segment_gap.jpg", expected_code=2)
        entry = _find(payload, "icc_segment_gap")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["segments"], 2)
        self.assertEqual(entry["facts"]["seq"], [1, 3])
        self.assertEqual(entry["facts"]["declared_totals"], [3])
        codes = [f["code"] for f in payload["findings"]]
        self.assertLess(codes.index("icc_present"), codes.index("icc_segment_gap"))

    def test_tiff_tag_34675_carrier(self) -> None:
        """TIFF tag 34675 是四种载体之一：必须被读到并解析头。

        退出码是 2：位深在 TIFF 上需读 BitsPerSample/解包（不在首期三支范围内）→ `unknown`。
        载体与头字段本身都正常（`summary.error == 0`）。
        """
        payload = _payload("m4_icc_tiff34675.tif", expected_code=2)
        present = _find(payload, "icc_present")
        self.assertEqual(present["facts"]["carrier"], "tag34675")
        self.assertEqual(payload["icc"]["header"]["ProfileFileSignature"], "acsp")
        self.assertEqual(payload["summary"]["error"], 0)

    def test_icc_missing_reports_info(self) -> None:
        """无载体 → `info: icc_missing`（不是 error），且逐条列出四种载体名。"""
        payload = _payload("m4_cmyk_app14.jpg")
        entry = _find(payload, "icc_missing")
        self.assertEqual(entry["severity"], "info")
        for carrier in ("APP2", "iCCP", "ICCP", "34675"):
            with self.subTest(carrier=carrier):
                self.assertIn(carrier, entry["message"])


class TestRiskField(unittest.TestCase):
    """确定性纪律：`risk: high/medium/low/unknown` + 依据，**绝不出色值**（`plan/03` §三）。"""

    def test_risk_present_and_in_domain(self) -> None:
        allowed = {"high", "medium", "low", "unknown"}
        for name, (_code, payload) in _runs().items():
            if payload is None:
                continue
            for finding in payload["findings"]:
                with self.subTest(fixture=name, code=finding["code"]):
                    self.assertIn(finding.get("risk"), allowed)

    def test_risk_follows_severity_mapping(self) -> None:
        """`risk` 只由 severity 决定（映射唯一实现在 `color.RISK_BY_SEVERITY`）。"""
        for name, (_code, payload) in _runs().items():
            if payload is None:
                continue
            for finding in payload["findings"]:
                with self.subTest(fixture=name, code=finding["code"]):
                    self.assertEqual(finding["risk"], color.RISK_BY_SEVERITY[finding["severity"]])

    def test_no_colour_values_in_output(self) -> None:
        """绝不出具体色值：整套输出里不得出现 `#rgb` / `rgb(` 这类色值形态。"""
        import re

        pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(")
        for name, (_code, payload) in _runs().items():
            if payload is None:
                continue
            text = json.dumps(payload, ensure_ascii=False)
            with self.subTest(fixture=name):
                self.assertIsNone(pattern.search(text), "输出里出现了色值（本工具绝不出色值）")

    def test_error_samples_are_high_risk(self) -> None:
        payload = _payload("m4_icc_acsp_bad.jpg")
        self.assertEqual(_find(payload, "icc_bad_signature")["risk"], "high")

    def test_unknown_samples_are_unknown_risk(self) -> None:
        """不解压 → risk 必须 `unknown`（风险不可估，不假装为零）。"""
        payload = _payload("m4_icc_ok.png")
        self.assertEqual(_find(payload, "compressed_profile_not_inspected")["risk"], "unknown")


class TestEvidenceComplete(unittest.TestCase):
    def test_every_finding_has_known_spec(self) -> None:
        for name, (_code, payload) in _runs().items():
            if payload is None:
                continue
            for finding in payload["findings"]:
                with self.subTest(fixture=name, code=finding["code"]):
                    self.assertIn(finding["evidence"]["spec"], CLAUSES)
                    self.assertTrue(finding["evidence"]["quote"].strip())
                    self.assertTrue(finding["evidence"]["location"])


# ─────────────────────────────────────────────────────────────────────────────
# manifest 对账 + 无误报
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestTriggersMatchRealOutput(unittest.TestCase):
    """M1 冻结真值 → M4 判决：manifest 里每条 `m4_*` 的 expected 都要在真输出里找到。"""

    def test_manifest_triggers_match_real_output(self) -> None:
        fixtures = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]
        runs = _runs()
        checked = 0
        for name, entry in fixtures.items():
            if not name.startswith("m4_"):
                continue
            _code, payload = runs[name]
            self.assertIsNotNone(payload, f"{name} 无法解析")
            for trigger in entry["triggers"]:
                checked += 1
                with self.subTest(fixture=name, code=trigger["code"]):
                    self._assert_trigger(payload, trigger)
        self.assertGreaterEqual(checked, 11, "manifest 里的 M4 trigger 数量异常")

    def _assert_trigger(self, payload: dict, trigger: dict) -> None:
        expected = trigger.get("expected", {})
        code = trigger["code"]
        entry = _find(payload, code)
        if "severity" in expected:
            self.assertEqual(entry["severity"], expected["severity"], f"{code} 的级别不符")
        for key, value in expected.items():
            if key in {"severity", "quote_says"}:
                continue
            with self.subTest(field=key):
                self.assertEqual(entry["facts"][key], value, f"{code} 的 facts.{key} 不符")


class TestNoFalsePositiveOnGoodSamples(unittest.TestCase):
    """出口门纪律：M2 的 22 份好样本整族跑 `color`，不得产生 error/warning。"""

    def test_good_samples_are_clean_or_info_only(self) -> None:
        from imageoracle import cli as cli_module

        offenders: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            for name, (data, _triggers) in gen_orientation.build_all().items():
                # 越界 / 类型错样本本身是 error（属于 M2 语义），排除它们
                if "oor" in name or "wrongtype" in name:
                    continue
                path = Path(tmp) / name
                path.write_bytes(data)
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                    code = cli_module.main(["color", "--json", str(path)])
                payload = json.loads(buffer.getvalue())
                for finding in payload["findings"]:
                    if finding["severity"] in {"error", "warning"}:
                        offenders.append(f"{name}: {finding['code']}")
        self.assertEqual(offenders, [], f"M2 好样本在 color 下出现误报: {offenders}")


class TestCliSurface(unittest.TestCase):
    def test_color_subcommand_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m4.jpg"
            path.write_bytes(gen_icc.build_all()["m4_icc_ok.jpg"][0])
            proc = run_cli("color", "--json", str(path))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "color")
        self.assertEqual(len(payload["default_assumptions"]), 7)

    def test_selftest_evidence_passes(self) -> None:
        """`--selftest-evidence`：每条 finding 都带 evidence（M6 硬项的前哨）。

        用 `m4_icc_ok.jpg`（无 `unknown`/`error`/`warning`，干净样本）：任何非 0 退出码
        都只可能来自 `--selftest-evidence` 报出的 evidence 缺失（它返回 EXIT_ERROR）。
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m4.jpg"
            path.write_bytes(gen_icc.build_all()["m4_icc_ok.jpg"][0])
            proc = run_cli("color", "--json", "--selftest-evidence", str(path))
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_deterministic_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m4.png"
            path.write_bytes(gen_icc.build_all()["m4_lr0_form.png"][0])
            first = run_cli("color", "--json", str(path)).stdout
            second = run_cli("color", "--json", str(path)).stdout
        self.assertEqual(first, second, "同一输入双跑必须逐字节相同")


if __name__ == "__main__":
    unittest.main()