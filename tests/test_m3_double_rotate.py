# -*- coding: utf-8 -*-
"""M3 的硬验收：三条件逐条命中 + `certain`/`heuristic` **分列** + 无误报。

四层判据（对应 `plan/05` §二 M3 出口门 + `plan/HANDOFF-M3.md` §六 DoD）：

1. **台账层**：`specs/` 里的 M3 条款原文与 `data/README.md` §1.10 表**逐字**一致
   （解析表格对账，不在测试里另抄一份——M2 的 `TestWordingMatchesDataReadme` 同款做法）。
2. **样本层**：`fixtures/gen_double_rotate.py` 的内存产出写到临时目录，跑**真 CLI**，
   逐条断言条件号 / 级别 / 关键字段 / 退出码。**不读 `fixtures/out/`**（产物不入仓）。
3. **分列层**：`certain` 与 `heuristic` 不得混算——条件 3 只准出现在 `heuristic`，
   且它的 `severity` 必须是 `suspicion`、`confidence` 必须是 `gray-heuristic`（`plan/00` R4）。
4. **无误报层**：M2 的 22 份好样本在 `double-rotate` 下**不得产生 `certain`**（出口门硬项）。

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

from imageoracle.modules import double_rotate  # noqa: E402
from imageoracle.specs import CLAUSES  # noqa: E402

import gen_double_rotate  # noqa: E402
import gen_orientation  # noqa: E402
from tests._helpers import run_cli  # noqa: E402

DATA_README = ROOT / "data" / "README.md"
MANIFEST = ROOT / "fixtures" / "manifest.json"


# ─────────────────────────────────────────────────────────────────────────────
# 台账层：条款原文必须与 data/README §1.10 逐字一致
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
    """`data/README` §1.10 是 M3 条款原文的**唯一定义处**；这里是机器化对账。"""

    def test_clause_quotes_equal_readme_table(self) -> None:
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "双重旋转的软件侧依据")
        parsed = {r[0]: _plain(r[1]) for r in rows if r and r[0] in CLAUSES}
        self.assertEqual(
            set(parsed),
            {"SHARP-AUTOORIENT", "JPEGTRAN-COPYALL", "IMAGEMAGICK-AUTOORIENT", "GRAY-DECODE-REQUIRED"},
            f"§1.10 表解析异常: {parsed}",
        )
        for cid, quote in parsed.items():
            with self.subTest(clause=cid):
                self.assertEqual(CLAUSES[cid].quote, quote, f"{cid} 的 quote 与 data/README §1.10 不一致")

    def test_english_quotes_also_appear_in_section_3(self) -> None:
        """三条英文原话必须也在第 3 节（工具原文）出现——防"只在 §1.10 顺手改写"。"""
        text = DATA_README.read_text(encoding="utf-8")
        for cid in ("SHARP-AUTOORIENT", "JPEGTRAN-COPYALL", "IMAGEMAGICK-AUTOORIENT"):
            with self.subTest(clause=cid):
                self.assertIn(_plain(CLAUSES[cid].quote), text)

    def test_conditions_and_levels_match_readme_8_6(self) -> None:
        """三个条件的 confidence / severity 与 §8.6 的表逐字一致。"""
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "三条件、级别与启发式阈值")
        parsed = {}
        for row in rows:
            if not row or not row[0].isdigit():
                continue
            parsed[int(row[0])] = (_plain(row[2]).strip("`"), _plain(row[3]).strip("`"))
        self.assertEqual(set(parsed), {1, 2, 3}, f"§8.6 表解析异常: {parsed}")
        for number, (confidence, severity) in parsed.items():
            with self.subTest(condition=number):
                self.assertEqual(double_rotate.CONDITION_CONFIDENCE[number], confidence)
                self.assertEqual(double_rotate.CONDITION_SEVERITY[number], severity)


# ─────────────────────────────────────────────────────────────────────────────
# 样本层：内存重生成 → 真 CLI
# ─────────────────────────────────────────────────────────────────────────────

_M3_RUNS: dict[str, tuple[int, dict | None]] = {}
_M2_RUNS: dict[str, tuple[int, dict | None]] = {}


def _run_family(names: dict, cache: dict[str, tuple[int, dict | None]], command: str) -> dict[str, tuple[int, dict | None]]:
    if cache:
        return cache
    from imageoracle import cli as cli_module

    with tempfile.TemporaryDirectory() as tmp:
        for name, (data, _triggers) in names.items():
            path = Path(tmp) / name
            path.write_bytes(data)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                code = cli_module.main([command, "--json", str(path)])
            cache[name] = (code, None if code == 3 else json.loads(buffer.getvalue()))
    return cache


def _m3_runs() -> dict[str, tuple[int, dict | None]]:
    return _run_family(gen_double_rotate.build_all(), _M3_RUNS, "double-rotate")


def _m2_runs() -> dict[str, tuple[int, dict | None]]:
    return _run_family(gen_orientation.build_all(), _M2_RUNS, "double-rotate")


class TestFixturesAgainstExitGate(unittest.TestCase):
    """`plan/05` §二 M3 出口门 + `HANDOFF-M3.md` §六 DoD 的逐条对标。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.runs = _m3_runs()

    def _payload(self, name: str, *, expected_code: int | None = None) -> dict:
        self.assertIn(name, self.runs, f"缺样本 {name}")
        code, payload = self.runs[name]
        if expected_code is not None:
            self.assertEqual(code, expected_code, f"{name} 预期 exit {expected_code}，实际 {code}")
        self.assertNotEqual(code, 3, f"{name} 被判成不可解析")
        assert payload is not None
        return payload

    def test_condition_1_ifd1_unsynced(self) -> None:
        """DoD #1：`jpegtran -copy all` 形态（IFD1 未同步）→ 条件 1 + `certain`。"""
        payload = self._payload("m3_ifd1_unsynced.jpg")
        self.assertIn(1, payload["condition_hits"])
        entry = next(e for e in payload["certain"] if e["condition"] == 1)
        self.assertEqual(entry["code"], "double_rotate_ifd1_unsynced")
        self.assertEqual(entry["confidence"], "certain")
        self.assertEqual(entry["severity"], "warning")
        self.assertEqual(entry["facts"]["exif.ifd0.orientation"], 6)
        self.assertEqual(entry["facts"]["exif.ifd1.orientation"], 1)
        self.assertEqual(entry["evidence"]["spec"], "EXIF-TAG274")

    def test_condition_2_xmp_residual(self) -> None:
        """DoD #2：`sharp #4585` 形态（EXIF 归 1、XMP 仍 6）→ 条件 2 + `certain`。"""
        payload = self._payload("m3_xmp_residual.jpg")
        self.assertIn(2, payload["condition_hits"])
        entry = next(e for e in payload["certain"] if e["condition"] == 2)
        self.assertEqual(entry["code"], "double_rotate_xmp_conflict")
        self.assertEqual(entry["confidence"], "certain")
        self.assertEqual(entry["facts"]["exif.ifd0.orientation"], 1)
        self.assertEqual(entry["facts"]["xmp.tiff:Orientation"], 6)

    def test_condition_3_bigedge_is_suspicion_only(self) -> None:
        """DoD #3：大边启发式命中，**只出 `suspicion`** + `gray-heuristic`，`certain` 为空。"""
        payload = self._payload("m3_bigedge_mismatch.jpg", expected_code=0)
        self.assertEqual(payload["condition_hits"], [3])
        self.assertEqual(payload["certain"], [], "条件 3 绝不准出现在 certain 列表里")
        self.assertEqual(len(payload["heuristic"]), 1)
        entry = payload["heuristic"][0]
        self.assertEqual(entry["code"], "double_rotate_bigedge_mismatch")
        self.assertEqual(entry["confidence"], "gray-heuristic")
        self.assertEqual(entry["severity"], "suspicion")
        self.assertEqual(entry["facts"]["stored"], [80, 40])
        self.assertEqual(entry["evidence"]["spec"], "GRAY-DECODE-REQUIRED")

    def test_certain_and_heuristic_are_separate_fields(self) -> None:
        """DoD #4：输出结构齐；`certain` / `heuristic` 各自成字段，不混进一个分数。"""
        payload = self._payload("m3_ifd1_unsynced.jpg")
        for key in ("condition_hits", "certain", "heuristic", "verdicts"):
            with self.subTest(key=key):
                self.assertIn(key, payload)
        certain_conditions = {e["condition"] for e in payload["certain"]}
        heuristic_conditions = {e["condition"] for e in payload["heuristic"]}
        self.assertEqual(certain_conditions & heuristic_conditions, set(), "两列表出现了同一个条件")
        for entry in payload["certain"]:
            self.assertEqual(entry["confidence"], "certain")
        for entry in payload["heuristic"]:
            self.assertNotEqual(entry["confidence"], "certain")

    def test_verdicts_carry_consumer_trigger_chain_consequence_evidence(self) -> None:
        """DoD #5：每条 verdict 给"软件 × 触发链" + 后果 + 依据。"""
        payload = self._payload("m3_xmp_residual.jpg")
        self.assertTrue(payload["verdicts"], "命中了却没有 verdict")
        consumers = {v["consumer"] for v in payload["verdicts"]}
        self.assertIn("sharp.autoOrient()", consumers)
        for verdict in payload["verdicts"]:
            with self.subTest(consumer=verdict["consumer"]):
                for key in ("consumer", "trigger_chain", "consequence", "evidence"):
                    self.assertTrue(verdict.get(key), f"verdict 缺 {key}")
                spec = verdict["evidence"]["spec"]
                self.assertIn(spec, CLAUSES, f"verdict 引用了未知条款 {spec}")
                self.assertTrue(verdict["evidence"]["quote"].strip())

    def test_three_consumers_are_covered(self) -> None:
        """三个软件例（sharp / jpegtran / ImageMagick）在命中时都要出现。"""
        consumers = {v["consumer"] for v in self._payload("m3_ifd1_unsynced.jpg")["verdicts"]}
        consumers |= {v["consumer"] for v in self._payload("m3_xmp_residual.jpg")["verdicts"]}
        for expected in ("sharp.autoOrient()", "jpegtran -copy all -rotate 90", "ImageMagick -auto-orient"):
            with self.subTest(consumer=expected):
                self.assertIn(expected, consumers)

    def test_manifest_triggers_match_real_output(self) -> None:
        """M1 冻结真值 → M3 判决：manifest 里每条 `m3_*` 的 expected 都要在真输出里找到对应。"""
        fixtures = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]
        checked = 0
        for name, entry in fixtures.items():
            if not name.startswith("m3_"):
                continue
            _code, payload = self.runs[name]
            assert payload is not None, f"{name} 无法解析"
            for trigger in entry["triggers"]:
                checked += 1
                with self.subTest(fixture=name, code=trigger["code"]):
                    self._assert_trigger(payload, trigger)
        self.assertGreaterEqual(checked, 3, "manifest 里的 M3 trigger 数量异常")

    def _assert_trigger(self, payload: dict, trigger: dict) -> None:
        expected = trigger.get("expected", {})
        code = trigger["code"]
        entry = next(
            (e for e in payload["certain"] + payload["heuristic"] if e["code"] == code),
            None,
        )
        self.assertIsNotNone(entry, f"真输出里没有 {code}: hits={payload['condition_hits']}")
        assert entry is not None
        self.assertEqual(entry["condition"], expected["condition"])
        self.assertEqual(entry["confidence"], expected["confidence"])
        if "severity" in expected:
            self.assertEqual(entry["severity"], expected["severity"])
        for key, value in expected.items():
            if key in {"condition", "confidence", "severity"}:
                continue
            with self.subTest(field=key):
                self.assertEqual(entry["facts"][key], value)

    def test_exit_codes_follow_severity(self) -> None:
        """条件 1/2 是 `warning` → exit 1；条件 3 的 `suspicion` 不影响退出码（§8.5）。"""
        self.assertEqual(self.runs["m3_ifd1_unsynced.jpg"][0], 1)
        self.assertEqual(self.runs["m3_xmp_residual.jpg"][0], 1)
        self.assertEqual(self.runs["m3_bigedge_mismatch.jpg"][0], 0, "suspicion 不得让退出码非 0")


