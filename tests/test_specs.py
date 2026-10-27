# -*- coding: utf-8 -*-
"""规范条款与证据链（规范贴合度 20 分的机器判据）。

- 每条 clause 的 ID 与字段非空、原文不空
- `orientation` 产出的 finding 的 spec 必须能在 `specs` 里查到
- 关键原文逐字比对（防日后"顺手改写"把证据变成转述）
- 版本号两处一致（`__init__.py` vs `pyproject.toml`）
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

from imageoracle import __version__  # noqa: E402
from imageoracle.specs import CLAUSES, known_ids  # noqa: E402

from build import build_jpeg, tiff_with_orientation  # noqa: E402

from imageoracle.modules.orientation import analyze  # noqa: E402
from imageoracle.readers import read  # noqa: E402


class TestSpecClauses(unittest.TestCase):
    def test_every_clause_is_well_formed(self) -> None:
        self.assertGreater(len(CLAUSES), 0, "条款库不能为空")
        for cid, clause in CLAUSES.items():
            with self.subTest(clause=cid):
                self.assertEqual(clause.id, cid)
                self.assertTrue(clause.title.strip())
                self.assertTrue(clause.quote.strip(), f"{cid} 的 quote 不能为空")
                self.assertTrue(clause.source.strip(), f"{cid} 缺 source")

    def test_orientation_six_cw90_wording(self) -> None:
        """证据里的 6 必须是 `Rotate 90 CW`，8 必须是 `Rotate 270 CW`。"""
        quote = CLAUSES["EXIF-TAG274"].quote
        self.assertIn("6 Rotate 90 CW", quote)
        self.assertIn("8 Rotate 270 CW", quote)

    def test_png_crc_excludes_length(self) -> None:
        """CRC 原文必须写明覆盖 chunk type + data（据此排除 length）。"""
        quote = CLAUSES["PNG3-CRC"].quote
        self.assertIn("including the chunk type field and chunk data fields", quote)
        self.assertIn("preceding bytes", quote)

    def test_iccp_srgb_is_should_not(self) -> None:
        """PNG-3 原文是 should not —— 不得升格为 shall not（否则会把 warning 报成 error）。"""
        quote = CLAUSES["PNG3-ICCP-SRGB"].quote
        self.assertIn("should not", quote)
        self.assertNotIn("shall not be present", quote)

    def test_apng_rules_present(self) -> None:
        quote = CLAUSES["APNG-SEQ"].quote
        for needle in (
            "must contain sequence number 0",
            "no gaps or duplicates",
            "must equal the number of fcTL chunks",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, quote)

    def test_webp_frame_duration_is_ms(self) -> None:
        self.assertIn("1-millisecond units", CLAUSES["WEBP-ANMF"].quote)

    def test_gif_delay_unit(self) -> None:
        quote = CLAUSES["GIF89A-GCE"].quote
        self.assertIn("1/100 second", quote)
        self.assertIn("To be defined", quote)


class TestFindingsCiteKnownSpecs(unittest.TestCase):
    def test_all_findings_use_known_spec_ids(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            cases = {
                "ok.jpg": build_jpeg(exif=tiff_with_orientation(6)),
                "oor.jpg": build_jpeg(exif=tiff_with_orientation(9)),
                "absent.jpg": build_jpeg(),
            }
            for name, data in cases.items():
                path = Path(tmp) / name
                path.write_bytes(data)
                container = read(path)
                result = analyze(container)
                for finding in result["findings"]:
                    with self.subTest(file=name, code=finding["code"]):
                        self.assertIn(finding["evidence"]["spec"], known_ids())


class TestVersionConsistency(unittest.TestCase):
    def test_version_two_places_agree(self) -> None:
        """版本号唯一定义处两处必须一致（`plan/06` D12）。"""
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
        self.assertIsNotNone(m, "pyproject.toml 里找不到 version")
        self.assertEqual(m.group(1), __version__)

    def test_readme_status_shows_version(self) -> None:
        """README 状态行要写出当前版本（读者解包后第一份文档）。"""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"`{__version__}`", readme)


if __name__ == "__main__":
    unittest.main()
