# -*- coding: utf-8 -*-
"""M2 的硬验收：8 元变换矩阵 + **6 = 顺时针 90°** + 22 份样本逐条命中。

三层判据（对应 `plan/05` §二 M2 出口门 + `plan/HANDOFF-M2.md` §六 DoD）：

1. **单元层**：矩阵 / label / 有效宽高与 `data/README.md` §1.1、§8.1 **逐字**一致
   （label 直接解析 README 表格，不在测试里另抄一份）。
2. **样本层**：`fixtures/gen_orientation.py` 的内存产出写到临时目录，跑真 CLI，
   逐条断言 `primary` / 来源 `label` / `transform` / `effective_size` / 退出码。
   **测试不读 `fixtures/out/`**（产物不入仓）：样本在内存里重生成（`plan/HANDOFF-M2.md` §二.2）。
3. **台账层**：`fixtures/manifest.json` 里每条 `m2_*` 的 `triggers[].expected`
   都能在真输出里找到对应——把 M1 冻结真值与 M2 判决对账。

最易搞反的一点（`plan/00` D1）：6 是 `Rotate 90 CW` = **顺时针** 90°，不是逆时针。
断言文案直接引用 ExifTool 原文，防止日后被"改反"——如果有人把矩阵改成 6→270，
失败信息会直接告诉维护者 ExifTool 是怎么写的。
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

from imageoracle.modules.orientation import (  # noqa: E402
    ORIENTATION_LABELS,
    ORIENTATION_MATRIX,
    effective_size,
    transform_for,
)

import gen_orientation  # noqa: E402
from build import build_jpeg, xmp_packet  # noqa: E402
from tests._helpers import run_cli  # noqa: E402

DATA_README = ROOT / "data" / "README.md"
MANIFEST = ROOT / "fixtures" / "manifest.json"

#: `data/README.md` §8.1 的**独立**副本（生成侧/生产侧各一份，一致性靠测试，别顺手统一）
EXPECTED = {
    1: (False, False, 0, False),
    2: (True, False, 0, False),
    3: (False, False, 180, False),
    4: (False, True, 0, False),
    5: (True, False, 270, True),
    6: (False, False, 90, True),
    7: (True, False, 90, True),
    8: (False, False, 270, True),
}


class TestMatrix(unittest.TestCase):
    def test_matrix_matches_data_readme(self) -> None:
        """矩阵与 data/README §8.1 逐行一致（(flip_h, flip_v, rotate, swap_wh)）。"""
        self.assertEqual(set(ORIENTATION_MATRIX), set(EXPECTED))
        for value, expected in EXPECTED.items():
            with self.subTest(value=value):
                self.assertEqual(ORIENTATION_MATRIX[value], expected)

    def test_six_is_clockwise_90(self) -> None:
        """ExifTool 原文：`6 Rotate 90 CW` —— 必须是顺时针 90°，不是逆时针。"""
        t = transform_for(6)
        self.assertEqual(
            t["rotate_cw_deg"],
            90,
            "ExifTool EXIF tag 274 value 6 is 'Rotate 90 CW' (clockwise 90 degrees); "
            "if this fails, the matrix was reversed",
        )
        self.assertFalse(t["flip_h"])
        self.assertFalse(t["flip_v"])
        self.assertTrue(t["swap_wh"])

    def test_eight_is_clockwise_270(self) -> None:
        """ExifTool 原文：`8 Rotate 270 CW`（等价逆时针 90°）。"""
        t = transform_for(8)
        self.assertEqual(
            t["rotate_cw_deg"],
            270,
            "ExifTool EXIF tag 274 value 8 is 'Rotate 270 CW'",
        )
        self.assertTrue(t["swap_wh"])

    def test_mirror_family_has_both_flip_and_rotate(self) -> None:
        """镜像族 2/4/5/7 必须给 flip；5/7 还必须给 rotate（不得只给旋转）。"""
        for value in (2, 4, 5, 7):
            with self.subTest(value=value):
                t = transform_for(value)
                self.assertTrue(
                    t["flip_h"] or t["flip_v"],
                    f"orientation {value} is in the mirror family and must set a flip",
                )
        for value in (5, 7):
            with self.subTest(value=value):
                self.assertNotEqual(transform_for(value)["rotate_cw_deg"], 0)

    def test_value_4_is_spec_form_not_simplified(self) -> None:
        """值 4 的规范形式是 `flip_v=True, rotate=0`；**不做等价化简**（§8.1 注记）。"""
        t = transform_for(4)
        self.assertEqual((t["flip_h"], t["flip_v"], t["rotate_cw_deg"]), (False, True, 0))

    def test_labels_are_exiftool_wording(self) -> None:
        """标签逐字来自 ExifTool，不得改写。"""
        self.assertEqual(ORIENTATION_LABELS[5], "Mirror horizontal and rotate 270 CW")
        self.assertEqual(ORIENTATION_LABELS[6], "Rotate 90 CW")
        self.assertEqual(ORIENTATION_LABELS[7], "Mirror horizontal and rotate 90 CW")
        self.assertEqual(ORIENTATION_LABELS[8], "Rotate 270 CW")


class TestEffectiveSize(unittest.TestCase):
    def test_swap_only_for_5_6_7_8(self) -> None:
        for value in (1, 2, 3, 4):
            with self.subTest(value=value):
                self.assertEqual(effective_size(64, 48, value), (64, 48))
        for value in (5, 6, 7, 8):
            with self.subTest(value=value):
                self.assertEqual(effective_size(64, 48, value), (48, 64))


# ─────────────────────────────────────────────────────────────────────────────
# 文案层：label / 矩阵必须与 `data/README.md` 的表格**逐字**一致
# ─────────────────────────────────────────────────────────────────────────────

def _markdown_table(text: str, heading_needle: str) -> list[list[str]]:
    """取某个标题后紧跟的表格行（标题行锚定，不扫自由文本）。"""
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


class TestWordingMatchesDataReadme(unittest.TestCase):
    """`data/README` §1.1 / §8.1 是数值与标签的**唯一定义处**；这里是机器化对账。"""

    def test_labels_equal_data_readme_1_1(self) -> None:
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "EXIF / TIFF Orientation")
        parsed = {int(r[0]): _plain(r[1]) for r in rows if r and r[0].isdigit()}
        self.assertEqual(set(parsed), set(range(1, 9)), f"§1.1 表解析异常: {parsed}")
        for value, expected in parsed.items():
            with self.subTest(value=value):
                self.assertEqual(
                    ORIENTATION_LABELS[value],
                    expected,
                    f"data/README §1.1 的 label 原文与实现不一致（值 {value}）",
                )

    def test_matrix_equal_data_readme_8_1(self) -> None:
        rows = _markdown_table(DATA_README.read_text(encoding="utf-8"), "8 元变换矩阵")
        parsed = {}
        for row in rows:
            if not row or not row[0].isdigit():
                continue
            value = int(row[0])
            flip_h = _plain(row[2]) == "T"
            flip_v = _plain(row[3]) == "T"
            rotate = int(_plain(row[4]))
            swap = _plain(row[5]) == "是"
            parsed[value] = (flip_h, flip_v, rotate, swap)
        self.assertEqual(set(parsed), set(range(1, 9)), f"§8.1 表解析异常: {parsed}")
        for value, expected in parsed.items():
            with self.subTest(value=value):
                self.assertEqual(
                    ORIENTATION_MATRIX[value],
                    expected,
                    f"data/README §8.1 的矩阵与实现不一致（值 {value}）",
                )


# ─────────────────────────────────────────────────────────────────────────────
# 样本层：M1 的 22 份 M2 样本 → 真 CLI → 逐条对账
# ─────────────────────────────────────────────────────────────────────────────

_M2_RUNS: dict[str, tuple[int, dict | None]] = {}


def _fixture_runs() -> dict[str, tuple[int, dict | None]]:
    """把 `gen_orientation` 的**内存产出**写到临时目录，跑一次 CLI 并缓存结果。

    不读 `fixtures/out/`（产物不入仓，`plan/HANDOFF-M2.md` §二.2）。
    """
    if _M2_RUNS:
        return _M2_RUNS
    import contextlib
    import io

    from imageoracle import cli as cli_module

    with tempfile.TemporaryDirectory() as tmp:
        for name, (data, _triggers) in gen_orientation.build_all().items():
            path = Path(tmp) / name
            path.write_bytes(data)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                code = cli_module.main(["orientation", "--json", str(path)])
            _M2_RUNS[name] = (code, None if code == 3 else json.loads(buffer.getvalue()))
    return _M2_RUNS


class TestFixturesAgainstPlan05ExitGate(unittest.TestCase):
    """`plan/05` §二 M2 出口门 + `HANDOFF-M2.md` §六 DoD 的逐条对标。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.runs = _fixture_runs()

    def _payload(self, name: str) -> dict:
        self.assertIn(name, self.runs, f"缺样本 {name}")
        code, payload = self.runs[name]
        self.assertEqual(code, 0, f"{name} 预期 exit 0，实际 {code}")
        assert payload is not None
        return payload

    def _source(self, payload: dict, source: str) -> dict:
        for entry in payload["sources"]:
            if entry["source"] == source:
                return entry
        self.fail(f"输出里没有来源 {source}: {[s['source'] for s in payload['sources']]}")

    def test_eight_values_primary_label_transform(self) -> None:
        """DoD #1：8 值逐项对 ExifTool 语义（`m2_orient1..8`）。"""
        for value in range(1, 9):
            name = f"m2_orient{value}_portrait.jpg"
            with self.subTest(fixture=name):
                payload = self._payload(name)
                self.assertEqual(payload["primary"], value)
                self.assertEqual(payload["summary"], {"error": 0, "warning": 0, "info": 0, "unknown": 0, "suspicion": 0})
                source = self._source(payload, "exif.ifd0.orientation")
                self.assertEqual(source["state"], "present")
                self.assertEqual(source["value"], value)
                self.assertEqual(source["label"], ORIENTATION_LABELS[value])
                flip_h, flip_v, rotate, swap = ORIENTATION_MATRIX[value]
                self.assertEqual(
                    source["transform"],
                    {
                        "flip_h": flip_h,
                        "flip_v": flip_v,
                        "rotate_cw_deg": rotate,
                        "swap_wh": swap,
                        "label": ORIENTATION_LABELS[value],
                    },
                )

    def test_label_is_readme_wording(self) -> None:
        """label 与 `data/README` §1.1 原文逐字一致（6/8 是最易被改反的两个）。"""
        expected = {
            1: "Horizontal (normal)",
            2: "Mirror horizontal",
            3: "Rotate 180",
            4: "Mirror vertical",
            5: "Mirror horizontal and rotate 270 CW",
            6: "Rotate 90 CW",
            7: "Mirror horizontal and rotate 90 CW",
            8: "Rotate 270 CW",
        }
        for value, label in expected.items():
            with self.subTest(value=value):
                payload = self._payload(f"m2_orient{value}_portrait.jpg")
                self.assertEqual(self._source(payload, "exif.ifd0.orientation")["label"], label)

    def test_effective_size_swap_only_for_5_to_8(self) -> None:
        """DoD #3：5/6/7/8 交换 W/H，1/2/3/4 不交换（样本为非正方形 64×48）。"""
        for value in range(1, 9):
            name = f"m2_orient{value}_portrait.jpg"
            with self.subTest(fixture=name):
                payload = self._payload(name)
                self.assertEqual(payload["effective_size"]["stored"], [64, 48])
                expected = [48, 64] if value in (5, 6, 7, 8) else [64, 48]
                self.assertEqual(payload["effective_size"]["effective"], expected)

    def test_big_endian_tiff_read_by_header_byte_order(self) -> None:
        """DoD #3：`MM` 大端 TIFF —— 274 按头字节序读，不得固定小端。

        反证：若按小端读，大端的 `00 06`（=6）会被读成 0x0600=1536 → `out_of_range`。
        `primary` 正确即证明读法正确。
        """
        for value in (6, 8):
            name = f"m2_orient{value}_be.tif"
            with self.subTest(fixture=name):
                payload = self._payload(name)
                self.assertEqual(payload["container"]["kind"], "tiff")
                self.assertEqual(payload["primary"], value, "大端样本被按小端读了？")
                self.assertEqual(self._source(payload, "exif.ifd0.orientation")["value"], value)
                self.assertEqual(payload["effective_size"]["effective"], [48, 64])

    def test_png_exif_both_branches(self) -> None:
        """DoD #5：PNG `eXIf` 双支（无前缀 = 规范；带前缀 = 容错并记 note）。"""
        plain = self._payload("m2_orient6_exif.png")
        prefixed = self._payload("m2_orient6_exif_prefixed.png")
        for payload in (plain, prefixed):
            self.assertEqual(payload["primary"], 6)
            self.assertEqual(self._source(payload, "exif.ifd0.orientation")["value"], 6)
        self.assertEqual(plain["container"]["notes"], [], "无前缀的规范样本不该产生 note")
        self.assertTrue(
            any("prefix" in note for note in prefixed["container"]["notes"]),
            f"带前缀样本应记录事实 note，实际: {prefixed['container']['notes']}",
        )

    def test_webp_exif_both_branches(self) -> None:
        """DoD #5：WebP `EXIF` 双支（有/无 `Exif\\0\\0` 前缀，D10）。"""
        for name in ("m2_orient6_prefix.webp", "m2_orient6_noprefix.webp"):
            with self.subTest(fixture=name):
                payload = self._payload(name)
                self.assertEqual(payload["container"]["kind"], "webp")
                self.assertEqual(payload["primary"], 6)
                self.assertEqual(payload["effective_size"]["effective"], [48, 64])

    def test_absent_is_not_value_one(self) -> None:
        """DoD #4：`absent` ≠ 1 —— 缺失就是缺失，不许默认成 1。"""
        absent = self._payload("m2_absent.jpg")
        self.assertIsNone(absent["primary"])
        self.assertIsNone(absent["effective_size"])
        codes = [f["code"] for f in absent["findings"]]
        self.assertIn("orientation_absent", codes)
        finding = next(f for f in absent["findings"] if f["code"] == "orientation_absent")
        self.assertEqual(finding["severity"], "info")
        self.assertTrue(
            any(s["state"] == "absent" for s in absent["sources"]) or absent["sources"] == [],
            "缺失必须以 absent 状态呈现",
        )
        one = self._payload("m2_orient1_portrait.jpg")
        self.assertNotEqual(absent["primary"], one["primary"])
        self.assertIsNone(absent["effective_size"])

    def test_out_of_range_is_error(self) -> None:
        """DoD #4：越界（0 / 9）→ `error: orientation_out_of_range`（exit 2）。"""
        for value in (0, 9):
            name = f"m2_orient{value}_oor.jpg"
            with self.subTest(fixture=name):
                code, payload = self.runs[name]
                self.assertEqual(code, 2)
                assert payload is not None
                self.assertEqual(payload["summary"]["error"], 1)
                self.assertIsNone(payload["primary"])
                finding = next(f for f in payload["findings"] if f["code"] == "orientation_out_of_range")
                self.assertEqual(finding["severity"], "error")
                self.assertIn(str(value), finding["message"])

    def test_wrong_type_is_error(self) -> None:
        """DoD #4：tag 274 写成 LONG → `orientation_not_int16u`（exit 2）。"""
        code, payload = self.runs["m2_orient6_wrongtype.jpg"]
        self.assertEqual(code, 2)
        assert payload is not None
        self.assertEqual(payload["summary"]["error"], 1)
        finding = next(f for f in payload["findings"] if f["code"] == "orientation_not_int16u")
        self.assertEqual(finding["severity"], "error")
        self.assertIn("4", finding["message"])

    def test_mirror_family_sources_carry_flip(self) -> None:
        """镜像族 2/4/5/7 必须给 flip；5/7 还必须给 rotate。"""
        for value in (2, 4, 5, 7):
            name = f"m2_orient{value}_mirror.jpg"
            with self.subTest(fixture=name):
                transform = self._source(self._payload(name), "exif.ifd0.orientation")["transform"]
                self.assertTrue(transform["flip_h"] or transform["flip_v"])
                if value in (5, 7):
                    self.assertNotEqual(transform["rotate_cw_deg"], 0)

    def test_manifest_triggers_match_real_output(self) -> None:
        """M1 冻结的 `triggers[].expected` 必须能在 M2 真输出里找到对应。"""
        fixtures = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixtures"]
        checked = 0
        for name, entry in fixtures.items():
            if not name.startswith("m2_"):
                continue
            _code, payload = self.runs[name]
            assert payload is not None, f"{name} 无法解析"
            for trigger in entry["triggers"]:
                checked += 1
                with self.subTest(fixture=name, code=trigger["code"]):
                    self._assert_trigger(payload, trigger)
        self.assertGreaterEqual(checked, 22, "manifest 里的 M2 trigger 数量异常")

    def _assert_trigger(self, payload: dict, trigger: dict) -> None:
        expected = trigger.get("expected", {})
        kind = trigger["code"]
        if kind == "orientation":
            self.assertEqual(payload["primary"], expected["exif.ifd0.orientation"])
            source = self._source(payload, "exif.ifd0.orientation")
            self.assertEqual(source["value"], expected["exif.ifd0.orientation"])
            if expected.get("mirror_family"):
                transform = source["transform"]
                self.assertTrue(transform["flip_h"] or transform["flip_v"])
        elif kind == "orientation_absent":
            self.assertIsNone(payload["primary"])
            if payload["sources"]:
                # 有 EXIF 块但没有 274 → 该 IFD 记 absent
                self.assertIn("absent", [s["state"] for s in payload["sources"]])
            else:
                # 完全无来源 → 也必须以 finding 形式呈现缺失（不是默认 1）
                self.assertIn("orientation_absent", [f["code"] for f in payload["findings"]])
            if expected.get("distinct_from_value_1"):
                self.assertNotEqual(payload["primary"], 1)
        elif kind == "orientation_out_of_range":
            self.assertEqual(payload["summary"]["error"], 1)
            message = next(
                f["message"] for f in payload["findings"] if f["code"] == "orientation_out_of_range"
            )
            self.assertIn(str(expected["value"]), message)
        elif kind == "orientation_not_int16u":
            message = next(
                f["message"] for f in payload["findings"] if f["code"] == "orientation_not_int16u"
            )
            self.assertIn(f"type {expected['tiff_type']}", message)
        elif kind in {"orientation_missing_prefix_ok", "note_exif_prefix"}:
            # 纯事实记录（container note）；样本存在 + 上面的 primary=6 断言已覆盖
            self.assertTrue(payload["sources"], f"{kind}: 该样本应仍能读到方向来源")
        else:  # pragma: no cover - 新增 trigger 类型必须在这里显式处理
            self.fail(f"未处理的 trigger code: {kind}")


class TestXmpSourceIsReadable(unittest.TestCase):
    """XMP 也是 M2 的来源之一（`plan/03` §一）——造字节就地验一遍。"""

    def test_xmp_only_yields_primary(self) -> None:
        import contextlib
        import io

        from imageoracle import cli as cli_module

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "xmp_only.jpg"
            path.write_bytes(build_jpeg(width=64, height=48, xmp=xmp_packet(6)))
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli_module.main(["orientation", "--json", str(path)])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["primary"], 6)
        source = next(s for s in payload["sources"] if s["source"] == "xmp.tiff:Orientation")
        self.assertEqual(source["state"], "present")
        self.assertEqual(source["label"], "Rotate 90 CW")
        self.assertEqual(payload["effective_size"]["effective"], [48, 64])


if __name__ == "__main__":
    unittest.main()
