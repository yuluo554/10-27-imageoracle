# -*- coding: utf-8 -*-
"""生成器共用外壳：**单一实现**，四个族生成器与聚合器都经这里。

放在 lib/ 的理由：四个族生成器各自的 `--check` / 自检 / 写盘逻辑若各写一份，
就会出现"四份口径漂移"（skill 假门族：同一件事多份实现）。这里只留一份：

  · `--check` 两层断言（内存重生成 vs manifest；冻结产物 vs 重生成）
  · 生成期自检挂在 `build_fn()` 的调用链上（不是挂在 `__main__` 下）
  · 写盘路径与 manifest 汇写

**聚合器独占 manifest 写入**：`gen_all.py` 汇写四个族的全集；单族生成器只写自己的
产物字节，不碰 manifest（否则后跑的族会把先跑的族覆盖掉，manifest 变成"最后那个"）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))   # lib/ 自身（build / manifest）
sys.path.insert(0, str(ROOT / "src"))

from manifest import build_manifest, compare, write_manifest  # noqa: E402

OUT_DIR = ROOT / "fixtures" / "out"
MANIFEST = ROOT / "fixtures" / "manifest.json"


def self_check(items: dict[str, tuple[bytes, list[dict]]], build_fn, extra=None) -> None:
    """生成期自检——挂在 `build_fn()` 的调用链上，不挂在 `__main__` 下（skill 假门族 ⑲）。

    断言：每个样本非空、签名可被本工具 sniff 到、至少一条 trigger、两次构建字节完全相同。
    `extra(items)` 给单族追加自己的领域断言（如镜像族样本存在）。
    """
    from imageoracle.readers import sniff

    assert items, "生成器没有产出任何样本"
    for name, (data, triggers) in items.items():
        assert data, f"{name} 是空文件"
        assert triggers, f"{name} 缺 triggers"
        sniff(data[:12])            # 签名无法识别会抛 UnsupportedFormat
    again = build_fn()
    assert set(again) == set(items), "两次构建的样本集合不一致（不确定性）"
    for name in items:
        assert items[name][0] == again[name][0], f"{name} 两次构建不一致（不确定性）"
    if extra is not None:
        extra(items)


def check(name: str, items: dict[str, tuple[bytes, list[dict]]], *, strict: bool) -> int:
    problems = compare(MANIFEST, items, OUT_DIR, strict=strict)
    layer2_checked = sum(1 for name in items if (OUT_DIR / name).is_file())
    layer2_skipped = len(items) - layer2_checked

    print(f"{name} --check")
    print("=" * 64)
    print(f"第一层 内存重生成 vs manifest: {len(items)} 条（{('全集' if strict else '本族')}）")
    print(f"第二层 冻结产物 vs 重生成: 核对 {layer2_checked} / 缺件 SKIP {layer2_skipped}"
          + ("（缺件是正常态：产物不入仓）" if layer2_skipped else ""))
    for p in problems:
        print(f"FAIL  {p}")
    print("=" * 64)
    print(f"结论: {'一致' if not problems else f'{len(problems)} 处漂移'}")
    return 0 if not problems else 1


def emit(
    name: str,
    build_fn,
    *,
    generators: list[str],
    notes: list[str] | None = None,
    extra=None,
    write_manifest_too: bool = False,
    argv: list[str] | None = None,
) -> int:
    """单族/聚合器的统一入口。

    `write_manifest_too=True` 供 `gen_all.py` 使用：汇写全量 manifest。
    单族生成器用默认值（只写自己的产物字节）。
    """
    parser = argparse.ArgumentParser(description=f"{name} fixture 生成器")
    parser.add_argument("--check", action="store_true", help="只核对，不写盘")
    parser.add_argument("--out", default=None, help="输出目录（默认 fixtures/out/）")
    args = parser.parse_args(argv)

    items = build_fn()
    self_check(items, build_fn, extra)   # 自检在调用链上：--check 与写盘两条路径都会跑到

    if args.check:
        return check(name, items, strict=write_manifest_too)

    out_dir = Path(args.out) if args.out else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for fname, (data, _triggers) in items.items():
        (out_dir / fname).write_bytes(data)

    if write_manifest_too:
        manifest = build_manifest(items, generators=generators, notes=notes)
        write_manifest(MANIFEST, manifest)
        print(f"写出 {len(items)} 个样本到 {out_dir.relative_to(ROOT)}/")
        print(f"写出 manifest: {MANIFEST.relative_to(ROOT)}（{len(items)} 条 sha256）")
        print(f"generators: {', '.join(generators)}")
    else:
        print(f"写出 {len(items)} 个样本到 {out_dir.relative_to(ROOT)}/（未改 manifest；汇写请跑 gen_all.py）")
    return 0
