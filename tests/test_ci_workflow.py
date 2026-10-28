# -*- coding: utf-8 -*-
"""CI 工作流与离线镜像的结构断言（本地可跑，不需要 docker / 不需要远端）。

为什么要有这一条（`ai-tool-project-sprint` 阶段 7 实测）：
  · 推送前先在本地解析 workflow 并断言 job/step 数——step `name` 里出现裸 `: `
    会让 GitHub **直接不建 job**（run 显示 failure 而 `jobs=0`，文件字节却完全正常）；
  · `container.options: --network none` 与 Actions 的 job 容器模型互斥
    （`Initialize containers` 一步红、断言一行都没跑），所以本项目**必须**用
    嵌套 `docker run --network none`——这条也在这里断死，防止日后被"顺手改回去"。

解析策略：PyYAML 不是本项目依赖（零第三方依赖是红线），所以用**行级结构解析**：
只认 `jobs:` / 顶层 key 缩进 / `- name:` 的行首形态。判据比 YAML 语法窄，因此不会误判，
且不需要任何依赖。
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
OFFLINE_DOCKERFILE = ROOT / ".github" / "offline.Dockerfile"


class TestWorkflowShape(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(WORKFLOW.is_file(), f"{WORKFLOW.relative_to(ROOT)} 缺失")
        self.text = WORKFLOW.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        # job 只在 `jobs:` 块里找（`on:` 块里的 push/tags 也是两空格缩进，会误命中）
        self.jobs_block = "\n".join(self._top_level_block("jobs"))

    def test_jobs_are_declared(self) -> None:
        """至少三个 job：门与测试矩阵 / 零依赖证明 / 离线证明。"""
        self.assertTrue(self.jobs_block, "workflow 里找不到 jobs:")
        job_ids = re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", self.jobs_block, re.MULTILINE)
        self.assertGreaterEqual(len(job_ids), 3, f"job 太少: {job_ids}")
        self.assertIn("offline", job_ids)
        self.assertIn("zero-dependency-check", job_ids)

    def test_every_job_has_steps_with_names(self) -> None:
        """每个 job 都要有 steps，且每个 step 有 name（缺 name 的 step 在日志里不可指认）。"""
        for job in re.finditer(r"^  ([A-Za-z0-9_-]+):\s*$", self.jobs_block, re.MULTILINE):
            start = job.end()
            rest = self.jobs_block[start:]
            nxt = re.search(r"^  [A-Za-z0-9_-]+:\s*$", rest, re.MULTILINE)
            block = rest[: nxt.start()] if nxt else rest
            with self.subTest(job=job.group(1)):
                self.assertIn("steps:", block, f"{job.group(1)} 没有 steps")
                uses = len(re.findall(r"^\s+- (?:name|uses):", block, re.MULTILINE))
                named = len(re.findall(r"^\s+- name:", block, re.MULTILINE))
                self.assertEqual(uses, named, f"{job.group(1)} 有 step 缺 name")

    def test_no_bare_colon_in_step_names(self) -> None:
        """step `name` 里不许出现裸 `: `（会让 GitHub 不建 job，run 显示 failure 而 jobs=0）。"""
        offenders = [
            line for line in self.lines
            if re.match(r"^\s+- name:\s*\S", line) and ": " in line.split("name:", 1)[1]
        ]
        self.assertEqual(
            offenders, [],
            "step name 里含裸冒号，会被 YAML 当成嵌套 map（GitHub 会静默不建 job）",
        )

    def test_offline_job_does_not_use_container_options(self) -> None:
        """`container.options: --network none` 是 docker 互斥项；必须用嵌套 docker run。"""
        self.assertNotIn("container:", self.text, "workflow 里不该出现 job 容器块")
        self.assertNotIn("container.options", self.text)
        self.assertIn("docker run --rm --network none", self.text)

    def test_gates_run_in_ci(self) -> None:
        """两道门与门自证都必须有 CI 步骤（门只在开发机存在 = 等于没有）。"""
        for needle in (
            "tools/check_sprint_layout.py",
            "tools/check_desensitized.py",
            "tools/verify_gates.py",
        ):
            with self.subTest(cmd=needle):
                self.assertIn(f"python {needle}", self.text)

    def test_matrix_covers_python_floor_and_dev_version(self) -> None:
        # 合法口径调整（DEC6=乙）：Python 3.10 / 3.11 已 EOL，floor 抬到 3.12，
        # 矩阵随之从 ["3.10","3.12"] 改为 ["3.12","3.13"]。判据仍是"矩阵必须同时覆盖
        # 最低支持版本与一个更高版本"，只是那两个字符串跟着 floor 走。
        self.assertIn('python: ["3.12", "3.13"]', self.text)
        self.assertIn("ubuntu-latest", self.text)
        self.assertIn("windows-latest", self.text)

    def test_workflow_has_no_deprecated_actions(self) -> None:
        """actions 必须用 v7（v4/v5 会触发 Node20 弃用注解，且依赖旧的 runner 契约）。"""
        self.assertNotIn("actions/checkout@v4", self.text)
        self.assertNotIn("actions/setup-python@v5", self.text)
        self.assertIn("actions/checkout@v7", self.text)
        self.assertIn("actions/setup-python@v7", self.text)

    def _top_level_block(self, key: str) -> list[str]:
        collecting = False
        block: list[str] = []
        for line in self.lines:
            if line.startswith(f"{key}:"):
                collecting = True
                continue
            if collecting:
                if line and not line.startswith((" ", "\t")):
                    break
                block.append(line)
        return block


class TestOfflineDockerfile(unittest.TestCase):
    def test_exists_and_does_not_install_dependencies(self) -> None:
        """离线镜像里不许有安装步骤——"无网络容器里跑通"顺带证明零第三方依赖。

        判据只看 **Dockerfile 指令行**（非注释行）：注释里写"不 pip install"是解释，
        不是指令。判据面收窄到指令，才不会把说明文字误判成违规。
        """
        self.assertTrue(OFFLINE_DOCKERFILE.is_file(), ".github/offline.Dockerfile 缺失")
        instructions = [
            line.strip()
            for line in OFFLINE_DOCKERFILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        joined = "\n".join(instructions)
        self.assertNotIn("pip install", joined)
        self.assertNotIn("RUN ", joined)  # 一条 RUN 都不需要：纯 COPY + CMD
        self.assertIn("COPY . /work", joined)


if __name__ == "__main__":
    unittest.main()
