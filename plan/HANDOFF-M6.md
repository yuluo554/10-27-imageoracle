# HANDOFF-M6 — consumers 矩阵 + 发布（收官交接单）

> 上一棒：**M5 container 校验器（✅）**。本棒：**M6 consumers 矩阵 + 发布**。
> **本棒状态：本地交付完成（测试 222 项 + 三道门全绿）；发布动作（commit / tag / 公开仓库 / push /
> Release）未执行** → 三处状态副本的 M6 **仍是 ⬜**。下一棒（或本棒授权后）从 §三 #1 接着走。

## 一、当前进度 + 证据

**M6 本地交付**（2026-10-27）：

| 交付 | 证据 |
|---|---|
| 9 行 × 6 列消费者矩阵（chrome / safari / firefox / macos_preview / windows_photos / imagemagick / libvips / sharp / exiftran） | `modules/consumers.py::MATRIX_ROWS`；`TestMatrixShape`（9 行、5 列 + evidence、取值词表） |
| 每行 `evidence.kind ∈ {spec, tool-doc, hn-quote}` + `confidence ∈ {certain, single-source, gray}` | `TestMatrixShape.test_every_row_has_evidence` / `test_confidence_vocabulary_and_gray_rows` |
| `tool-doc` 行 = URL + 原文片段（**只有 2 行**：sharp / ImageMagick） | `data/README` §3.1（本棒逐字复核）；`test_tool_doc_rows_have_url_and_excerpt` |
| 13 条风险清单（`consumer/risk/severity/trigger/confidence/evidence`） | `RISKS`；`TestRisksMatchDataReadme` / `test_severity_is_risk_vocabulary_not_finding_vocabulary` |
| 6 条加工命令 diff（≥4 条硬验收） | `PROCESS_DIFFS`；`test_at_least_four_commands_including_required` |
| `--strip safe` 丢 `gAMA`/`cHRM`、保留 `cICP, iCCP, sRGB, pHYs, acTL, fcTL, fdAT` | `test_strip_safe_drops_gama_keeps_iccp`（判据源＝§1.13 条款原文） |
| 按字节事实命中风险（APNG→R07 / gAMA→R06 / IFD1→R05 / XMP→R02 / PNG `eXIf`→R03 / `iCCP`→R04） | `TestRuntimeOnAllSamples`（54 份样本逐个跑真 CLI）+ `test_gif_does_not_trigger_png_risks` 反证 |
| `--selftest-evidence` 覆盖三张表（缺 evidence / `tool-doc` 缺 URL / confidence 越界都红） | `report.selftest_evidence_complete`；`TestSelftestCatchesMissingEvidence`（4 条反证） |
| 台账逐格对账（§1.13 条款 + §8.9 矩阵/风险/diff 三张表） | `TestClausesMatchDataReadme` / `TestMatrixMatchesDataReadme` / `TestRisksMatchDataReadme` / `TestProcessDiffs` |
| 接线三处同改 + `PLANNED` 清空 | `modules.IMPLEMENTED` 有 `consumers`、`PLANNED == {}`；`TestWiring` + `test_cli_contract.TestModuleRegistration` |
| 人读矩阵表（文本模式） | `report.render_text`；`test_text_output_renders_matrix` |
| 单元测试 | `py -3.12 -m unittest discover -s tests -t .` → **222 tests OK** |
| 三道门 | `check_sprint_layout` / `check_desensitized` / `verify_gates`（18/18）→ **全绿** |
| 发布留档 | `plan/RELEASE-M6.md` §一 tag 前事实 / §二 tag 后待回填 / §三 出口门对账（8 条） |

**诚实口径**：以上全部是**本地等价校验**。仓库**无远端**，**一次 CI 都没跑过**；
发布动作**一步都没执行**——任何文档都不得写"CI 绿"或"已发布"。

## 二、当前事实·状态不变量（下一棒动手前必须知道）

1. **M6 是末棒 + 发布棒**：本地交付已完，**发布未执行**。`plan/05` §三 的 7 步顺序不可交换；
   `plan/RELEASE-M6.md` §二 是发布事实的唯一回填处。
2. **三处状态副本（`plan/00` 里程碑表 / `plan/05` §二 / `README.md` 状态行）此刻都是 M6 ⬜**。
   翻 ✅ 的前置条件 = tag + Release + 附件 sha256 落进 §二；否则就是"把未执行写成已完成"（红线）。
