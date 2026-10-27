# HANDOFF-M4 — color 体检器（题目 M3）

> 上一棒：**M3 双重旋转探测器（✅）**。下一棒：**M4 color 体检器**。
> 本文件是第 4 棒的**入口交接单**；动手前先跑三道门（见 §七）。

## 一、当前进度 + 证据

**M3 已完成并验证**（2026-10-27）：

| 交付 | 证据 |
|---|---|
| 条件 1（IFD1 未同步）`certain` | `tests/test_m3_double_rotate.py::TestFixturesAgainstExitGate::test_condition_1_ifd1_unsynced`（`m3_ifd1_unsynced.jpg` 跑真 CLI） |
| 条件 2（XMP 残留，sharp #4585）`certain` | `test_condition_2_xmp_residual`（`m3_xmp_residual.jpg`：EXIF=1 / XMP=6） |
| 条件 3（大边启发式）**只出** `suspicion` | `test_condition_3_bigedge_is_suspicion_only`（断言 `certain == []`、`gray-heuristic`、exit 0） |
| `certain` / `heuristic` 分列 | `test_certain_and_heuristic_are_separate_fields`（两列表无同一条件，置信度字段互斥） |
| 每条 verdict 带 software × 触发链 × 后果 × evidence | `test_verdicts_carry_consumer_trigger_chain_consequence_evidence` + `test_three_consumers_are_covered`（sharp / jpegtran / ImageMagick 三例） |
| manifest 冻结真值 → 真输出对账 | `test_manifest_triggers_match_real_output`（解析 `fixtures/manifest.json` 的 `m3_*` triggers） |
| 无误报（M2 22 份好样本不产生 `certain`） | `TestNoFalseCertainOnGoodSamples::test_no_certain_on_m2_samples` |
| 基线 findings 不降级（越界/类型错仍 exit 2） | `TestNoFalseCertainOnGoodSamples::test_error_samples_keep_exit_2` |
| 边界反证（IFD1 缺失 / XMP 缺失 / 1–4 不评估 / 存储纵向不命中） | `TestConditionBoundaries`（4 条，就地造字节跑真 CLI） |
| 条款原文与 `data/README` §1.10 / §8.6 逐字对账 | `TestClausesMatchDataReadme`（3 条，解析表格，不另抄一份） |
| 接线三处同改 + 登记一致性判据 | `tests/test_cli_contract.py::TestModuleRegistration`（5 条；判据面从**真 CLI parser** 采） |
| 单元测试 | `py -3.12 -m unittest discover -s tests -t .` → **104 tests OK** |
| 三道门 + 门自证 | `check_sprint_layout` / `check_desensitized` / `verify_gates` → **全绿（18/18）** |

**M4 现状（本棒实测基线，动手前先复现）**：`modules/color.py` 是**契约占位**（`analyze()` 抛
`NotImplementedError`），CLI 里 `color` 未接线 → exit 3。fixtures 里 M4 那一族已经就位（11 份）：

- 四份 PNG `iCCP`：`m4_icc_ok.png`（合法流 + 128B 头全字段）/ `m4_icc_truncated.png` /
  `m4_icc_size_bad.png` / `m4_icc_acsp_bad.png`
- lr0 形态：`m4_lr0_form.png`（`iCCP` 无 `sRGB`、有 `gAMA`/`cHRM`）
- 互斥：`m4_iccp_srgb_conflict.png`；CMYK：`m4_cmyk_app14.jpg`
- **三类 ICC 损坏各有 JPEG APP2 孪生**（`m4_icc_truncated.jpg` / `m4_icc_size_bad.jpg` /
  `m4_icc_acsp_bad.jpg`）——PNG 侧只证明 `unknown`、JPEG 侧才证明 `error`（R5 的刻意范围限定）

**诚实口径**：以上全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**——任何文档都不得写"CI 绿"。

## 二、当前事实·状态不变量（下一棒动手前必须知道）

1. **条件 2 的"一方缺失"分支是 D17 刻意不实现的**，不是漏项。若 M4 想复用"两来源比对"的思路，
   同样先问"照抄题目原文会不会把最常见的好样本判成冲突"。
2. **条件 3 对规范的手机竖拍有已知假阳性**（D18），这是声明而非隐瞒；它只出 `suspicion`、
   **不进退出码**。M4 若引入新的启发式，同样必须"只出 `suspicion` + 在 `data/README` 声明代价"。
