# HANDOFF-M3 — 双重旋转探测器（题目 M2）

> 上一棒：**M2 orientation 判定器（✅）**。下一棒：**M3 double-rotate 探测器**。
> 本文件是第 3 棒的**入口交接单**；动手前先跑三道门（见 §七）。

## 一、当前进度 + 证据

**M2 已完成并验证**（2026-10-27）：

| 交付 | 证据 |
|---|---|
| 8 值逐项对 ExifTool 语义 | `tests/test_m2_orientation.py::TestFixturesAgainstPlan05ExitGate::test_eight_values_primary_label_transform`（22 份 M2 样本跑真 CLI） |
| label 与原文逐字一致 | `test_label_is_readme_wording` + `TestWordingMatchesDataReadme`（**解析 `data/README` §1.1 表格**对账，不在测试里另抄一份） |
| 矩阵与 §8.1 逐字一致 | `test_matrix_equal_data_readme_8_1`（解析 `data/README` §8.1 表格） |
| 6=CW90 / 8=CW270 单测 | `TestMatrix::test_six_is_clockwise_90` / `test_eight_is_clockwise_270`（断言文案引用 ExifTool 原文） |
| 5/6/7/8 交换 W/H | `test_effective_size_swap_only_for_5_to_8`（样本为非正方形 64×48，交换可观测） |
| 大端 `MM` TIFF 按头字节序读 | `test_big_endian_tiff_read_by_header_byte_order`（`m2_orient6_be.tif` / `m2_orient8_be.tif`） |
| PNG `eXIf` 双支 + WebP `EXIF` 双支（D10） | `test_png_exif_both_branches` / `test_webp_exif_both_branches`（4 份样本 `primary=6`；带前缀的 PNG 记 note） |
| `absent` ≠ 1；越界/类型错 → `error`（exit 2） | `test_absent_is_not_value_one` / `test_out_of_range_is_error` / `test_wrong_type_is_error` |
| XMP 来源可读 | `TestXmpSourceIsReadable`（内存造 XMP-only JPEG） |
| manifest `triggers` 与真输出对账 | `test_manifest_triggers_match_real_output`（M1 冻结真值 → M2 判决） |
| 单元测试 | `py -3.12 -m unittest discover -s tests -t .` → **79 tests OK** |
| 三道门 + 门自证 | `check_sprint_layout` / `check_desensitized` / `verify_gates` → **全绿（18/18）** |

**M3 现状（本棒实测基线，动手前先复现）**：`modules/double_rotate.py` 是**契约占位**（`analyze()` 抛
`NotImplementedError`），CLI 里 `double-rotate` 未接线 → exit 3。M2 已经把 M3 需要的**三份 `sources`**
喂出来了（`py -3.12 fixtures/gen_all.py` 后用 `imageoracle orientation` 看）：

- `m3_ifd1_unsynced.jpg` → `primary=6`，sources 有 `exif.ifd0.orientation=6` **和** `exif.ifd1.orientation=1`（条件 1 素材）
- `m3_xmp_residual.jpg` → `primary=1`，sources 有 `exif.ifd0.orientation=1` **和** `xmp.tiff:Orientation=6`（条件 2 素材）
- `m3_bigedge_mismatch.jpg` → `primary=6`，`stored=[80,40]`/`effective=[40,80]`（条件 3：声明 6 但容器宽>高）

**诚实口径**：以上全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**——任何文档都不得写"CI 绿"。

## 二、当前事实·状态不变量（下一棒动手前必须知道）

1. **M3 从 `modules.orientation.analyze()` 的 `sources` 起步，不重读容器**。XMP 正则的**唯一实现**是
   `orientation.read_xmp_orientation`（`plan/03` §二 复用约定）；再写第二份正则 = 两处漂移。
