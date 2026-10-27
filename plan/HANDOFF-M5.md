# HANDOFF-M5 — container 校验器（题目 M4）

> 上一棒：**M4 color 体检器（✅）**。下一棒：**M5 container 校验器**。
> 本文件是第 5 棒的**入口交接单**；动手前先跑三道门（见 §七）。

## 一、当前进度 + 证据

**M4 已完成并验证**（2026-10-27）：

| 交付 | 证据 |
|---|---|
| ICC 四种载体（APP2 多段 / `iCCP` / `ICCP` / TIFF 34675） | `tests/test_m4_color.py::TestIccCarriers`（`m4_icc_multi_segment.jpg` / `m4_icc_tiff34675.tif`；`icc_missing` 逐条列载体名） |
| APP2 段号 `i/n` 连续性 → `icc_segment_gap`(error) | `test_segment_gap_is_error`（声明 3 段、实到 seq=1,3；顺序：present 后再报 gap） |
| 128B 头逐字段合法 | `test_ok_sample_is_fully_legal`（`m4_icc_ok.jpg` 六字段逐个断言；`summary.error==0 / warning==0`） |
| 三类损坏各命中（截断 / `size` 错 / `acsp` 坏） | `test_three_damage_classes_hit_on_jpeg_app2`（`m4_icc_{truncated,size_bad,acsp_bad}.jpg`，各带 facts 与 `spec=ICC-HEAD`） |
| **R5 双行为**：PNG 走 `unknown`、JPEG 孪生走 `error` | `test_three_damage_classes_hit_on_png_as_unknown` + `test_jpeg_twins_do_not_report_not_inspected` + `test_both_behaviours_present_in_one_family` |
| lr0 形态复现（`iCCP present (len=N)` / `sRGB absent` / `gAMA`,`cHRM`） | `test_lr0_form_reproduced` + `test_lr0_icc_present_message_shape`（`m4_lr0_form.png`） |
| `iccp_srgb_conflict` 是 warning（不升格） | `test_iccp_srgb_conflict_is_warning`（`facts.quote_says == "should not"`；`summary.error==0`） |
| `cmyk_jpeg` 是 warning + 只在四分量 JPEG 上命中 | `test_cmyk_jpeg_is_warning`；**收窄口径**见 `data/README` §8.2 与 `plan/06` D19 |
| 位深三支（JPEG SOF / PNG IHDR → info；WebP → unknown） | `test_bit_depth_reported_for_jpeg_and_png` / `test_bit_depth_unknown_for_webp` |
| **默认假设表 7 行逐行带 `source`** | `tests/test_m4_defaults.py`（表体 7 行 + 四字段非空 + 解析 `data/README` §8.7 逐字对账 + 报告里逐行出现） |
| 台账逐字：`specs/` 六条 = `data/README` §1.11 | `TestClausesMatchDataReadme`（解析 §1.11 表对账） |
| 级别逐条 = `data/README` §8.2 | `TestSeverityTableMatchesDataReadme`（解析 §8.2 表） |
| manifest 冻结真值 → 真输出对账 | `test_manifest_triggers_match_real_output`（解析 `fixtures/manifest.json` 的 `m4_*` triggers） |
| 无误报（M2 好样本不产生 error/warning） | `TestNoFalsePositiveOnGoodSamples` |
| 接线三处同改 + 登记一致性 | `tests/test_cli_contract.py::TestModuleRegistration`（K15，判据面从真 CLI parser 采） |
| 单元测试 | `py -3.12 -m unittest discover -s tests -t .` → **146 tests OK** |
| 三道门 + 门自证 | `check_sprint_layout` / `check_desensitized` / `verify_gates` → **全绿（18/18）** |

**M5 现状（本棒实测基线，动手前先复现）**：`modules/container.py` 是**契约占位**（`analyze()` 抛
`NotImplementedError`），CLI 里 `container` 未接线 → exit 3。fixtures 里 M5 那一族已经就位（15 份）：

- PNG：`m5_png_gama_after_idat.png`（`gAMA` 在 IDAT 后）/ `m5_png_idat_nonconsecutive.png` /
  `m5_png_bad_crc.png` / `m5_png_missing_crc.png`
- APNG：`m5_apng_numframes.png`（`num_frames` 与 `fcTL` 数不符）/ `m5_apng_seq_gap.png`（序号 0,1,3）
- WebP：`m5_webp_anmf_truncated.webp` / `m5_webp_anim_loop_swap.webp`
- GIF：`m5_gif_dispose4.gif` / `m5_gif_delay_ms.gif`
- 跨格式 100 ms：`m5_frames_100ms.{gif,apng,webp}`（三份，归一化后都应为 100）
- JPEG：`m5_jpeg_progressive_mixed.jpg` / `m5_jpeg_app14_pos.jpg`