3. **基线 findings 必须透传**：M3 把 `orientation` 的 findings 一并带出，否则越界样本会在
   `double-rotate` 下静默变成 exit 0。M4 的 `color` 若也读 `orientation`/`double-rotate` 的产物，
   照此办理（`plan/01` §3：M1 的解析结果是 M2 的**超集**）。
4. **PNG `iCCP` 不解压是硬约束**（D9）：PNG 侧一律 `unknown: compressed_profile_not_inspected`，
   **不许**为了"让损坏样本报 error"而加 zlib 解压——两者是**协作的**：JPEG APP2 孪生样本才证明 `error`。
   `tests/test_layering.py::TestRedLines` 的 `zlib.decompress` 禁令会当场抓住。
5. **判据与阈值的唯一定义处是 `data/README`**：M3 新增了 §8.6（判据/级别/启发式）。M4 的
   校验项与级别**已在 §8.2 定义**，实现时直接引用，不要另立一套。
6. **条款原文的唯一定义处**：M3 新增 `data/README` §1.10（四条），测试解析该表逐字对账。
   M4 要用到的 `libvips icc_import` 原话（D2 的默认假设表依据）与 ICC 头字段（§1.2）
   **已在台账里**；新增 ID 必须先登记再引。
7. **默认假设表 7 行**是 M4 的硬验收（`plan/03` §三 第 7 项）——7 行**逐行带 `source`**，
   其中 D2 已定"不得写'大家都假设 sRGB'"，libvips 那条原话在 `data/README` §3。
8. **接线要三处一起改**：`modules/color.py` 去占位 → `modules.IMPLEMENTED` 里登记 →
   `modules.PLANNED` 里删掉 `color`。`tests/test_cli_contract.py::TestModuleRegistration` 会红。
9. **退出码只认 `cli.py:exit_code_for`**（K4/K5）。新增 severity 前先看 `data/README` §8.5；
   `unknown` 计入 2，`suspicion` 不在判据里。
