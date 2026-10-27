# -*- coding: utf-8 -*-
"""manifest 读写（生成器共用）。

`fixtures/manifest.json` 是**冻结真值**：每个样本的 `sha256` + 触发项。
生成器与 `--check` 都只经这里读写，避免两份实现漂移。

口径（`plan/04` §二）：
  · sha256 是 Python 3.12 的**冻结值**；zlib 输出跨解释器可能不同 → CI 跨版本只断言解析结果一致
  · `notes` 必须写明"像素数据不可解码"这条诚实边界，不许省略
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

STRUCTURAL_NOTE = (
    "structural fixture: pixel data is not decodable (the tool never decodes pixels); "
    "all fields the tool reads (tags, offsets, lengths, CRCs, frame timings) are exact"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(
    items: dict[str, tuple[bytes, list[dict]]],
    *,
    generators: list[str],
    notes: list[str] | None = None,
) -> dict:
    return {
        "schema": 1,
        "generators": generators,
        "deterministic": True,
        "notes": [STRUCTURAL_NOTE, *(notes or [])],
        "fixtures": {
            name: {"sha256": sha256(data), "bytes": len(data), "triggers": triggers}
            for name, (data, triggers) in items.items()
        },
    }


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(manifest_path: Path, items: dict[str, tuple[bytes, list[dict]]], out_dir: Path) -> list[str]:
    """两层断言。返回问题列表（空 = 一致）。**不抛异常**，缺件走显式 SKIP 由调用方打印。"""
    if not manifest_path.is_file():
        return [f"{manifest_path.name} 不存在（先跑一次不带 --check）"]

    frozen = read_manifest(manifest_path).get("fixtures", {})
    problems: list[str] = []

    now_names, frozen_names = set(items), set(frozen)
    for name in sorted(frozen_names - now_names):
        problems.append(f"manifest 有条目但生成器不再产出: {name}")
    for name in sorted(now_names - frozen_names):
        problems.append(f"生成器产出但 manifest 无条目: {name}")
    for name in sorted(now_names & frozen_names):
        digest = sha256(items[name][0])
        if digest != frozen[name]["sha256"]:
            problems.append(
                f"哈希漂移 {name}: manifest={frozen[name]['sha256'][:12]} now={digest[:12]}"
            )
        frozen_path = out_dir / name
        if frozen_path.is_file() and frozen_path.read_bytes() != items[name][0]:
            problems.append(f"冻结产物与重生成不一致: {name}")

    return problems