class TestNoFalseCertainOnGoodSamples(unittest.TestCase):
    """出口门硬项：M2 的 22 份好样本在 `double-rotate` 下**不得产生 `certain`**。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.runs = _m2_runs()

    def test_no_certain_on_m2_samples(self) -> None:
        offenders = []
        for name, (code, payload) in self.runs.items():
            assert payload is not None, f"{name} 无法解析"
            for entry in payload["certain"]:
                offenders.append(f"{name}: {entry['code']}")
        self.assertEqual(offenders, [], f"M2 好样本上出现 certain（误报）: {offenders}")

    def test_error_samples_keep_exit_2(self) -> None:
        """基线 findings 必须带出来：越界/类型错在 `double-rotate` 下仍是 exit 2（不许被降级）。"""
        for name, want_code in (
            ("m2_orient0_oor.jpg", "orientation_out_of_range"),
            ("m2_orient9_oor.jpg", "orientation_out_of_range"),
            ("m2_orient6_wrongtype.jpg", "orientation_not_int16u"),
        ):
            with self.subTest(fixture=name):
                code, payload = self.runs[name]
                self.assertEqual(code, 2, f"{name} 的 error 被静默丢了")
                assert payload is not None
                self.assertIn(want_code, [f["code"] for f in payload["findings"]])

    def test_absent_sample_stays_clean(self) -> None:
        """`absent` ≠ 1（K3）：无方向的样本不得因此被当成冲突。"""
        code, payload = self.runs["m2_absent.jpg"]
        self.assertEqual(code, 0)
        assert payload is not None
        self.assertEqual(payload["condition_hits"], [])
        self.assertEqual(payload["certain"], [])


class TestConditionBoundaries(unittest.TestCase):
    """两个边界的就地反证：合成字节 → 真 CLI，防止日后"顺手放宽"把好样本判成冲突。"""

    def _run(self, name: str, data: bytes) -> tuple[int, dict]:
        from imageoracle import cli as cli_module

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_bytes(data)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                code = cli_module.main(["double-rotate", "--json", str(path)])
        return code, json.loads(buffer.getvalue())

    def test_ifd1_absent_is_not_condition_1(self) -> None:
        """只有 IFD0 有 274、IFD1 没有 → 不是"不一致"（要求两者都存在）。"""
        from build import build_jpeg, tiff_with_orientation

        data = build_jpeg(width=64, height=48, exif=tiff_with_orientation(6, width=64, height=48))
        _code, payload = self._run("ifd1_absent.jpg", data)
        self.assertNotIn(1, payload["condition_hits"])
        self.assertEqual(payload["certain"], [])

    def test_xmp_missing_with_exif_six_is_not_condition_2(self) -> None:
        """EXIF=6 且**没有** XMP → 不得判成条件 2（否则最常见的正常照片全被误判）。"""
        from build import build_jpeg, tiff_with_orientation

        data = build_jpeg(width=64, height=48, exif=tiff_with_orientation(6, width=64, height=48))
        _code, payload = self._run("exif_only.jpg", data)
        self.assertNotIn(2, payload["condition_hits"])

    def test_condition_3_not_evaluated_for_values_1_to_4(self) -> None:
        """1–4 不涉及 90° 旋转 → 不评估条件 3（宽>高的竖构图也不得命中）。"""
        from build import build_jpeg, tiff_with_orientation

        for value in (1, 2, 3, 4):
            with self.subTest(value=value):
                data = build_jpeg(width=64, height=48, exif=tiff_with_orientation(value, width=64, height=48))
                _code, payload = self._run(f"orient{value}.jpg", data)
                self.assertNotIn(3, payload["condition_hits"])

    def test_portrait_stored_size_is_not_condition_3(self) -> None:
        """声明 6 且存储**高>宽**（已纵向）→ 不命中（判据是"宽 > 高"）。"""
        from build import build_jpeg, tiff_with_orientation

        data = build_jpeg(width=48, height=64, exif=tiff_with_orientation(6, width=48, height=64))
        _code, payload = self._run("portrait.jpg", data)
        self.assertNotIn(3, payload["condition_hits"])


class TestCliSurface(unittest.TestCase):
    """CLI 面：可跑、`--json` 自洽、退出码与 severity 一致。"""

    def test_cli_runs_and_matches_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m3.jpg"
            path.write_bytes(gen_double_rotate.build_all()["m3_xmp_residual.jpg"][0])
            proc = run_cli("double-rotate", "--json", str(path))
        self.assertEqual(proc.returncode, 1, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "double-rotate")
        self.assertEqual(payload["condition_hits"], [2])
        self.assertEqual(payload["summary"]["warning"], 1)

    def test_selftest_evidence_passes(self) -> None:
        """`--selftest-evidence`：每条 finding 都带 evidence（M6 硬项的前哨）。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m3.jpg"
            path.write_bytes(gen_double_rotate.build_all()["m3_ifd1_unsynced.jpg"][0])
            proc = run_cli("double-rotate", "--json", "--selftest-evidence", str(path))
        self.assertNotEqual(proc.returncode, 2, proc.stderr)


if __name__ == "__main__":
    unittest.main()