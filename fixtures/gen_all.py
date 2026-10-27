# -*- coding: utf-8 -*-
"""M1 聚合生成器：把四族样本合成一份 `fixtures/manifest.json`（覆盖 M2–M6 验收面）。

**manifest 只有一个写入者**（本文件）。单族生成器只写自己的产物字节，不碰 manifest——
否则后跑的族会把先跑的族从 manifest 里覆盖掉，真值就只剩"最后一个族"。

CLI:
  py -3.12 fixtures/gen_all.py            # 写全部产物 + 汇写 manifest
  py -3.12 fixtures/gen_all.py --check    # 只核对全部（严格集合相等；退出码 1 = 漂移）

`--check` 两层断言（`plan/04` §二.3）：
  第一层 四族内存重生成 → 与 manifest.json 的 sha256 逐条比对（集合必须**恰好相等**）
  第二层 fixtures/out/ 里若存在冻结产物 → 与其字节逐字节比对（不存在则显式 SKIP）
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fixtures"))
sys.path.insert(0, str(ROOT / "fixtures" / "lib"))
sys.path.insert(0, str(ROOT / "src"))

import gen_container  # noqa: E402
import gen_double_rotate  # noqa: E402
import gen_icc  # noqa: E402
import gen_orientation  # noqa: E402
from generator import emit  # noqa: E402

#: 固定顺序（合并顺序稳定 → manifest 稳定）
FAMILIES = (gen_orientation, gen_double_rotate, gen_icc, gen_container)

GENERATORS = [
    "fixtures/gen_orientation.py",
    "fixtures/gen_double_rotate.py",
    "fixtures/gen_icc.py",
    "fixtures/gen_container.py",
]

NOTES = [
    "manifest sha256 是 Python 3.12 的冻结值；zlib 输出跨解释器版本可能不同，"
    "CI 跨版本只断言解析结果一致，不断言字节哈希一致（plan/05 §四 #4）",
    "eXIf：PNG 按规范不带 Exif\\0\\0 前缀；另造一份带前缀的样本记录事实（D10）",
    "M4 范围限定：PNG iCCP 首期不解压（unknown: compressed_profile_not_inspected）；"
    "三类损坏另造 JPEG APP2 孪生样本证明 error 路径（plan/04 §二 / R5）",
    "M5 帧时长：同一 100 ms 在 GIF=10(1/100s) / APNG=10/100 / WebP=100(ms) 三格式各一份，"
    "归一化后都必须等于 100 ms（data/README §8.3）",
]


def build_all() -> dict[str, tuple[bytes, list[dict]]]:
    """四族合并。名字冲突即刻失败（重名 = 一族会静默盖掉另一族）。"""
    items: dict[str, tuple[bytes, list[dict]]] = {}
    for module in FAMILIES:
        for name, payload in module.build_all().items():
            assert name not in items, f"样本名冲突（两族产出同名）: {name}"
            items[name] = payload
    return items


def main(argv: list[str] | None = None) -> int:
    return emit(
        "全量 fixtures（M2–M5 验收样本）",
        build_all,
        generators=GENERATORS,
        notes=NOTES,
        write_manifest_too=True,
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
