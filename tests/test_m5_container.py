# -*- coding: utf-8 -*-
"""M5 的硬验收：`plan/05` §二 M5 出口门逐条对标 + 跨格式帧时长 + 无误报。

五层判据：

1. **台账层**：`specs/` 里 M5 条款原文与 `data/README.md` §1.12 表**逐字**一致；
   结果码级别与 §8.8 表逐条一致（解析表格对账，不在测试里另抄一份）。
2. **出口门层**：15 份 `m5_*` 样本逐条命中自己的 trigger（PNG 顺序 / CRC / IDAT；
   APNG 数量与序号；WebP ANIM 与 ANMF；GIF disposal；JPEG 段序与 APP14）。
3. **CRC 层**：已知向量 `b"IEND"` → `0xAE426082`；覆盖范围 = chunk type + data（不含 length）。
4. **帧时长层**：GIF / APNG / WebP 三格式的 100 ms 样本归一化后都等于 100 ms；
   错写单位报 `unit_mismatch`（10× / 1×）；APNG `delay_den == 0` 按 100 处理。
5. **无误报层**：M1–M4 的全部样本跑 `container`，不得产生 `error`/`warning`/`unknown`。

诚实口径：全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**。
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

from imageoracle import cli as cli_module  # noqa: E402
from imageoracle.model import Chunk  # noqa: E402
from imageoracle.modules import container  # noqa: E402
from imageoracle.readers import png as png_reader  # noqa: E402
from imageoracle.specs import CLAUSES  # noqa: E402

import gen_all  # noqa: E402
import gen_container  # noqa: E402
from build import (  # noqa: E402
    actl,
    anim_payload,
    anmf_payload,
    build_gif,
    build_png,
    fctl,
    idat,
    ihdr,
    png_chunk,
    riff_chunk,
    riff_webp,
    tiff_with_orientation,
    vp8x,
)
from tests._helpers import run_cli  # noqa: E402

DATA_README = ROOT / "data" / "README.md"
MANIFEST = ROOT / "fixtures" / "manifest.json"

#: M5 在 §1.12 里登记的条款（唯一定义处），测试逐字对账
M5_CLAUSE_IDS = {"JPEG-T81-FRAME", "GIF89A-GCE-SCOPE", "FRAME-UNITS"}


# ─────────────────────────────────────────────────────────────────────────────
# 台账层
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
    def test_clause_quotes_equal_readme_table(self) -> None:
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "容器结构的条款依据")
        parsed = {r[0]: r[1] for r in rows if r and r[0] in CLAUSES}
        self.assertEqual(set(parsed), M5_CLAUSE_IDS, f"§1.12 表解析异常: {parsed}")
        for cid, quote in parsed.items():
            with self.subTest(clause=cid):
                self.assertEqual(CLAUSES[cid].quote, _plain(quote), f"{cid} 的 quote 与 §1.12 不一致")

    def test_crc_clause_excludes_length(self) -> None:
        quote = CLAUSES["PNG3-CRC"].quote
        self.assertIn("including the chunk type field and chunk data fields", quote)

    def test_jpeg_clause_supports_frame_header_order(self) -> None:
        self.assertIn("a frame shall begin with a frame header", CLAUSES["JPEG-T81-FRAME"].quote)

    def test_gif_scope_clause(self) -> None:
        self.assertIn("the first graphic rendering block to follow", CLAUSES["GIF89A-GCE-SCOPE"].quote)


class TestSeverityTableMatchesDataReadme(unittest.TestCase):
    def test_m5_severities_match_readme_8_8(self) -> None:
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "container 检查项（报错级别）")
        declared: dict[str, str] = {}
        for row in rows:
            if len(row) < 3 or not row[2]:
                continue
            cell = _plain(row[2]).strip("`")
            if ":" in cell:
                severity, _, code = cell.partition(":")
                declared[code.strip()] = severity.strip()
        for code, (severity, _confidence) in container.SEVERITY.items():
            with self.subTest(code=code):
                self.assertIn(code, declared, f"{code} 未在 §8.8 表里登记级别")
                self.assertEqual(severity, declared[code], f"{code} 的级别与 §8.8 不一致")


# ─────────────────────────────────────────────────────────────────────────────
# 输出层：内存重生成 → 真 CLI
# ─────────────────────────────────────────────────────────────────────────────

_RUNS: dict[str, tuple[int, dict | None]] = {}


def _runs() -> dict[str, tuple[int, dict | None]]:
    if _RUNS:
        return _RUNS
    with tempfile.TemporaryDirectory() as tmp:
        for name, (data, _triggers) in gen_container.build_all().items():
            path = Path(tmp) / name
            path.write_bytes(data)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                code = cli_module.main(["container", "--json", str(path)])
            _RUNS[name] = (code, None if code == 3 else json.loads(buffer.getvalue()))
    return _RUNS


def _payload(name: str, *, expected_code: int | None = None) -> dict:
    runs = _runs()
    if name not in runs:
        raise AssertionError(f"缺样本 {name}")
    code, payload = runs[name]
    if expected_code is not None and code != expected_code:
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


def _run_bytes(data: bytes, suffix: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"probe{suffix}"
        path.write_bytes(data)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            code = cli_module.main(["container", "--json", str(path)])
    if code == 3:
        raise AssertionError("probe 被判成不可解析")
    return json.loads(buffer.getvalue())


# ─────────────────────────────────────────────────────────────────────────────
# CRC 已知向量（K21）
# ─────────────────────────────────────────────────────────────────────────────

class TestCrcKnownVector(unittest.TestCase):
    def test_iend_crc_vector(self) -> None:
        """`b"IEND"` 的 CRC 应为 `0xAE426082`（`data/README` §1.4）。"""
        self.assertEqual(zlib.crc32(b"IEND") & 0xFFFFFFFF, 0xAE426082)
        iend = Chunk(type="IEND", offset=0, length=0, data_offset=8, crc=None, crc_offset=None, raw_data=b"")
        self.assertEqual(png_reader.compute_crc(iend), 0xAE426082)

    def test_crc_covers_type_and_data_but_not_length(self) -> None:
        """覆盖范围 = chunk type + data；加上 length 会得到另一个值（防"顺手把长度也算进去"）。"""
        chunk = Chunk(
            type="gAMA", offset=0, length=4, data_offset=8, crc=None, crc_offset=None,
            raw_data=b"\x00\x00\xb1\x8f",
        )
        self.assertEqual(png_reader.compute_crc(chunk), zlib.crc32(b"gAMA\x00\x00\xb1\x8f") & 0xFFFFFFFF)
        with_length = zlib.crc32(b"\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f") & 0xFFFFFFFF
        self.assertNotEqual(png_reader.compute_crc(chunk), with_length)


# ─────────────────────────────────────────────────────────────────────────────
# 出口门层：15 份样本逐条对标
# ─────────────────────────────────────────────────────────────────────────────

class TestFixturesAgainstExitGate(unittest.TestCase):
    """`plan/05` §二 M5 出口门 + `HANDOFF-M5.md` §六 DoD 的逐条对标。"""

    def test_each_family_has_at_least_two_samples(self) -> None:
        names = list(gen_container.build_all())
        families = {
            "png": [n for n in names if n.startswith("m5_png_")],
            "apng": [n for n in names if "apng" in n],
            "webp": [n for n in names if n.startswith("m5_webp_")],
            "gif": [n for n in names if n.startswith("m5_gif_")],
            "jpeg": [n for n in names if n.startswith("m5_jpeg_")],
        }
        for family, members in families.items():
            with self.subTest(family=family):
                self.assertGreaterEqual(len(members), 2, f"{family} 族样本少于 2 例: {members}")

    def test_png_chunk_order_hits(self) -> None:
        entry = _find(_payload("m5_png_gama_after_idat.png", expected_code=2), "png_chunk_order")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["chunk"], "gAMA")
        self.assertEqual(entry["facts"]["rule"], "before IDAT")
        self.assertEqual(entry["evidence"]["spec"], "PNG3-T7")

    def test_png_idat_nonconsecutive_hits(self) -> None:
        payload = _payload("m5_png_idat_nonconsecutive.png", expected_code=2)
        entry = _find(payload, "png_idat_nonconsecutive")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["interrupted_by"], "tEXt")
        self.assertIn("Multiple IDAT chunks shall be consecutive", entry["evidence"]["quote"])

    def test_png_crc_mismatch_hits(self) -> None:
        entry = _find(_payload("m5_png_bad_crc.png", expected_code=2), "png_crc_mismatch")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["chunk"], "gAMA")
        self.assertNotEqual(entry["facts"]["stored"], entry["facts"]["computed"])
        self.assertEqual(entry["evidence"]["spec"], "PNG3-CRC")

    def test_png_crc_missing_hits(self) -> None:
        entry = _find(_payload("m5_png_missing_crc.png", expected_code=2), "png_crc_missing")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["chunk"], "IEND")
        self.assertIn("The CRC is always present", entry["evidence"]["quote"])

    def test_apng_num_frames_mismatch_hits(self) -> None:
        entry = _find(_payload("m5_apng_numframes.png", expected_code=2), "apng_num_frames_mismatch")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["declared"], 3)
        self.assertEqual(entry["facts"]["actual"], 2)
        self.assertEqual(entry["evidence"]["spec"], "APNG-SEQ")

    def test_apng_sequence_gap_hits(self) -> None:
        entry = _find(_payload("m5_apng_seq_gap.png", expected_code=2), "apng_sequence_gap")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["sequence"], [0, 3])
        self.assertEqual(entry["facts"]["shared_sequence"], [0, 3, 4])
        self.assertEqual(entry["facts"]["problem"], "gap")
        self.assertIn("no gaps or duplicates", entry["evidence"]["quote"])

    def test_webp_anmf_truncated_hits(self) -> None:
        entry = _find(_payload("m5_webp_anmf_truncated.webp", expected_code=2), "webp_anmf_truncated")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["chunk"], "ANMF")
        self.assertEqual(entry["facts"]["declared"], 4096)
        self.assertEqual(entry["evidence"]["spec"], "WEBP-ANMF")

    def test_webp_anim_structure_hits(self) -> None:
        entry = _find(_payload("m5_webp_anim_loop_swap.webp", expected_code=2), "webp_anim_structure")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["chunk"], "ANIM")
        self.assertEqual(entry["facts"]["size"], 8)
        self.assertEqual(entry["facts"]["expected_size"], 6)
        self.assertEqual(entry["facts"]["fields"], "Background/Loop swapped")
        self.assertEqual(entry["evidence"]["spec"], "WEBP-ANIM")

    def test_gif_disposal_undefined_hits(self) -> None:
        entry = _find(_payload("m5_gif_dispose4.gif", expected_code=1), "gif_disposal_undefined")
        self.assertEqual(entry["severity"], "warning", "disposal 4–7 是 To be defined，不是非法值")
        self.assertEqual(entry["facts"]["disposal"], 4)
        self.assertIn("To be defined", entry["evidence"]["quote"])

    def test_jpeg_segment_order_hits(self) -> None:
        entry = _find(_payload("m5_jpeg_progressive_mixed.jpg", expected_code=2), "jpeg_segment_order")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["before"], "SOS")
        self.assertEqual(entry["facts"]["after"], "SOF2")
        self.assertEqual(entry["evidence"]["spec"], "JPEG-T81-FRAME")

    def test_jpeg_app14_position_hits(self) -> None:
        entry = _find(_payload("m5_jpeg_app14_pos.jpg", expected_code=2), "jpeg_app14_position")
        self.assertEqual(entry["severity"], "error")
        self.assertEqual(entry["facts"]["segment"], "APP14")
        self.assertEqual(entry["facts"]["after"], "SOS")


# ─────────────────────────────────────────────────────────────────────────────
# 帧时长层（K22）
# ─────────────────────────────────────────────────────────────────────────────

class TestFrameDurations(unittest.TestCase):
    def test_three_formats_normalise_to_100ms(self) -> None:
        """出口门：GIF(10) / APNG(10/100) / WebP(100) 归一化后**都等于 100 ms**。"""
        for name, expected_raw in (
            ("m5_frames_100ms.gif", 10),
            ("m5_frames_100ms.apng", 10),
            ("m5_frames_100ms.webp", 100),
        ):
            with self.subTest(fixture=name):
                payload = _payload(name, expected_code=0)
                self.assertTrue(payload["frames"], f"{name} 没有帧")
                for frame in payload["frames"]:
                    self.assertEqual(frame["duration_ms"], 100)
                self.assertEqual(payload["frames"][0]["raw_duration"], expected_raw)
                self.assertNotIn("unit_mismatch", [f["code"] for f in payload["findings"]])

    def test_gif_delay_written_in_ms_reports_unit_mismatch(self) -> None:
        """GIF `delay=100`（1/100 s）→ 1000 ms；按 ms 假读恰为 100 ms → 10× 错。"""
        payload = _payload("m5_gif_delay_ms.gif", expected_code=1)
        entry = _find(payload, "unit_mismatch")
        self.assertEqual(entry["severity"], "warning")
        self.assertEqual(entry["facts"]["raw"], 100)
        self.assertEqual(entry["facts"]["raw_unit"], "1/100s")
        self.assertEqual(entry["facts"]["ms"], 1000)
        self.assertEqual(entry["facts"]["expected_ms"], 100)
        self.assertEqual(entry["facts"]["factor"], 10)
        self.assertEqual(entry["facts"]["scale"], "10x")
        self.assertEqual(entry["evidence"]["spec"], "FRAME-UNITS")

    def test_webp_duration_written_in_centiseconds_reports_unit_mismatch(self) -> None:
        """反向（1×）：WebP duration=10（ms）→ 假读成 1/100 s 恰为 100 ms。"""
        payload = _run_bytes(
            riff_webp(
                [
                    riff_chunk(b"VP8X", vp8x(64, 48, animation=True)),
                    riff_chunk(b"ANIM", anim_payload(0)),
                    riff_chunk(b"ANMF", anmf_payload(duration=10)),
                ]
            ),
            ".webp",
        )
        entry = _find(payload, "unit_mismatch")
        self.assertEqual(entry["facts"]["ms"], 10)
        self.assertEqual(entry["facts"]["scale"], "1/10x")
        self.assertEqual(entry["facts"]["factor"], 10)

    def test_apng_delay_den_zero_is_treated_as_100(self) -> None:
        """`delay_den == 0` 按 100 处理（`data/README` §1.6 / §8.3）→ 10/0 应等于 100 ms。"""
        payload = _run_bytes(
            build_png(
                chunks=[
                    png_chunk("IHDR", ihdr(64, 48)),
                    png_chunk("acTL", actl(1, 0)),
                    png_chunk("fcTL", fctl(0, 64, 48, delay_num=10, delay_den=0)),
                    png_chunk("IDAT", idat()),
                ]
            ),
            ".png",
        )
        self.assertEqual(payload["frames"][0]["duration_ms"], 100)
        self.assertEqual(payload["frames"][0]["raw_den"], 0)
        self.assertNotIn("unit_mismatch", [f["code"] for f in payload["findings"]])

    def test_frames_are_integers_not_floats(self) -> None:
        for name, (_code, payload) in _runs().items():
            if payload is None:
                continue
            for frame in payload["frames"]:
                with self.subTest(fixture=name):
                    self.assertIsInstance(frame["duration_ms"], int)

    def test_frame_findings_follow_report_table(self) -> None:
        """finding 的 facts 与顶层 `frames` 表同源（`ms` ↔ `duration_ms`）。"""
        payload = _payload("m5_frames_100ms.gif")
        entry = _find(payload, "frame_duration_normalized")
        self.assertEqual(entry["facts"]["ms"], payload["frames"][0]["duration_ms"])
        self.assertEqual(entry["facts"]["raw"], payload["frames"][0]["raw_duration"])


# ─────────────────────────────────────────────────────────────────────────────
# manifest 对账 + 无误报
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestTriggersMatchRealOutput(unittest.TestCase):
    def test_manifest_triggers_match_real_output(self) -> None:
        fixtures = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]
        runs = _runs()
        checked = 0
        for name, entry in fixtures.items():
            if not name.startswith("m5_"):
                continue
            _code, payload = runs[name]
            self.assertIsNotNone(payload, f"{name} 无法解析")
            for trigger in entry["triggers"]:
                checked += 1
                with self.subTest(fixture=name, code=trigger["code"]):
                    self._assert_trigger(payload, trigger)
        self.assertEqual(checked, 15, "manifest 里的 M5 trigger 数量异常")

    def _assert_trigger(self, payload: dict, trigger: dict) -> None:
        expected = trigger.get("expected", {})
        code = trigger["code"]
        entry = _find(payload, code)
        if "severity" in expected:
            self.assertEqual(entry["severity"], expected["severity"], f"{code} 的级别不符")
        for key, value in expected.items():
            if key == "severity":
                continue
            if key == "quote":
                self.assertIn(value, entry["evidence"]["quote"], f"{code} 的 evidence.quote 不含 {value!r}")
                continue
            with self.subTest(field=key):
                self.assertEqual(entry["facts"][key], value, f"{code} 的 facts.{key} 不符")


class TestNoFalsePositiveOnGoodSamples(unittest.TestCase):
    """M1–M4 的全部样本跑 `container`：不得出现 error / warning / unknown。"""

    def test_all_other_samples_are_clean(self) -> None:
        offenders: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            for name, (data, _triggers) in gen_all.build_all().items():
                if name.startswith("m5_"):
                    continue
                path = Path(tmp) / name
                path.write_bytes(data)
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                    code = cli_module.main(["container", "--json", str(path)])
                if code == 3:
                    offenders.append(f"{name}: 不可解析")
                    continue
                payload = json.loads(buffer.getvalue())
                for finding in payload["findings"]:
                    if finding["severity"] in {"error", "warning", "unknown"}:
                        offenders.append(f"{name}: {finding['code']} ({finding['severity']})")
        self.assertEqual(offenders, [], f"非 M5 样本在 container 下出现误报: {offenders}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI 面 + 确定性 + evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestCliSurface(unittest.TestCase):
    def test_container_subcommand_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "anim.gif"
            path.write_bytes(build_gif(frames=[(0, 10)]))
            proc = run_cli("container", "--json", str(path))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["command"], "container")
        self.assertEqual(payload["frames"][0]["duration_ms"], 100)
        self.assertEqual(payload["container_facts"]["kind"], "gif")

    def test_selftest_evidence_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "anim.gif"
            path.write_bytes(build_gif(frames=[(0, 10)]))
            proc = run_cli("container", "--json", "--selftest-evidence", str(path))
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_deterministic_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "anim.apng"
            path.write_bytes(gen_container.build_all()["m5_frames_100ms.apng"][0])
            first = run_cli("container", "--json", str(path)).stdout
            second = run_cli("container", "--json", str(path)).stdout
        self.assertEqual(first, second, "同一输入双跑必须逐字节相同")

    def test_every_finding_has_known_spec(self) -> None:
        for name, (_code, payload) in _runs().items():
            if payload is None:
                continue
            for finding in payload["findings"]:
                with self.subTest(fixture=name, code=finding["code"]):
                    self.assertIn(finding["evidence"]["spec"], CLAUSES)
                    self.assertTrue(finding["evidence"]["quote"].strip())
                    self.assertTrue(finding["evidence"]["location"])

    def test_out_of_scope_kind_is_noted_not_silently_passed(self) -> None:
        """TIFF 不在 §四 的容器面内：记 `container.notes` 事实，不假装"检查过了"（也不误报）。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.tif"
            path.write_bytes(tiff_with_orientation(6))
            proc = run_cli("container", "--json", str(path))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["findings"], [])
        self.assertTrue(
            any("not defined for tiff" in note for note in payload["container"]["notes"]),
            payload["container"]["notes"],
        )


if __name__ == "__main__":
    unittest.main()