3. **`consumers` 只出 `info` finding**，风险清单的 `severity`（`high/medium/low/unknown`）
   **不进 `exit_code_for`**。理由写在 `data/README` §8.9 末段：它预言"你若跑某条命令会发生什么"，
   不是文件缺陷；且 `always` 触发的风险会让每张图都 exit 1。
4. **表体的唯一定义处 = `data/README` §8.9**（矩阵/风险/diff 三张表），条款原文 = §1.13。
   改矩阵值、加风险、加 diff 命令，都要先改 §8.9/§1.13，再改 `modules/consumers.py`，再改测试——
   否则 `TestMatrixMatchesDataReadme` 立刻红。
5. **`tool-doc` 只能给已逐字复核的页面**（当前 2 行：sharp `rotate()`、ImageMagick `-auto-orient`，
   URL 在 §3.1）。取不到页面的工具（exiftran / oxipng / jpegtran / libvips 参数页）挂
   `spec` 或 `hn-quote`，并在 §9 #13 登记——**不许编地址**（D20）。
6. **`gray` 行的 `unknown` 是声明，不是遗漏**：Firefox / macOS Preview / Windows 照片 / libvips autorot
   都没有第一方文档（§9 #11–#13），矩阵里一律 `unknown`，测试断言 `gray` 行 ≥2 个 `unknown` 格。
7. **`modules.PLANNED` 现在是空表**。新增模块要四处同改：`cli.COMMANDS`、`IMPLEMENTED`、
   `_help_for`、`_run_one` 的 payload 键；`TestModuleRegistration` 从**真 CLI** 采面（K15）。
8. **`selftest_evidence_complete` 现在吃两个面**：`findings`（spec + quote）与
   `consumers` / `risks` / `process_diffs`（kind + quote + tool-doc 的 URL + confidence 词表）。
   呈现层只做形态校验，**不查条款是否存在**（那是 `tests/test_specs` + `test_m6` 的事）。
9. **版本真源两处**：`src/imageoracle/__init__.py` + `pyproject.toml` = **`0.5.0`**；
   `README.md` 的 `版本：\`0.5.0\`` 与状态行也要同步（`test_readme_status_shows_version`）。
10. **发布附件口径（D13）**：`git archive --format=tar.gz v0.5.0` 手工出包；附件 sha256 **只写
    Release 正文 / `plan/RELEASE-M6.md` §二**，**不写进 tag 树内的文档**（自指失效）。
11. **tag 之后只允许非交付面提交**：`plan/`、`docs/`、`tests/`、`tools/`、`README.md`、`AGENTS.md`。
    `src/`、`pyproject.toml` 有差异 = 发布物变了，必须重发版本。
12. **CI 从未实跑**：`plan/05` §四 #1 保持 ⬜，直到首推后回填真实 run id。
13. **布局门的三个连带点**（翻 ✅ 时会红）：`LAYOUT.RELEASE` 要 `plan/RELEASE-M6.md` 在位
    （已在位）；`LAYOUT.RELEASE` 还要求两栏标题与 ≥3 行"实现/不适用/待首推"；`LAYOUT.GAPS`
    要求 `plan/06` 缺口表**不再出现 M6**（已改成"待发布动作执行"）。
14. **假阳性代价与不可判项全部显式**：`consumers` 不引入新的启发式；M5 的 `unit_mismatch`
    假阳性（§8.3）、M3 条件 3 的假阳性（§8.6）原样保留，不得在本棒"顺手收紧"。

## 三、下一棒待办（发布 + 后续）

| # | 待办 | 完成判据 |
|---|---|---|
| 1 | 取得发布授权后：`git add -A` → `commit`（含本棒全部改动） | `git status` 干净；提交信息点明 M6 |
| 2 | `git tag -a v0.5.0 -m "…"` | `git tag -l v0.5.0` 有输出；tag 指向该提交 |
| 3 | 建 GitHub 公开仓库 `yuluo554/10-27-imageoracle` 并 `push origin main` + `push origin v0.5.0` | `gh repo view` 可读；两个 ref 都在远端 |
| 4 | `git archive --format=tar.gz v0.5.0` 出源码包到中立目录，复算 sha256 | 重建一次 `cmp` 逐字节相等（`plan/RELEASE-M6.md` §三 第 1 行） |
| 5 | `gh release create v0.5.0 <tarball> --notes-file <留档正文>` | 附件 sha256 **只**出现在 Release 正文与 §二 |
| 6 | 回填 `plan/RELEASE-M6.md` §二（tag / run id / 附件 sha256）+ 三处状态副本 M6 → ✅ | 布局门 `STATUS` + `RELEASE` PASS；`git log --oneline v0.5.0..HEAD` 只含非交付面 |
| 7 | 首推后回填 CI run id（branch + tag 两条）到 `plan/05` §四 #1 与留档 §二 #7 | 两条 run 都绿，且 run id 是**真实**的 |

