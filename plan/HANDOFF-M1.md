# HANDOFF-M1 — 数据先行（fixtures 生成器）

> 上一棒：M0 计划与骨架（✅）。下一棒：**M1 数据先行**。
> 本文件是第 1 棒的**入口交接单**；动手前先跑两道门（见 §七）。

## 一、当前进度 + 证据

**M0 已完成并验证**（2026-10-27）：

| 交付 | 证据 |
|---|---|
| 计划套件 `plan/00–06` | 7 份齐备；布局门 `LAYOUT.SECTIONS` PASS（9 份小节） |
| 方法论装订 | `AGENTS.md` + `plan/00` 顶部装订行；`LAYOUT.BINDING_HEAD` PASS |
| 布局门 | `py -3.12 tools/check_sprint_layout.py` → **全绿（10 项 PASS，16 份必备件）** |
| 脱敏门 | `py -3.12 tools/check_desensitized.py` → **全绿（47 份文本，豁免自身 2 份）** |
| 门自证 | `py -3.12 tools/verify_gates.py` → **18/18 符合预期**（基线 2 + 布局 11 组 + 脱敏 5 组，逐条断言到具体判据 ID） |
| 包骨架 | 四层（readers → model → modules → report）+ CLI + `__main__`；`imageoracle --help` 可跑 |
| 单元测试 | `py -3.12 -m unittest discover -s tests -t .` → **54 tests OK** |
| orientation 已实现 | `imageoracle orientation --json <file>` 可跑：fixture `m2_orient6_portrait.jpg` → `primary=6`、`rotate_cw_deg=90`、`effective_size=[48,64]`（宽高已交换）、`summary` 全 0（exit 0） |
| fixtures 已起头 | `fixtures/gen_orientation.py` 产出 **22 个样本** + `fixtures/manifest.json` |
| CI 工作流 | `.github/workflows/ci.yml` 就位；**未接远端，待首推验证** |

**诚实口径**：以上全部是**本地等价校验**。仓库无远端，**一次 CI 都没跑过**——
任何文档都不得写"CI 绿"。

## 二、当前事实·状态不变量（下一棒动手前必须知道，否则会踩）

1. **本机没有 exiftool / jpegtran / sharp / magick / cjpeg**（2026-10-27 实测）。
   题目文档 `plan/01` 写的 `exiftool -Orientation#=N` 与 `jpegtran -copy all` **不能作为生成路径**；
   所有 fixture 必须由 `fixtures/lib/build.py` 纯字节构造。如果有人试图"先装 exiftool 再生成"，
   那会直接违反 `plan/04` §二 的真值纪律（哈希随工具链版本漂移）。
2. **`python` 是 3.8.8 商店占位符**。一律用 `py -3.12`。CI 矩阵是 3.10 + 3.12，
   所以语法**不得用 3.11+ 独有特性**（如 `typing.Self`、异常组）；`X | None` 是 3.10 可用的，允许。
3. **`fixtures/manifest.json` 已冻结 22 条 sha256**。改任何 fixture 的字节 = 必须重跑生成器
   并接受 manifest 变更；`--check` 会红（那是设计如此，不是 bug）。
   **不要为了让 `--check` 变绿而手改 manifest**——那等于把真值改成"我认为它是"。
4. **状态行机读形态**：`| M<k> | … | <状态> |`，首格**恰好**是 `M<k>`。
   `plan/05` §一 的映射表刻意写成 `| orientation 判定器（M2） | … |`，就是为了不被读成状态行。
   **新增状态副本时必须同步改写全部副本**（3 处：`plan/00` 里程碑表、`plan/05` 状态表、`README.md` 状态行）。
5. **布局门的 `STATUS_LINE` 已收窄**为 `^\|\s*\*{0,2}M(\d+)\*{0,2}\s*\|`。
   这是本轮门自证抓出的真缺陷（旧宽判据把 `plan/05` 映射表读成状态行，导致 6 个里程碑假红）。
   **别把这条判据改宽**。
6. **退出码唯一出口 = `src/imageoracle/cli.py:exit_code_for`**。任何子命令都不得自己 `sys.exit(数字)`。
   测试 `test_exit_code_has_one_definition` 会按 AST 数定义处数量（只能 1 处）。
7. **报告 `generated_at` 默认 `"1970-01-01T00:00:00Z"`**，且包内**禁止读时钟**（AST 守门）。
   想输出真实时间必须由调用方传 `--generated-at` 或 `SOURCE_DATE_EPOCH`。
8. **JSONB 序列化唯一入口 = `report.render_json`**（`sort_keys=True` / 固定分隔符 / 不允许 NaN/Infinity）。
   别在别处另写 `json.dumps`——双跑逐字节相等会破。
9. **`modules.PLANNED` 是显式登记**：`double-rotate` / `color` / `container` / `consumers` 有契约占位文件，
   但**没接线**，CLI 对它们返回 exit 3 并打印"计划于 M<k>"。实现某模块时，要把它从 `PLANNED`
   移到 `IMPLEMENTED`（`tests/test_cli_contract.py` 与 `test_fixtures.py` 会检查登记一致性）。
10. **`zlib.decompress` 在 `readers/` 与 `modules/` 里被 AST 守门禁止**。
    M4 若要读 PNG `iCCP` 的 profile 内省，必须先改这条判据并在 `plan/00` D9 说明理由
    （当前 D9 的结论是"首期不解压"，标 `unknown: compressed_profile_not_inspected`）。