2. **接线要三处一起改**：`modules/double_rotate.py` 去占位 → `modules.IMPLEMENTED` 里登记 →
   `modules.PLANNED` 里删掉 `double-rotate`。漏一处，`tests/test_cli_contract.py` 的登记一致性判据会红。
3. **`certain` 与 `heuristic` 必须分列**（`condition_hits` / `certain` / `heuristic` 各自成字段），
   不得混进同一个分数。条件 3 只准出 `severity: suspicion` + `confidence: gray-heuristic`
   （`data/README` §8.4 第 1 条：需要解码像素才能确认的一律 gray）。
4. **退出码只认 `cli.py:exit_code_for`**。`suspicion` **不在** 0/1/2/3 判据里（口径见 `data/README` §8.5）；
   若要让"有 suspicion 就非 0"，必须先改 `data/README` §8.5 与 `exit_code_for`，不能就地加分支。
5. **状态行机读形态**：`| M<k> | … | <状态> |`，首格**恰好**是 `M<k>`；新增/翻状态必须**三处同改**
   （`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态行）。`plan/05` §一 映射表刻意写成
   `| orientation 判定器（M2） | … |`，**不要**把它改成 `| M2 |` 开头。
6. **`fixtures/out/` 不入仓**（`.gitignore` 封图像后缀）。测试**不读产物**：把 `gen_*.build_all()`
   的内存产出写到临时目录再跑 CLI（`tests/test_m2_orientation.py` 已给可复制的样板）。
7. **不改 M1 已冻结样本字节**。改了要重跑 `gen_all.py` 并接受 manifest 变更；`--check` 变红是设计如此。
   `gen_all.py --check` 现在两层都断言（内存重生成 + 冻结产物）。
8. **`m3_bigedge_mismatch.jpg` 的语义由 M3 定**：80×40、声明 6 → 只出 `suspicion`（见 `manifest.json`
   的 `triggers.expected`：`condition=3` / `confidence=gray-heuristic` / `severity=suspicion`）。
9. **报告 `generated_at` 默认 `"1970-01-01T00:00:00Z"`**，包内**禁止读时钟**（AST 守门）；
   JSON 序列化唯一入口 = `report.render_json`（别处另写 `json.dumps` 会破双跑逐字节相等）。
10. **证据面**：每条 finding 必须带 `evidence.spec`（在 `specs.CLAUSES` 里）+ `quote`（条款原文逐字）。
    M3 会用到 `sharp` / `jpegtran` / ImageMagick 的**需求原话**——它们是"需求依据"，若进 `evidence.quote`
    需先在 `specs/` 立条款 ID，否则 `selftest_evidence_complete` 会红。
11. **`fixtures/` 里禁用 `.run(`/`.call(`/`.system(`/`.popen(` 这些属性名**（AST 判据会读成"调外部 CLI"）；
    共用外壳入口叫 `emit(...)`。
12. **改交付面（`src/`、`pyproject.toml`）必须同步升版本号两处**（`src/imageoracle/__init__.py` +
    `pyproject.toml`）。M3 落地 = 交付面变更 → 升版本。

## 三、下一棒待办（M3 double-rotate 探测器）

**目标**：把 `plan/05` §二 M3 出口门**逐条对标**三份 `m3_*` 样本，实现判决 + verdicts，收口翻 ✅。

| # | 待办 | 完成判据 |
|---|---|---|
| 1 | 条件 1：`IFD1.orientation != IFD0.orientation`（两者都存在时）→ `certain` | `m3_ifd1_unsynced.jpg` 命中，输出含两个来源的原始值 |
| 2 | 条件 2：XMP 与 EXIF 274 冲突（值不同；或一方存在且非 1 而另一方缺失）→ `certain` | `m3_xmp_residual.jpg` 命中（EXIF=1 / XMP=6，复现 sharp #4585） |
| 3 | 条件 3：声明方向与容器自带宽高的"大边位置"不符 → `gray-heuristic` + `suspicion` | `m3_bigedge_mismatch.jpg` 命中，且 `certain` 列表为空 |
| 4 | `{condition_hits, certain, heuristic, verdicts:[{consumer, trigger_chain, consequence, evidence}]}` | 输出结构齐；`certain`/`heuristic` **分列** |
| 5 | 每条 verdict 给"软件 × 触发链"（sharp / jpegtran / ImageMagick 三例） | 每条带 `evidence` |
| 6 | 接线：`IMPLEMENTED` 登记 + 从 `PLANNED` 移除 + CLI 暴露 `double-rotate` | CLI 可跑；`test_cli_contract` 登记一致性绿 |
| 7 | 写 `tests/test_m3_double_rotate.py`：三条件各命中 + 分列断言 + 无误报（M2 好样本不命中） | 测试绿 |
| 8 | 回写三处状态副本 M3 → ✅（同提交） | 布局门 `STATUS` PASS |
| 9 | 写 `plan/HANDOFF-M4.md`（七节） | 布局门 `HANDOFFS` PASS |

**不要做**：不要在 M3 里实现 M4/M5 的判定逻辑；不要为了让条件 3 命中而改 M1 冻结产物；
不要把 `heuristic` 结论升格成 `certain`。

## 四、既定口径清单（K 编号，动了会打挂测试）

| K | 口径 | 动了会红 |
|---|---|---|
| K1 | 8 元变换矩阵 = `data/README` §8.1；`6→CW90`、`8→CW270` | `test_m2_orientation`（含断言文案） |
| K2 | 变换记录规范形式（4 = `flip_v`），**不做等价化简** | `test_value_4_is_spec_form_not_simplified` |
| K3 | 有效宽高只在 5/6/7/8 交换；`absent` ≠ `=1` | `test_swap_only_for_5_6_7_8` + CLI 契约测试 |
| K4 | 退出码 0/1/2/3，优先级 3 > 2 > 1 > 0；`unknown` 计入 2 | `test_cli_contract.TestExitCodes` |
| K5 | `exit_code_for` 全仓库只能有 1 处定义 | `test_exit_code_has_one_definition` |
| K6 | JSON 双跑逐字节相等；无浮点；`generated_at` 默认固定串 | `TestDeterminism` |
| K7 | 报告路径按入参原样输出（不 `abspath`） | 脱敏门 |
| K8 | `evidence.spec` 必须在 `specs.CLAUSES` 里；条款原文逐字 | `test_specs` + `selftest_evidence_complete` |
| K9 | 分层：readers↛modules、modules↛report、report↛readers | `test_layering.TestLayering` |
| K10 | 零第三方 import、零网络 import、无 `zlib.decompress`（readers/modules）、包内不读时钟 | `test_layering.TestRedLines` |
| K11 | 版本号两处一致（`__init__.py` + `pyproject.toml`） | `test_version_two_places_agree` |
| K12 | 状态行形态 `\| M<k> \| …`，首格恰好是里程碑号 | 布局门 `STATUS_LINE` |
| K13 | manifest 的 sha256 是 **3.12 冻结值**；跨解释器只断言解析一致 | `tests/test_m1_manifest.py` + `plan/05` §四 #4 |
| K14 | fixtures 不得调用外部 CLI（AST 判据：属性级 + import 级） | `test_no_external_toolchain` / `test_no_external_process_imports` |
| K15 | `modules.PLANNED` 与 `IMPLEMENTED` 必须与 CLI 实际暴露面一致 | CLI 测试 + `test_fixtures` |
| K16 | `data/README` §1.1/§8.1 是 label 与矩阵的**唯一定义处**；测试解析表格对账 | `TestWordingMatchesDataReadme` |
| K17 | M3 读 `orientation.analyze()` 的 `sources`；XMP 正则唯一实现 = `read_xmp_orientation` | 新增的 M3 测试 + 分层判据 |

## 五、本机环境坑（只写实测过的）

| 坑 | 实测现象 | 处置 |
|---|---|---|
| `python` 是 3.8.8 商店占位符 | `python --version` → 3.8.8 | 一律 `py -3.12` |
| Windows 默认代码页解不了中文输出 | `subprocess.run(text=True)` 抛 `UnicodeDecodeError` | 统一走 `tests/_helpers.run_cli()`（显式 `encoding="utf-8"`） |
| 直接跑 `py -3.12 fixtures/*.py` 时 `sys.path` 不含 `src/` 与 `fixtures/lib/` | `ModuleNotFoundError` | 生成器自己注入路径（`fixtures/lib/generator.py` 已统一注入） |
| fixtures 里 `x.run(...)` 会被 AST 判据读成"调外部 CLI" | `test_no_external_toolchain` 假红 | 共用外壳入口取名 `emit(...)` |
| 本机无 exiftool/jpegtran/sharp/magick | `which` 全部 not found | 全部 fixture 纯 Python 字节构造（K14） |
| 安全钩子拦子进程拼接 | 早期门自证脚本被拦 | 门自证改为**进程内 import 门模块调 `main()`**，无子进程 |
| 测试里 `from tests._helpers import …` 需要仓库根在 `sys.path` | 裸 import `_helpers` → `ModuleNotFoundError` | `unittest discover -s tests -t .`（`-t .` 保证根在路径上） |
| 大面积 `-A` 抓 grep 上下文时易误读表格行 | 手工核对时把 `plan/05` §一 映射表读成状态行 | 状态只认 `^\|\s*\*{0,2}M(\d+)\*{0,2}\s*\|`（K12） |

## 六、DoD 逐项 checklist（M3 出口）

- [ ] 条件 1（IFD1≠IFD0）在 `m3_ifd1_unsynced.jpg` 上命中且 `certain`
- [ ] 条件 2（XMP 冲突）在 `m3_xmp_residual.jpg` 上命中且 `certain`（复现 sharp #4585）
- [ ] 条件 3（大边启发式）在 `m3_bigedge_mismatch.jpg` 上命中，**只出 `suspicion`** + `gray-heuristic`
- [ ] `certain` / `heuristic` 分列；`verdicts` 每条带 `consumer + trigger_chain + consequence + evidence`
- [ ] 无误报：M2 的 22 份好样本在 `double-rotate` 下不产生 `certain`
- [ ] 接线完成：`IMPLEMENTED` 有 `double-rotate`、`PLANNED` 无；CLI 可跑
- [ ] `py -3.12 -m unittest discover -s tests -t .` 全绿
- [ ] 布局门 + 脱敏门 + 门自证三条命令全绿
- [ ] 三处状态副本 M3 → ✅（同提交）
- [ ] `plan/HANDOFF-M4.md` 七节齐

## 七、关键命令速查

```bash
# 门（每次新对话第一件事）
py -3.12 tools/check_sprint_layout.py
py -3.12 tools/check_desensitized.py
py -3.12 tools/verify_gates.py

# 测试
py -3.12 -m unittest discover -s tests -t .
py -3.12 -m unittest tests.test_m3_double_rotate -v

# 生成 fixtures（产物不入仓）：先跑这个才能就地复算样本
py -3.12 fixtures/gen_all.py
py -3.12 fixtures/gen_all.py --check            # 严格：四族全集两层断言
py -3.12 fixtures/gen_double_rotate.py --check   # 单族（非严格）

# M3 基线：先用 M2 的 orientation 看三份 m3_* 的 sources
$env:PYTHONPATH="src"; py -3.12 -m imageoracle orientation --json fixtures/out/m3_ifd1_unsynced.jpg
$env:PYTHONPATH="src"; py -3.12 -m imageoracle double-rotate --json fixtures/out/m3_xmp_residual.jpg

# 查看帮助 / 版本
py -3.12 -m imageoracle --help
py -3.12 -m imageoracle --version
```