**不要做**：不要把"未实跑 CI"写成"CI 绿"；不要在 tag 之后改 `src/`/`pyproject.toml`；
不要给取不到页面的工具编 `tool-doc` URL；不要把 `unknown` 格按常识补成 `yes`；
不要让风险清单的 severity 折进退出码（那要先改 §8.9 与 `cli.exit_code_for`）。

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
| K8 | `evidence.spec` 必须在 `specs.CLAUSES` 里；条款原文逐字 | `test_specs` + `selftest_evidence_complete` + `test_m6_consumers` |
| K9 | 分层：readers↛modules、modules↛report、report↛readers | `test_layering.TestLayering` |
| K10 | 零第三方 import、零网络 import、无 `zlib.decompress`（readers/modules）、包内不读时钟 | `test_layering.TestRedLines` |
| K11 | 版本号两处一致（`__init__.py` + `pyproject.toml`） | `test_version_two_places_agree` |
| K12 | 状态行形态 `\| M<k> \| …`，首格恰好是里程碑号 | 布局门 `STATUS_LINE` |
| K13 | manifest 的 sha256 是 **3.12 冻结值**；跨解释器只断言解析一致 | `tests/test_m1_manifest.py` + `plan/05` §四 #4 |
| K14 | fixtures 不得调用外部 CLI（AST 判据：属性级 + import 级） | `test_no_external_toolchain` / `test_no_external_process_imports` |
| K15 | `modules.PLANNED` 与 `IMPLEMENTED` 必须与 CLI **实际暴露面**一致（末棒 `PLANNED` 为空） | `test_cli_contract.TestModuleRegistration` |
| K16 | `data/README` §1.1/§8.1、§1.10/§8.6、§1.11/§8.2/§8.7 各是唯一定义处 | 对应 `Test*MatchDataReadme` |
| K17 | M3 读 `orientation.analyze()` 的 sources；XMP 正则唯一实现 = `read_xmp_orientation`（M6 复用同一实现） | `test_m3_double_rotate` / `test_m6_consumers` |
| K18 | 条件 2 不收"一方缺失"分支（D17）；条件 3 只出 `suspicion`（D18） | `TestConditionBoundaries` |
| K19 | M4：PNG `iCCP` 不解压 → `unknown`（D9）；`cmyk_jpeg` 只在四分量 JPEG 上（D19） | `TestDoubleCarrierBehaviour` + `test_cmyk_jpeg_is_warning` |
| K20 | M4 默认假设表 7 行 = `data/README` §8.7；不得出现笼统"都假设 sRGB" | `tests/test_m4_defaults.py` |
| K21 | CRC 覆盖 = chunk type + data（不含 length）；已知向量 `b"IEND"` → `0xAE426082` | `test_m5_container.TestCrcKnownVector` |
| K22 | 帧时长归一化整数口径（§8.3）；AVIF = `not-in-band` | `test_m5_container.TestFrameDurations` |
| K23 | M5 级别表 = `data/README` §8.8；条款原文 = §1.12 | `TestSeverityTableMatchesDataReadme` / `TestClausesMatchDataReadme` |
| K24 | `unit_mismatch` 判据 = 假读值恰为 100 ms 且声明值不是；假阳性代价已声明（§8.3） | `test_gif_delay_written_in_ms_reports_unit_mismatch` |
| K25 | `consumers` 只出 `info`；风险 severity 用 risk 词表且**不参与** `exit_code_for` | `TestRuntimeOnAllSamples` / `test_severity_is_risk_vocabulary_not_finding_vocabulary` |
| K26 | 矩阵/风险/diff 三张表 = `data/README` §8.9 的机器可读副本（9 行、13 条、6 条） | `TestMatrixMatchesDataReadme` / `TestRisksMatchDataReadme` / `TestProcessDiffs` |
| K27 | 证据形态：`tool-doc` 必须 URL；`gray` 行必须 ≥2 个 `unknown` 格；`spec` 必须已登记 | `TestMatrixShape` / `selftest_evidence_complete` |

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
| `ICCP`/`iCCP` 样本在 `color` 下可能 exit 2（`unknown`） | 断言写死 exit 0 会红 | 断言按样本给 `expected_code`；`unknown` 计入 2 是设计（§8.5） |
| **Markdown 表解析：表头分隔行会把一张表切成两半** | `_tables_under` 首版把 `\|---\|---\|` 当成"表结束"，每张表只剩表头（本轮实测：§1.13 解析出 0 行） | 分隔行必须 `continue`，不能走"断表"分支（`tests/test_m6_consumers.py::_tables_under`） |
| WebFetch 取官方文档页会被重定向/拒绝 | ImageMagick 302 到 `/command-line-options/`；exiftran man 页 302 后 404；oxipng README 连接重置 | 只在**取到并逐字命中**时才写 `tool-doc`（§3.1）；否则挂 `spec`/`hn-quote`，地址进 §9 #13 |
| 台账原文与页面现状可能漂移 | ImageMagick `-auto-orient` 第三句已改写（§3.1 记录了漂移） | **按 §3 原文保留判据**（改会打挂 M3 单测），漂移只登记、不悄悄改 |

