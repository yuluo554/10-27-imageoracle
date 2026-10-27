# -*- coding: utf-8 -*-
"""M2 的硬验收：8 元变换矩阵 + **6 = 顺时针 90°**。

最易搞反的一点（`plan/00` D1）：6 是 `Rotate 90 CW` = **顺时针** 90°，不是逆时针。
断言文案直接引用 ExifTool 原文，防止日后被"改反"——如果有人把矩阵改成 6→270，
失败信息会直接告诉维护者 ExifTool 是怎么写的。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from imageoracle.modules.orientation import (  # noqa: E402
    ORIENTATION_LABELS,
    ORIENTATION_MATRIX,
    effective_size,
    transform_for,
)

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


if __name__ == "__main__":
    unittest.main()
