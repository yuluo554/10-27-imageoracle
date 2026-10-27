# HANDOFF-M2 — orientation 判定器（题目 M1）

> 上一棒：**M1 数据先行（✅）**。下一棒：**M2 orientation 判定器**。
> 本文件是第 2 棒的**入口交接单**；动手前先跑两道门（见 §七）。

## 一、当前进度 + 证据

**M1 已完成并验证**（2026-10-27）：

| 交付 | 证据 |
|---|---|
| 四族生成器拆族 | `fixtures/gen_orientation.py` / `gen_double_rotate.py` / `gen_icc.py` / `gen_container.py` + 聚合器 `gen_all.py`；共用外壳 `fixtures/lib/generator.py` |
| 样本扩到 51 份 | M2 22 + M3 3 + M4 11 + M5 15；`fixtures/manifest.json` 冻结 **51 条 sha256** |
| `--check` 位级一致 | `py -3.12 fixtures/gen_all.py --check` → **一致**（第一层 51 条全集；第二层冻结产物 51/51） |
| 单族可独立核对 | 四个族各自 `--check` → 全部**一致**（严格集合相等只在聚合器） |
| 冻结值未被手改 | `tests/test_m1_manifest.py::test_sha256_and_len_are_frozen_truth`（重算 51 份字节 vs manifest） |
| M2 旧哈希未漂移 | `git diff fixtures/manifest.json`：只**新增** 29 条，原有 22 条 sha256 一行未改 |
| 生成器不 spawn 外部进程 | AST 双判据：属性级（`tests/test_fixtures.py`）+ import 级（`tests/test_m1_manifest.py`） |
| 单元测试 | `py -3.12 -m unittest discover -s tests -t .` → **65 tests OK** |
| 两道门 + 门自证 | `check_sprint_layout` / `check_desensitized` / `verify_gates` → **全绿（18/18）** |

**M2 现状**：`modules/orientation.py` **已在 M0 骨架期落地**（不是空白）。本棒本地基线实测
（`py -3.12 fixtures/gen_all.py` 生成产物后跑 CLI）：

- `m2_orient6_portrait.jpg` → `primary=6`、`effective_size={stored:[64,48], effective:[48,64]}`、`summary` 全 0（exit 0）
- `m2_orient8_portrait.jpg` → `primary=8`、`Rotate 270 CW`、W/H 交换（exit 0）
- `m2_orient6_be.tif`（大端 `MM`）→ `primary=6`（**按头字节序读，未固定小端**）✓
- `m2_absent.jpg` → `primary=null` + `orientation_absent`(info)（exit 0，**不是** 1）
- `m2_orient0_oor.jpg` / `m2_orient9_oor.jpg` / `m2_orient6_wrongtype.jpg` → `summary.error=1`（exit 2）
- `m2_orient6_noprefix.webp` / `m2_orient6_prefix.webp` → 均 `primary=6`（D10 双支）

⇒ **M2 本棒的主要工作是"对标 + 收口"，不是从零实现**：把 plan/05 §二 M2 出口门逐条钉到 fixtures 上，
补/核单测，然后翻 ✅。

**诚实口径**：以上全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**——任何文档都不得写"CI 绿"。

## 二、当前事实·状态不变量（下一棒动手前必须知道）

1. **manifest 只有一个写入者 = `fixtures/gen_all.py`**。单族生成器只写自己的产物字节，
   **不碰 manifest**（否则后跑的族会覆盖先跑的族）。单族 `--check` 用 `strict=False`（只核本族名字），
   聚合器 `--check` 用 `strict=True`（集合必须**恰好相等**）。
2. **`fixtures/out/` 不入仓**（`.gitignore` 封了全部图像后缀）。测试**不需要**产物：
   `test_m1_manifest` 与各族自检都在**内存里**重生成后比哈希。第二层（冻结产物比对）在缺件时显式 SKIP。
   要就地复算请先 `py -3.12 fixtures/gen_all.py`。
3. **`fixtures/` 里禁用 `.run(` / `.call(` / `.system(` / `.popen(`** 这些**属性名**：
   `tests/test_fixtures.py` 的 AST 判据会把 `x.run(...)` 读成"调外部 CLI"。
   共用外壳的入口因此叫 **`emit(...)`**，不叫 `run(...)`（本棒踩过一次）。
4. **不改任何 M1 已冻结样本的字节**。改了必须重跑 `gen_all.py` 并接受 manifest 变更；
   `--check` 会红是**设计如此**。**不要为了让 `--check` 变绿而手改 manifest**——
   `test_sha256_and_len_are_frozen_truth` 会当场抓住（重算 vs 冻结值）。