## 六、DoD 逐项 checklist（M6 出口）

- [x] 消费者矩阵 9 行 × 6 列齐，每行 `evidence.kind ∈ {spec, tool-doc, hn-quote}`
- [x] `tool-doc` 行有 URL + 原文片段；`confidence ∈ {certain, single-source, gray}`
- [x] 风险清单每条带 evidence + confidence（13 条）
- [x] 处理前后 diff ≥4 条加工命令（实际 6 条：oxipng safe/all/fix、sharp、exiftran、jpegtran）
- [x] `--selftest-evidence` 在 consumers 上通过（缺 evidence 的行 → 失败，附反证测试）
- [x] 接线完成：`IMPLEMENTED` 有 `consumers`、`PLANNED` 空；CLI 可跑
- [x] 版本号两处一致（`0.5.0`）；`README.md` 版本行同步
- [x] `py -3.12 -m unittest discover -s tests -t .` 全绿（222 项）
- [x] 布局门 + 脱敏门 + 门自证三条命令全绿（18/18）
- [x] `plan/RELEASE-M6.md` 三节齐；§三 出口门对账 8 条
- [ ] **tag + Release + 附件 sha256**（未执行；见 §三 #1–#6）
- [ ] 三处状态副本 M6 → ✅（**同上，发布后才翻**）
- [x] 收官交接单七节齐（本文件）

## 七、关键命令速查

```bash
# 门（每次新对话第一件事）
py -3.12 tools/check_sprint_layout.py
py -3.12 tools/check_desensitized.py
py -3.12 tools/verify_gates.py

# 测试
py -3.12 -m unittest discover -s tests -t .
py -3.12 -m unittest tests.test_m6_consumers -v

# 生成 fixtures（产物不入仓）：先跑这个才能就地复算样本
py -3.12 fixtures/gen_all.py
py -3.12 fixtures/gen_all.py --check            # 严格：四族全集两层断言
py -3.12 fixtures/gen_container.py --check      # 单族（非严格）

# M6 基线（consumers）
$env:PYTHONPATH="src"; py -3.12 -m imageoracle consumers --json fixtures/out/m5_frames_100ms.apng
$env:PYTHONPATH="src"; py -3.12 -m imageoracle consumers --json fixtures/out/m5_png_gama_after_idat.png
$env:PYTHONPATH="src"; py -3.12 -m imageoracle consumers --json --selftest-evidence fixtures/out/m3_ifd1_unsynced.jpg
$env:PYTHONPATH="src"; py -3.12 -m imageoracle consumers fixtures/out/m5_frames_100ms.apng      # 人读矩阵表

# 发布（未执行；需显式授权）
git tag -a v0.5.0 -m "imageoracle v0.5.0"
git archive --format=tar.gz -o <中立目录>/imageoracle-v0.5.0.tar.gz v0.5.0
gh release create v0.5.0 <tarball> --notes-file <留档正文>

# 版本
$env:PYTHONPATH="src"; py -3.12 -m imageoracle --version
```

> **M6 出口门原文**（`plan/05` §二）：每行有 evidence（`selftest_evidence_complete` 绿）；
> ≥4 条加工命令 diff；tag + Release + 留档。**前两条已达成，第三条未执行。**