11. **`.gitignore` 封了全部图像后缀**。`fixtures/out/` 与 `out/` 不入仓是**正确**状态；
    "解包树里没有 fixture"不是缺陷，README 已写前置条件（先跑生成器）。
12. **M0 不单出交接单**（`AGENTS.md` 豁免条 1）。`LAYOUT.HANDOFFS` 现在报 "0 份交接单齐"，
    这是合法终态；M1 完成后要写 `plan/HANDOFF-M2.md`。

## 三、下一棒待办（M1 数据先行）

**目标**：把 `fixtures/manifest.json` 扩到覆盖 M2–M6 全部验收样本，且生成器保持确定性。

| # | 待办 | 完成判据 |
|---|---|---|
| 1 | 补齐 M3 双重旋转族（`m3_*`）：XMP 残留、IFD1 未同步、大边启发式 | 3 类样本存在；`triggers` 写到 M3 的 code |
| 2 | 补齐 M4 ICC 族（`m4_*`）：正常 / 截断 / `size` 错 / `acsp` 坏 / `iCCP+sRGB` / CMYK APP14 / lr0 形态 | 7 类样本；三类损坏在 JPEG APP2 路径上可触发（PNG `iCCP` 走 `unknown`） |
| 3 | 补齐 M5 容器族（`m5_*`）：PNG 顺序 2 例 / CRC 2 例 / APNG 2 例 / WebP 2 例 / GIF 2 例 / JPEG 段序 / 100 ms 三格式 | 每类 2 例；`unit_mismatch` 样本存在 |
| 4 | 拆成 `gen_orientation.py` / `gen_double_rotate.py` / `gen_icc.py` / `gen_container.py` + `gen_all.py` 聚合 | `gen_all.py --check` 一次核对全部；自检挂在 `build_all()` 末尾 |
| 5 | 写 `tests/test_m1_manifest.py`：manifest 集合 == 生成器产出集合；每条有 triggers；no external CLI | 测试绿 |
| 6 | 回写：`plan/00` 里程碑表 M1 → ✅、`plan/05` 状态表、`README.md` 状态行（三处同提交） | 布局门 STATUS PASS |
| 7 | 写 `plan/HANDOFF-M2.md`（七节） | 布局门 HANDOFFS PASS |

**不要做**：不要在 M1 里实现任何判定逻辑（那是 M2–M5）；不要为了造样本去装外部工具链。

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
| K13 | manifest 的 sha256 是 **3.12 冻结值**；跨解释器只断言解析一致 | `plan/05` §四 #4 |
| K14 | fixtures 不得调用外部 CLI（AST 判据） | `test_no_external_toolchain` |
| K15 | `modules.PLANNED` 与 `IMPLEMENTED` 必须与 CLI 实际暴露面一致 | CLI 测试 + `test_fixtures` |

## 五、本机环境坑（只写实测过的）

| 坑 | 实测现象 | 处置 |
|---|---|---|
| `python` 是 3.8.8 商店占位符 | `python --version` → 3.8.8；`where python` 首项是 `WindowsApps` | 一律 `py -3.12` |
| Windows 默认代码页解不了中文输出 | `subprocess.run(text=True)` 抛 `UnicodeDecodeError: byte 0xc9` | 测试统一走 `tests/_helpers.run_cli()`（显式 `encoding="utf-8"`） |
| `tests/` 是包，helper 不能裸 import | `ModuleNotFoundError: No module named '_helpers'` | 用 `from tests._helpers import …` |
| 直接跑 `py -3.12 tools/<门脚本>.py` 时 `sys.path` 不含 `src/` | 门/生成器需要自己注入路径 | 生成器已 `sys.path.insert(0, ROOT/"src")`；门只读文件、不需要 `src` |
| 安全钩子拦 `subprocess.run` 拼接 | 门自证脚本首版被拦（命令注入告警） | 已改为**进程内 import 门模块调 `main()`**，无子进程 |
| 本机无 exiftool/jpegtran/sharp/magick | `which` 全部 not found | 全部 fixture 纯 Python 构造（K14） |

## 六、DoD 逐项 checklist（M1 出口）

- [ ] `fixtures/gen_all.py` 存在且可跑，`--check` 位级一致（两层断言：manifest + 冻结产物）
- [ ] manifest 覆盖 M2–M6 全部验收样本，每条含 `triggers`（module + code）
- [ ] 生成器确定性：两次构建字节相同（自检在 `build_all()` 末尾，不在 `__main__`）
- [ ] 生成器不调用外部 CLI（AST 判据绿）
- [ ] `py -3.12 -m unittest discover -s tests -t .` 全绿
- [ ] 布局门 + 脱敏门 + 门自证三条命令全绿
- [ ] 三处状态副本 M1 → ✅（同提交）
- [ ] `plan/HANDOFF-M2.md` 七节齐

## 七、关键命令速查

```bash
# 门（每次新对话第一件事）
py -3.12 tools/check_sprint_layout.py
py -3.12 tools/check_desensitized.py
py -3.12 tools/verify_gates.py

# 测试
py -3.12 -m unittest discover -s tests -t .

# 生成 fixtures（产物不入仓）
py -3.12 fixtures/gen_orientation.py
py -3.12 fixtures/gen_orientation.py --check

# 跑 CLI（不安装）
$env:PYTHONPATH="src"; py -3.12 -m imageoracle orientation --json fixtures/out/m2_orient6_portrait.jpg

# 查看帮助 / 版本
py -3.12 -m imageoracle --help
py -3.12 -m imageoracle --version
```