**诚实口径**：以上全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**——任何文档都不得写"CI 绿"。

## 二、当前事实·状态不变量（下一棒动手前必须知道）

1. **判据与阈值的唯一定义处是 `data/README`**：M5 的检查项落在 §8.3（帧时长归一化）与 §1.3–§1.9
   （PNG 顺序 / CRC / APNG / WebP / GIF）；CRC 已知向量在 §1.4（`b"IEND"` → `0xAE426082`）。
   实现时直接引用，不要另立一套数值。
2. **`unknown` 计入退出码 2，`suspicion` 不计**（§8.5）。M5 若引入启发式，同样必须
   "只出 `suspicion` + 在 `data/README` 声明代价"（照 M3 条件 3 / D18 的先例）。
3. **`fixtures/lib/build.py` 已备好 M5 需要的字节构造器**：`png_chunk(..., crc=…)` / `include_crc=False`、
   `actl` / `fctl` / `fdat`、`anmf_payload` / `anim_payload` / `anim_payload_swapped` /
   `riff_chunk_raw`、`build_gif(frames=[(dispose, delay_cs)])`、`build_jpeg_segments` /
   `jpeg_segment` / `build_jpeg(..., trailing_segments=…)`。**不得另写一份**（两处实现会漂移）。
4. **`readers/` 只切结构、不判定**：CRC 计算在 `readers/png.py::compute_crc`（**chunk type + data**，
   不含 length），但"报不报错"在 `modules/container`。M5 只读 `container.chunks` / `.segments` /
   `.frames` / `.image_info`，**不重解析字节**。
5. **帧时长归一化的整数口径**（§8.3）：`gif = delay*10`；`apng = num*1000 // (den or 100)`；
   `webp = 原值`；`avif = not-in-band`。**不得出浮点**（`test_cli_contract.TestDeterminism::test_json_has_no_floats`）。
6. **APNG `fcTL`/`fdAT` 是否共享同一 `sequence_number` 序列**：`data/README` §1.6 标 ⚠️ 待逐字复核，
   §9 #10 仍在 ⬜；**生成器按"共享一个序列"构造**（读 `fixtures/lib/build.py::fctl`/`fdat` 的用法）。
   若复核推翻，先改生成器与 manifest，再改判决。
7. **`unit_mismatch` 是 M5 的核心判据**（10× / 1×）：`m5_gif_delay_ms.gif` 把 100 ms 按 ms 写成 100
   （正确应为 10）。判据面是"归一化值 × 倍率与声明单位自相矛盾"，不是"猜作者意图"。
8. **接线要三处一起改**：`modules/container.py` 去占位 → `modules.IMPLEMENTED` 里登记 →
   `modules.PLANNED` 里删掉 `container`。`tests/test_cli_contract.py::TestModuleRegistration` 会红。
