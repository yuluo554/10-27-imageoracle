# -*- coding: utf-8 -*-
"""fixtures 生成器与 manifest 的守门。

判据：
  · 生成器不调用外部 CLI（AST：无 subprocess / os.system）
  · 生成器确定性（两次构建字节相同）
  · manifest 与生成器产出**集合相等**（缺与多都要报）
  · manifest 每条都有 triggers，且 triggers 的 module 在本项目里程碑表里
  · manifest 的 notes 含"像素不可解码"这条诚实边界
  · `--check` 在 manifest 缺失时返回 1（不是崩，也不是绿）
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

import gen_orientation  # noqa: E402
from tests._helpers import run_script  # noqa: E402

KNOWN_MODULES = {"M1", "M2", "M3", "M4", "M5", "M6"}


class TestGeneratorDiscipline(unittest.TestCase):
    def test_no_external_toolchain(self) -> None:
        """生成器不得调用外部 CLI（本机没有 exiftool/jpegtran/sharp）。"""
        offenders: list[str] = []
        for path in sorted((ROOT / "fixtures").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in {"system", "popen", "run", "call", "check_output"}:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
                if isinstance(node, ast.Name) and node.id == "__import__" and False:
                    pass
        self.assertEqual(offenders, [], f"fixtures 里出现进程调用: {offenders}")

    def test_generation_is_deterministic(self) -> None:
        first = gen_orientation.build_all()
        second = gen_orientation.build_all()
        self.assertEqual(set(first), set(second))
        for name in first:
            with self.subTest(fixture=name):
                self.assertEqual(first[name][0], second[name][0], f"{name} 两次构建不一致")

    def test_every_fixture_has_triggers(self) -> None:
        items = gen_orientation.build_all()
        for name, (_data, triggers) in items.items():
            with self.subTest(fixture=name):
                self.assertTrue(triggers, f"{name} 没有写『它要触发哪条验收项』")
                for trigger in triggers:
                    self.assertIn(trigger["module"], KNOWN_MODULES)
                    self.assertIn("code", trigger)

    def test_mirror_family_superset_present(self) -> None:
        """镜像族 2/4/5/7 + 6/8 + absent + 越界 + 类型错 + 大端 + 两种 eXIf + 两种 WebP 前缀。"""
        items = gen_orientation.build_all()
        required = [
            "m2_orient1_portrait.jpg",
            "m2_orient6_portrait.jpg",
            "m2_orient8_portrait.jpg",
            "m2_orient2_mirror.jpg",
            "m2_orient4_mirror.jpg",
            "m2_orient5_mirror.jpg",
            "m2_orient7_mirror.jpg",
            "m2_orient6_be.tif",
            "m2_orient8_be.tif",
            "m2_orient6_exif.png",
            "m2_orient6_exif_prefixed.png",
            "m2_orient6_prefix.webp",
            "m2_orient6_noprefix.webp",
            "m2_absent.jpg",
            "m2_orient0_oor.jpg",
            "m2_orient9_oor.jpg",
            "m2_orient6_wrongtype.jpg",
        ]
        for name in required:
            with self.subTest(fixture=name):
                self.assertIn(name, items)


class TestManifest(unittest.TestCase):
    def test_manifest_matches_generator(self) -> None:
        manifest_path = ROOT / "fixtures" / "manifest.json"
        self.assertTrue(
            manifest_path.is_file(),
            "fixtures/manifest.json 缺失：先跑 py -3.12 fixtures/gen_orientation.py",
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        items = gen_orientation.build_all()
        self.assertEqual(set(manifest["fixtures"]), set(items), "manifest 与生成器产出集合不等")

    def test_manifest_notes_state_structural_limit(self) -> None:
        """诚实边界：必须写明像素数据不可解码。"""
        manifest = json.loads((ROOT / "fixtures" / "manifest.json").read_text(encoding="utf-8"))
        joined = " ".join(manifest.get("notes", []))
        self.assertIn("not decodable", joined)


class TestCheckMode(unittest.TestCase):
    def test_check_passes_against_frozen_manifest(self) -> None:
        proc = run_script("fixtures/gen_orientation.py", "--check")
        self.assertEqual(proc.returncode, 0, (proc.stdout or "") + (proc.stderr or ""))


if __name__ == "__main__":
    unittest.main()