5. **状态行机读形态**：`| M<k> | … | <状态> |`，首格**恰好**是 `M<k>`。新增状态副本必须**三处同改**
   （`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态行）。
6. **退出码唯一出口 = `src/imageoracle/cli.py:exit_code_for`**；子命令不得自己 `sys.exit(数字)`。
7. **报告 `generated_at` 默认 `"1970-01-01T00:00:00Z"`**，包内**禁止读时钟**（AST 守门）；
   JSON 序列化唯一入口 = `report.render_json`（别处另写 `json.dumps` 会破双跑逐字节相等）。
8. **`modules.PLANNED` 是显式登记**：`double-rotate`/`color`/`container`/`consumers` 有契约占位文件但**没接线**，
   CLI 对它们返回 exit 3。M2 的 `orientation` 已在 `IMPLEMENTED` 里，**本棒不要动登记面**。
9. **M3 条件 3（大边启发式）的样本语义由 M3 定**：`m3_bigedge_mismatch.jpg` 按交接单原话造
   （**声明 6 + 容器宽>高**，80×40），只触发 `suspicion`。M2 棒**不需要**碰它。
10. **fixtures 造的是结构性样本**：工具读的字段（tag/偏移/长度/CRC/帧时序）精确，**像素不可解码**
    （manifest 的 `notes` 已写明）。别试图去解码 IDAT / 熵段。

## 三、下一棒待办（M2 orientation 判定器）

**目标**：把 plan/05 §二 M2 出口门**逐条对标 fixtures**，补/核单测，收口翻 ✅。

| # | 待办 | 完成判据 |
|---|---|---|
| 1 | 8 值逐项对 ExifTool 语义（`m2_orient1..8_portrait.jpg`） | 每值 `primary=N` + `label` 与 §1.1 原文逐字一致 |
| 2 | `6=CW90` / `8=CW270` 单测（断言文案引用 ExifTool 原文） | `tests/test_m2_orientation.py` 绿 |
| 3 | 5/6/7/8 交换 W/H；`m2_orient6_be.tif` 证明按头字节序读 | 单测 + 大端样本 |
| 4 | `absent` ≠ 1；越界（0/9）→ `error: orientation_out_of_range`；类型错 → `orientation_not_int16u` | 单测 + `summary.error` |
| 5 | PNG `eXIf` 双支（有/无 `Exif\0\0`）、WebP `EXIF` 双支（D10） | 四个样本 `primary=6` |
| 6 | 值 4 的规范形式 = `flip_v=True, rotate=0`（**不做等价化简**，K2） | 单测 |
| 7 | 回写三处状态副本 M2 → ✅（同提交） | 布局门 `STATUS` PASS |
| 8 | 写 `plan/HANDOFF-M3.md`（七节） | 布局门 `HANDOFFS` PASS |

**不要做**：不要在 M2 里实现 M3–M5 的判定逻辑；不要为了让样本"更好看"而改 M1 冻结产物。

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

## 五、本机环境坑（只写实测过的）

| 坑 | 实测现象 | 处置 |
|---|---|---|
| `python` 是 3.8.8 商店占位符 | `python --version` → 3.8.8 | 一律 `py -3.12` |
| Windows 默认代码页解不了中文输出 | `subprocess.run(text=True)` 抛 `UnicodeDecodeError` | 统一走 `tests/_helpers.run_cli()`（显式 `encoding="utf-8"`） |
| 直接跑 `py -3.12 fixtures/*.py` 时 `sys.path` 不含 `src/` 与 `fixtures/lib/` | `ModuleNotFoundError` | 生成器自己注入路径（`fixtures/lib/generator.py` 已统一注入） |
| fixtures 里 `x.run(...)` 会被 AST 判据读成"调外部 CLI" | `test_no_external_toolchain` 假红 | 共用外壳入口取名 `emit(...)`，别用 `run`/`call` 等保留属性名 |
| 本机无 exiftool/jpegtran/sharp/magick | `which` 全部 not found | 全部 fixture 纯 Python 字节构造（K14） |
| 安全钩子拦子进程拼接 | 早期门自证脚本被拦 | 门自证改为**进程内 import 门模块调 `main()`**，无子进程 |
| 单族生成器误写 manifest 会覆盖其他族 | manifest 只剩最后跑的那一族 | manifest 只在 `gen_all.py` 写；单族只写产物字节 |

## 六、DoD 逐项 checklist（M2 出口）

- [ ] 8 值逐项对 ExifTool 语义（`m2_orient1..8`），label 与原文逐字一致
- [ ] `6=CW90` / `8=CW270` 单测绿（断言文案引用 ExifTool 原文）
- [ ] 5/6/7/8 交换 W/H；大端 `MM` TIFF 按头字节序读
- [ ] `absent` ≠ 1；越界/类型错 → `error`（exit 2）
- [ ] PNG `eXIf` 双支 + WebP `EXIF` 双支（D10）
- [ ] `py -3.12 -m unittest discover -s tests -t .` 全绿
- [ ] 布局门 + 脱敏门 + 门自证三条命令全绿
- [ ] 三处状态副本 M2 → ✅（同提交）
- [ ] `plan/HANDOFF-M3.md` 七节齐

## 七、关键命令速查

```bash
# 门（每次新对话第一件事）
py -3.12 tools/check_sprint_layout.py
py -3.12 tools/check_desensitized.py
py -3.12 tools/verify_gates.py

# 测试
py -3.12 -m unittest discover -s tests -t .

# 生成 fixtures（产物不入仓）：先跑这个才能就地复算样本
py -3.12 fixtures/gen_all.py
py -3.12 fixtures/gen_all.py --check        # 严格：四族全集两层断言
py -3.12 fixtures/gen_orientation.py --check  # 单族（非严格）

# 跑 CLI（不安装）
$env:PYTHONPATH="src"; py -3.12 -m imageoracle orientation --json fixtures/out/m2_orient6_portrait.jpg

# 查看帮助 / 版本
py -3.12 -m imageoracle --help
py -3.12 -m imageoracle --version
```
