# -*- coding: utf-8 -*-
"""M1 出口门：manifest 是**冻结真值**，四族生成器是它的唯一来源。

判据（逐条对应 `plan/HANDOFF-M1.md` §六 DoD）：
  · manifest 的 fixture 集合 == 四族生成器产出集合（聚合器的 `build_all()`）
  · 每条样本都有 `triggers`，且 `module` 落在里程碑表里、含 `code`
  · 样本名前缀 `m<k>_` 与 triggers 的 `module` 一致（`m3_*` 只许触发 M3）
  · manifest 的 `sha256` / `bytes` 与**重新生成**的字节逐条吻合（冻结值没被人手改过）
  · 生成器不 spawn 外部进程（import 级 + 属性级双判据）
  · `gen_all.py --check` 位级一致（两层断言）

**为什么"冻结值"要重算**：`plan/HANDOFF-M1.md` §二.3 明写"不要为了让 `--check` 变绿而手改 manifest"。
这条测试把"手改 manifest"变成红灯——重算与冻结值不符即失败。
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "fixtures"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))

import gen_all  # noqa: E402
import gen_container  # noqa: E402
import gen_double_rotate  # noqa: E402
import gen_icc  # noqa: E402
import gen_orientation  # noqa: E402
from tests._helpers import run_script  # noqa: E402

MANIFEST = ROOT / "fixtures" / "manifest.json"
KNOWN_MODULES = {"M1", "M2", "M3", "M4", "M5", "M6"}
FAMILY_GENERATORS = (
    "fixtures/gen_orientation.py",
    "fixtures/gen_double_rotate.py",
    "fixtures/gen_icc.py",
    "fixtures/gen_container.py",
)
#: 生成器**不得** import 的进程/网络模块（fixtures 只做纯字节构造）
FORBIDDEN_FIXTURE_IMPORTS = {"subprocess", "os", "socket", "shutil", "pty", "multiprocessing"}


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class TestManifestIsFrozenTruth(unittest.TestCase):
    def test_manifest_set_equals_generator_output(self) -> None:
        items = gen_all.build_all()
        self.assertEqual(set(_manifest()["fixtures"]), set(items), "manifest 与四族产出集合不等")

    def test_sha256_and_len_are_frozen_truth(self) -> None:
        """重算每一份字节 → 必须与 manifest 里的 sha256/bytes 逐条吻合（不许手改）。"""
        items = gen_all.build_all()
        frozen = _manifest()["fixtures"]
        for name, (data, _triggers) in items.items():
            with self.subTest(fixture=name):
                self.assertEqual(hashlib.sha256(data).hexdigest(), frozen[name]["sha256"])
                self.assertEqual(len(data), frozen[name]["bytes"])

    def test_every_fixture_has_module_and_code_triggers(self) -> None:
        for name, entry in _manifest()["fixtures"].items():
            with self.subTest(fixture=name):
                self.assertTrue(entry["triggers"], f"{name} 没有写『要触发哪条验收项』")
                for trigger in entry["triggers"]:
                    self.assertIn(trigger["module"], KNOWN_MODULES)
                    self.assertIn("code", trigger)
                    self.assertTrue(trigger["code"], f"{name} 的 trigger 缺 code")

    def test_name_prefix_matches_trigger_module(self) -> None:
        """`m<k>_*` 只许触发 `M<k>`：让"样本放错族"当场红灯。"""
        for name, entry in _manifest()["fixtures"].items():
            if not name.startswith("m") or "_" not in name:
                continue
            number = name[1:].split("_", 1)[0]
            with self.subTest(fixture=name):
                self.assertTrue(number.isdigit(), f"{name} 不符合 m<k>_<case> 命名口径")
                self.assertTrue(
                    all(t["module"] == f"M{number}" for t in entry["triggers"]),
                    f"{name} 的 triggers 模块号与文件名前缀不符",
                )

    def test_notes_state_structural_limit(self) -> None:
        self.assertIn("not decodable", " ".join(_manifest().get("notes", [])))

    def test_generators_registered(self) -> None:
        self.assertEqual(sorted(_manifest()["generators"]), sorted(FAMILY_GENERATORS))
        self.assertTrue(_manifest()["deterministic"])


class TestGeneratorDiscipline(unittest.TestCase):
    def test_no_external_process_imports(self) -> None:
        """生成器**不得** import 进程/网络模块（import 级判据，与属性级判据互补）。"""
        offenders: list[str] = []
        for path in sorted((ROOT / "fixtures").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in FORBIDDEN_FIXTURE_IMPORTS:
                            offenders.append(f"{path.relative_to(ROOT)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    if (node.module or "").split(".")[0] in FORBIDDEN_FIXTURE_IMPORTS:
                        offenders.append(f"{path.relative_to(ROOT)}: from {node.module}")
        self.assertEqual(offenders, [], f"fixtures 里出现进程/网络 import: {offenders}")

    def test_aggregate_build_is_deterministic(self) -> None:
        first = gen_all.build_all()
        second = gen_all.build_all()
        self.assertEqual(set(first), set(second))
        for name in first:
            with self.subTest(fixture=name):
                self.assertEqual(first[name][0], second[name][0], f"{name} 两次构建不一致")

    def test_no_name_collision_between_families(self) -> None:
        seen: dict[str, str] = {}
        for module in (gen_orientation, gen_double_rotate, gen_icc, gen_container):
            for name in module.build_all():
                with self.subTest(fixture=name):
                    self.assertNotIn(name, seen, f"{name} 同时来自 {seen.get(name)} 与 {module.__name__}")
                    seen[name] = module.__name__


class TestCheckMode(unittest.TestCase):
    def test_aggregate_check_is_bitwise_equal(self) -> None:
        proc = run_script("fixtures/gen_all.py", "--check")
        self.assertEqual(proc.returncode, 0, (proc.stdout or "") + (proc.stderr or ""))

    def test_each_family_check_is_bitwise_equal(self) -> None:
        for rel in FAMILY_GENERATORS:
            with self.subTest(generator=rel):
                proc = run_script(rel, "--check")
                self.assertEqual(proc.returncode, 0, f"{rel}: " + (proc.stdout or "") + (proc.stderr or ""))


if __name__ == "__main__":
    unittest.main()