10. **状态行机读形态**：`| M<k> | … | <状态> |`，首格**恰好**是 `M<k>`；翻状态必须**三处同改**
    （`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态行）。`plan/05` §一 映射表刻意写成
    `| color 体检器（M4） | … |`，**不要**改成 `| M4 |` 开头（K12）。
11. **改交付面（`src/`、`pyproject.toml`）必须同步升版本号两处**
    （`src/imageoracle/__init__.py` + `pyproject.toml`）。M3 落地已把版本从 `0.1.0` 升到 `0.2.0`；
    M4 落地 = 再升（`0.3.0`），并在 `CHANGELOG.md` 追一条。
12. **`fixtures/out/` 不入仓**；测试**不读产物**——把 `gen_*.build_all()` 的内存产出写到临时目录再跑 CLI
    （`tests/test_m3_double_rotate.py` 的 `_run_family` 是可复制的样板）。
13. **不改 M1 已冻结样本字节**（`fixtures/manifest.json` 的 sha256 是冻结真值，K13）。
14. **`fixtures/` 里禁用 `.run(`/`.call(`/`.system(`/`.popen(` 这些属性名**（AST 判据读成"调外部 CLI"）；
    共用外壳入口叫 `emit(...)`。
15. **报告 `generated_at` 默认 `"1970-01-01T00:00:00Z"`**，包内禁止读时钟；JSON 序列化唯一入口
    = `report.render_json`（别处另写 `json.dumps` 会破双跑逐字节相等）。

## 三、下一棒待办（M4 color 体检器）

**目标**：把 `plan/05` §二 M4 出口门**逐条对标** 11 份 `m4_*` 样本，实现判决 + 默认假设表，收口翻 ✅。

| # | 待办 | 完成判据 |
|---|---|---|
| 1 | ICC 存在性（APP2 多段拼接 + 段号 `i/n` 连续 / `iCCP` / `ICCP` / TIFF 34675） | `icc_missing`(info) / `icc_segment_gap`(error) 各命中 |
| 2 | 128B 头逐字段（`@36 == acsp`、`ProfileSize` vs 载体长度、`ProfileClass@12`、`ColorSpaceData@16`、`ProfileConnectionSpace@20`、`RenderingIntent@64`） | `m4_icc_ok.png` 全字段合法；三类损坏各命中（`plan/05` §二：截断 / `size` 错 / `acsp` 坏） |
| 3 | **PNG 侧不解压 → `unknown`；JPEG APP2 孪生 → `error`** | 六份样本（PNG 三 + JPEG 三）**两种行为都证明**（R5） |
| 4 | PNG `iCCP` ↔ `sRGB` 并存 → `warning: iccp_srgb_conflict` | `m4_iccp_srgb_conflict.png` 命中；措辞是 should not，**不得升格为 error** |
| 5 | `gAMA` / `cHRM` 有无组合 → `info`，逐组合标注 | `m4_lr0_form.png` 命中 lr0 形态（`iCCP present` / `sRGB absent` / `gAMA`,`cHRM` 有无） |
| 6 | CMYK JPEG（APP14 `transform`）→ `warning: cmyk_jpeg` | `m4_cmyk_app14.jpg` 命中（@amiantos 原话作**需求依据**，不作技术依据） |
| 7 | 位深（不解码能读到才报，否则 `unknown`） | JPEG SOF / PNG IHDR / WebP 三支各断言 |
| 8 | **默认假设表 7 行，逐行带 `source`** | 报告里逐行出现；`tests/test_m4_defaults.py` 断言 7 行 + 每行 `source` |
| 9 | 接线：`IMPLEMENTED` 登记 + 从 `PLANNED` 移除 + CLI 暴露 `color` | CLI 可跑；`test_cli_contract` 登记一致性绿 |
| 10 | 写 `tests/test_m4_color.py`：三类损坏各命中 + `unknown`/`error` 双行为 + 无误报 | 测试绿 |
| 11 | 升版本号两处（`0.3.0`）+ `CHANGELOG` 追一条 | `test_version_two_places_agree` 绿 |
| 12 | 回写三处状态副本 M4 → ✅（同提交） | 布局门 `STATUS` PASS |
| 13 | 写 `plan/HANDOFF-M5.md`（七节） | 布局门 `HANDOFFS` PASS |

**不要做**：不要在 M4 里实现 M5/M6 的判定逻辑；不要为了"报 error 好看"而给 PNG `iCCP` 加解压
（D9 是硬约束，且会破 `test_layering` 红线）；不要改 M1 冻结产物；不要把 `unknown` 降级成 `info`。

## 四、既定口径清单（K 编号，动了会打挂测试）

| K | 口径 | 动了会红 |
|---|---|---|
| K1 | 8 元变换矩阵 = `data/README` §8.1；`6→CW90`、`8→CW270` | `test_m2_orientation`（含断言文案） |
| K2 | 变换记录规范形式（4 = `flip_v`），**不做等价化简** | `test_value_4_is_spec_form_not_simplified` |
| K3 | 有效宽高只在 5/6/7/8 交换；`absent` ≠ `=1` | `test_swap_only_for_5_6_7_8` + `test_m3_double_rotate` |
| K4 | 退出码 0/1/2/3，优先级 3 > 2 > 1 > 0；`unknown` 计入 2；`suspicion` 不计入 | `test_cli_contract.TestExitCodes` |
| K5 | `exit_code_for` 全仓库只能有 1 处定义 | `test_exit_code_has_one_definition` |
| K6 | JSON 双跑逐字节相等；无浮点；`generated_at` 默认固定串 | `TestDeterminism` |
| K7 | 报告路径按入参原样输出（不 `abspath`） | 脱敏门 |
| K8 | `evidence.spec` 必须在 `specs.CLAUSES` 里；条款原文逐字来自 `data/README` | `test_specs` + `test_m3_double_rotate.TestClausesMatchDataReadme` |
| K9 | 分层：readers↛modules、modules↛report、report↛readers | `test_layering.TestLayering` |
| K10 | 零第三方 import、零网络 import、无 `zlib.decompress`（readers/modules）、包内不读时钟 | `test_layering.TestRedLines` |
| K11 | 版本号两处一致（`__init__.py` + `pyproject.toml`） | `test_version_two_places_agree` |
| K12 | 状态行形态 `\| M<k> \| …`，首格恰好是里程碑号 | 布局门 `STATUS_LINE` |
| K13 | manifest 的 sha256 是 **3.12 冻结值**；跨解释器只断言解析一致 | `tests/test_m1_manifest.py` + `plan/05` §四 #4 |
| K14 | fixtures 不得调用外部 CLI（AST 判据：属性级 + import 级） | `test_no_external_toolchain` / `test_no_external_process_imports` |
| K15 | `modules.PLANNED` 与 `IMPLEMENTED` 必须与 CLI **实际暴露面**一致 | `test_cli_contract.TestModuleRegistration`（本棒新增实物） |
| K16 | `data/README` §1.1/§8.1 是 label 与矩阵的唯一定义处；§1.10/§8.6 是 M3 的唯一定义处 | `TestWordingMatchesDataReadme` / `TestClausesMatchDataReadme` |
| K17 | M3 读 `orientation.analyze()` 的 `sources`；XMP 正则唯一实现 = `read_xmp_orientation` | `test_m3_double_rotate` + 分层判据 |
| K18 | 条件 2 不收"一方缺失"分支（D17）；条件 3 只出 `suspicion`（D18） | `TestConditionBoundaries` + `test_error_samples_keep_exit_2` |

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
| 断言写死 exit 码会在"合法 exit 0 的样本"上假红 | M3 首版 `_payload()` 写死 `exit 1`，条件 3 样本（`suspicion` → exit 0）当场红 | 断言按条件分别给 `expected_code`；`suspicion` 不进退出码是设计 |
| 大面积 `-A` 抓 grep 上下文时易误读表格行 | 手工核对时把 `plan/05` §一 映射表读成状态行 | 状态只认 `^\|\s*\*{0,2}M(\d+)\*{0,2}\s*\|`（K12） |

## 六、DoD 逐项 checklist（M4 出口）

- [ ] ICC 存在性：`icc_missing` / `icc_segment_gap` 各命中
- [ ] 128B 头逐字段：`m4_icc_ok.png` 合法；三类损坏（截断 / `size` 错 / `acsp` 坏）各命中
- [ ] PNG `iCCP` 走 `unknown`、JPEG APP2 孪生走 `error` —— **两种行为都有样本证明**（R5）
- [ ] `iccp_srgb_conflict`（warning，不升格 error）
- [ ] lr0 形态复现（`iCCP present` / `sRGB absent` / `gAMA`,`cHRM` 有无）
- [ ] `cmyk_jpeg`（warning）+ 位深三支
- [ ] 默认假设表 **7 行**逐行带 `source`
- [ ] 接线完成：`IMPLEMENTED` 有 `color`、`PLANNED` 无；CLI 可跑
- [ ] 版本号两处升到 `0.3.0`；`CHANGELOG` 追一条
- [ ] `py -3.12 -m unittest discover -s tests -t .` 全绿
- [ ] 布局门 + 脱敏门 + 门自证三条命令全绿
- [ ] 三处状态副本 M4 → ✅（同提交）
- [ ] `plan/HANDOFF-M5.md` 七节齐

## 七、关键命令速查

```bash
# 门（每次新对话第一件事）
py -3.12 tools/check_sprint_layout.py
py -3.12 tools/check_desensitized.py
py -3.12 tools/verify_gates.py

# 测试
py -3.12 -m unittest discover -s tests -t .
py -3.12 -m unittest tests.test_m4_color -v

# 生成 fixtures（产物不入仓）：先跑这个才能就地复算样本
py -3.12 fixtures/gen_all.py
py -3.12 fixtures/gen_all.py --check            # 严格：四族全集两层断言
py -3.12 fixtures/gen_icc.py --check            # 单族（非严格）

# M4 基线：先看 11 份 m4_* 里 ICC 的载体与长度
$env:PYTHONPATH="src"; py -3.12 -m imageoracle color --json fixtures/out/m4_icc_ok.png
$env:PYTHONPATH="src"; py -3.12 -m imageoracle color --json fixtures/out/m4_icc_truncated.jpg

# M2/M3 基线（M4 会复用它们的产物）
$env:PYTHONPATH="src"; py -3.12 -m imageoracle orientation --json fixtures/out/m4_lr0_form.png
$env:PYTHONPATH="src"; py -3.12 -m imageoracle double-rotate --json fixtures/out/m3_ifd1_unsynced.jpg

# 查看帮助 / 版本
py -3.12 -m imageoracle --help
py -3.12 -m imageoracle --version
```

> **M4 出口门原文**（`plan/05` §二）：lr0 形态复现；三类损坏各命中；默认假设表 7 行逐行带 `source`。