9. **状态行机读形态**：`| M<k> | … | <状态> |`，首格**恰好**是 `M<k>`；翻状态必须**三处同改**
   （`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态行）。
   `plan/05` §一 映射表刻意写成 `| container 校验器（M5） | … |`，**不要**改成 `| M5 |` 开头（K12）。
10. **改交付面（`src/`、`pyproject.toml`）必须同步升版本号两处**。M4 落地已把版本从 `0.2.0` 升到 `0.3.0`；
    M5 落地 = 再升（`0.4.0`），并在 `CHANGELOG.md` 追一条。
11. **`fixtures/out/` 不入仓**；测试**不读产物**——把 `gen_*.build_all()` 的内存产出写到临时目录再跑 CLI
    （`tests/test_m4_color.py` 的 `_runs()` 是可复制的样板）。
12. **不改 M1 已冻结样本字节**（`fixtures/manifest.json` 的 sha256 是冻结真值，K13）。本棒为证明
    `icc_segment_gap`/多段拼接/TIFF 载体**新增**了 3 份 M4 样本、manifest 由 51 条变为 **54 条**；
    M5 若要新增样本，同样只**追加**、不修改既有字节。
13. **`fixtures/` 里禁用 `.run(`/`.call(`/`.system(`/`.popen(` 这些属性名**（AST 判据读成"调外部 CLI"）；
    共用外壳入口叫 `emit(...)`。
14. **报告 `generated_at` 默认 `"1970-01-01T00:00:00Z"`**，包内禁止读时钟；JSON 序列化唯一入口
    = `report.render_json`（别处另写 `json.dumps` 会破双跑逐字节相等）。
15. **证据面**：每条 finding 必须带 `evidence.spec`（在 `specs.CLAUSES` 里）+ `quote`（条款原文逐字）。
    M5 会用到 PNG-3 / APNG / WebP / GIF 条款——`specs/` 里**已在位**（M0 就立了），
    新增条款必须先登记 `data/README` 再引。

## 三、下一棒待办（M5 container 校验器）

**目标**：把 `plan/05` §二 M5 出口门**逐条对标** 15 份 `m5_*` 样本，实现判决 + 归一化帧时长表，收口翻 ✅。

| # | 待办 | 完成判据 |
|---|---|---|
| 1 | PNG chunk 顺序（IHDR 首 / IEND 末 / PLTE / `cHRM,cICP,gAMA,iCCP,sBIT,sRGB` / `bKGD,hIST,tRNS` / `acTL,eXIf,pHYs,sPLT` / `fcTL` / `fdAT`） | `m5_png_gama_after_idat.png` 命中顺序 error |
| 2 | CRC = `chunk type + data`（不含 length）+ 每个 chunk 都要有 | `m5_png_bad_crc.png` / `m5_png_missing_crc.png` 各命中；已知向量单测 `b"IEND"` → `0xAE426082` |
| 3 | `IDAT` 连续 | `m5_png_idat_nonconsecutive.png` 命中 |
| 4 | APNG：`num_frames == fcTL count`；首 `fcTL` 序号 0；序号单调无缺口无重复；`delay_den==0→100`；`acTL` 在首 IDAT 前 | `m5_apng_numframes.png` / `m5_apng_seq_gap.png` 各命中 |
| 5 | WebP：`ANIM`（BGRA / Loop u16）/ `ANMF` duration 24-bit ms / 内部边界 | `m5_webp_anmf_truncated.webp` / `m5_webp_anim_loop_swap.webp` 各命中 |
| 6 | GIF：disposal 含 4–7 / delay 1/100 s / GCE 位置 | `m5_gif_dispose4.gif` 命中 |
| 7 | JPEG 段顺序 + progressive 一致 + APP14 位置 | `m5_jpeg_progressive_mixed.jpg` / `m5_jpeg_app14_pos.jpg` 各命中 |
| 8 | 跨格式帧时长归一化到 ms + `unit_mismatch`（10× / 1×） | `m5_frames_100ms.{gif,apng,webp}` 归一化后**都等于 100**；`m5_gif_delay_ms.gif` 报 `unit_mismatch` |
| 9 | 接线：`IMPLEMENTED` 登记 + 从 `PLANNED` 移除 + CLI 暴露 `container` | CLI 可跑；`test_cli_contract` 登记一致性绿 |
| 10 | 写 `tests/test_m5_container.py`：每类 ≥2 例 + 归一化相等 + `unit_mismatch` + CRC 向量 | 测试绿 |
| 11 | 升版本号两处（`0.4.0`）+ `CHANGELOG` 追一条 | `test_version_two_places_agree` 绿 |
| 12 | 回写三处状态副本 M5 → ✅（同提交） | 布局门 `STATUS` PASS |
| 13 | 写 `plan/HANDOFF-M6.md`（七节） | 布局门 `HANDOFFS` PASS |

**不要做**：不要在 M5 里实现 M6 的判定逻辑；不要为了让样本"更坏"而改 M1 冻结产物；
不要输出浮点帧时长（一律整数 ms）；不要把 `unknown` 降级成 `info`。

## 四、既定口径清单（K 编号，动了会打挂测试）

| K | 口径 | 动了会红 |
|---|---|---|
| K1 | 8 元变换矩阵 = `data/README` §8.1；`6→CW90`、`8→CW270` | `test_m2_orientation` |
| K2 | 变换记录规范形式（4 = `flip_v`），**不做等价化简** | `test_value_4_is_spec_form_not_simplified` |
| K3 | 有效宽高只在 5/6/7/8 交换；`absent` ≠ `=1` | `test_swap_only_for_5_6_7_8` |
| K4 | 退出码 0/1/2/3，优先级 3 > 2 > 1 > 0；`unknown` 计入 2；`suspicion` 不计入 | `test_cli_contract.TestExitCodes` |
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
| K15 | `modules.PLANNED` 与 `IMPLEMENTED` 必须与 CLI **实际暴露面**一致 | `test_cli_contract.TestModuleRegistration` |
| K16 | `data/README` §1.1/§8.1（label/矩阵）、§1.10/§8.6（M3）、§1.11/§8.2/§8.7（M4）各是唯一定义处 | 对应 `Test*MatchDataReadme` |
| K17 | M3 读 `orientation.analyze()` 的 sources；XMP 正则唯一实现 = `read_xmp_orientation` | `test_m3_double_rotate` |
| K18 | 条件 2 不收"一方缺失"分支（D17）；条件 3 只出 `suspicion`（D18） | `TestConditionBoundaries` |
| K19 | M4：PNG `iCCP` 不解压 → `unknown`（D9）；`cmyk_jpeg` 只在四分量 JPEG 上（D19） | `TestDoubleCarrierBehaviour` + `test_cmyk_jpeg_is_warning` |
| K20 | M4 默认假设表 7 行 = `data/README` §8.7；不得出现笼统"都假设 sRGB" | `tests/test_m4_defaults.py` |
| K21 | CRC 覆盖 = chunk type + data（不含 length）；已知向量 `b"IEND"` → `0xAE426082` | 新增 M5 测试（本棒无实物，M5 补） |
| K22 | 帧时长归一化整数口径（§8.3）；AVIF = `not-in-band` | 新增 M5 测试（本棒无实物，M5 补） |

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
| PNG `iCCP` 样本在 `color` 下**必然 exit 2**（`unknown`） | 首版断言写死 exit 0，`m4_icc_ok.png` 当场红 | 断言按样本给 `expected_code`；`unknown` 计入 2 是设计（§8.5） |
| 条件 2 的"一方缺失"分支若照抄题目会把最常见好样本判冲突 | 见 D17 | 口径以 `data/README` §8.6 为准，不照抄题目原话 |
| `icc_segment_gap` 若在 `_icc_payload` 里顺手出 finding，会排在 `icc_present` **之前** | 顺序不直观、且拼接函数承担了两种职责 | 连续性判据单独出 `_segment_gap_finding(...)`，由 `_inspect_icc` 在 present 之后追加 |

## 六、DoD 逐项 checklist（M5 出口）

- [ ] PNG chunk 顺序违规命中（`gAMA` 在 IDAT 后）
- [ ] CRC 坏 / 缺 CRC 各命中；CRC 已知向量单测（`b"IEND"` → `0xAE426082`）
- [ ] `IDAT` 非连续命中
- [ ] APNG `num_frames` 不符 + 序号缺口各命中
- [ ] WebP `ANMF` 越界 + `ANIM` 字段错位各命中
- [ ] GIF disposal=4 命中
- [ ] JPEG 段顺序 / APP14 位置各命中
- [ ] 100 ms 三格式（GIF 10 / APNG 10/100 / WebP 100）归一化后**都等于 100 ms**
- [ ] 错写单位报 `unit_mismatch`（10×）
- [ ] 接线完成：`IMPLEMENTED` 有 `container`、`PLANNED` 无；CLI 可跑
- [ ] 版本号两处升到 `0.4.0`；`CHANGELOG` 追一条
- [ ] `py -3.12 -m unittest discover -s tests -t .` 全绿
- [ ] 布局门 + 脱敏门 + 门自证三条命令全绿
- [ ] 三处状态副本 M5 → ✅（同提交）
- [ ] `plan/HANDOFF-M6.md` 七节齐

## 七、关键命令速查

```bash
# 门（每次新对话第一件事）
py -3.12 tools/check_sprint_layout.py
py -3.12 tools/check_desensitized.py
py -3.12 tools/verify_gates.py

# 测试
py -3.12 -m unittest discover -s tests -t .
py -3.12 -m unittest tests.test_m5_container -v

# 生成 fixtures（产物不入仓）：先跑这个才能就地复算样本
py -3.12 fixtures/gen_all.py
py -3.12 fixtures/gen_all.py --check            # 严格：四族全集两层断言
py -3.12 fixtures/gen_container.py --check      # 单族（非严格）

# M5 基线：先看 15 份 m5_* 的结构与帧时长
$env:PYTHONPATH="src"; py -3.12 -m imageoracle container --json fixtures/out/m5_frames_100ms.gif
$env:PYTHONPATH="src"; py -3.12 -m imageoracle container --json fixtures/out/m5_apng_numframes.png
$env:PYTHONPATH="src"; py -3.12 -m imageoracle container --json fixtures/out/m5_png_bad_crc.png

# M4 基线（M5 会复用它的容器事实）
$env:PYTHONPATH="src"; py -3.12 -m imageoracle color --json fixtures/out/m4_icc_ok.jpg
$env:PYTHONPATH="src"; py -3.12 -m imageoracle color --json fixtures/out/m4_lr0_form.png

# 查看帮助 / 版本
py -3.12 -m imageoracle --help
py -3.12 -m imageoracle --version
```

> **M5 出口门原文**（`plan/05` §二）：每类 2 例；三格式 100 ms 归一化相等；错写报 `unit_mismatch`；
> CRC 已知向量单测。