# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)；日期为 UTC。

## [Unreleased] — v0.5.0

### M0 计划与骨架（2026-10-27）

- 计划套件 `plan/00`–`plan/06`：需求解读、架构与技术选型、模块详设（M2–M6 契约）、数据计划、
  里程碑与发布、交付对标与决策。
- 方法论装订：`AGENTS.md` 锚点 + `tools/check_sprint_layout.py` 布局门 +
  `plan/00` 顶部装订行；`tools/check_desensitized.py` 脱敏门；
  `tools/verify_gates.py` 对两道门做**变异验证**（18 组，逐条断言到底哪条判据红了）。
- 包骨架（零第三方依赖，Python ≥ 3.10）：
  - 容器层 `readers/`：`jpeg`（段切片）、`tiff`（IFD，**按头部字节序读**）、`png`（chunk + CRC 计算）、
    `webp`（RIFF，含 `ANIM`/`ANMF` 帧时长）、`gif`（块级，含 GCE disposal/delay）。
  - 语义层 `model/`：统一中间表示（Container / Chunk / Segment / Ifd / IccRef / Frame）。
  - 判决层 `modules/`：`orientation`（8 元变换矩阵 + 有效宽高）已实现；
    `double-rotate` / `color` / `container` / `consumers` 为**契约占位**，登记在 `modules.PLANNED`，
    CLI 对它们显式返回 exit 3 并报出计划里程碑。
  - 呈现层 `report/`：人读 + JSON 双轨同源；`generated_at` 默认固定串以保证逐字节可复现。
  - CLI `imageoracle`（`python -m imageoracle`）：子命令 `orientation`（已实现）；
    退出码唯一出口 `exit_code_for`（0/1/2/3）。
- fixtures：`fixtures/lib/build.py` 纯字节构造 + `fixtures/lib/manifest.py` 冻结真值；
  `fixtures/gen_orientation.py` 产出 22 个 orientation 族样本与 `fixtures/manifest.json`；
  `--check` 两层断言（manifest + 冻结产物）。
- 测试：47 项，标准库 `unittest`；含 6=CW90 单测、分层 AST 守门、零依赖/零网络守门、
  双跑逐字节确定性、只读不改源文件、退出码优先级。
- CI：`.github/workflows/ci.yml`（3.10/3.12 × ubuntu/windows + offline 作业）。
  **未接远端，CI 待首推验证**。

### M1 数据先行（2026-10-27）

- fixtures 拆族：`gen_orientation.py` / `gen_double_rotate.py` / `gen_icc.py` / `gen_container.py`
  四族各自 `build_all()` + 聚合器 `gen_all.py`（**唯一 manifest 写入者**）；
  共用外壳 `fixtures/lib/generator.py`（`--check` 两层断言 + 自检挂在调用链上）。
- `fixtures/lib/build.py` 扩到全容器面：XMP 包、APNG（`acTL`/`fcTL`/`fdAT`）、
  WebP RIFF（`VP8X`/`ANIM`/`ANMF`，含错位/越界形态）、GIF89a（GCE disposal/delay）、
  JPEG 段序自由拼装、ICC APP2 分片、PNG 色彩 chunk。
- 样本扩到 **51 份**（M2 22 + M3 3 + M4 11 + M5 15），全部冻结 `sha256`；
  三类 ICC 损坏**双承载**（PNG `iCCP` 走 `unknown`、JPEG APP2 走 `error`，R5）。
- 测试：`tests/test_m1_manifest.py`（集合/哈希重算/前缀↔模块/无进程 import/`--check` 位级一致）；
  全量 **65 项** `unittest` 绿。三处状态副本 M1 → ✅。

### M2 orientation 判定器（2026-10-27）

- `imageoracle orientation` 对标 `plan/05` §二 M2 出口门：8 值逐项对 ExifTool 语义、
  5/6/7/8 交换 W/H、大端 `MM` TIFF 按头字节序读、PNG `eXIf` / WebP `EXIF` 双支（D10）。
- `tests/test_m2_orientation.py`：label 与矩阵**解析 `data/README` §1.1/§8.1 表格**逐字对账，
  不在测试里另抄一份；`absent` ≠ 1、越界/类型错 → `error`；22 份样本逐条对标。
- 全量 **79 项** `unittest` 绿。三处状态副本 M2 → ✅（`version` 仍为 `0.1.0`——本棒未改交付面语义）。

### M3 双重旋转探测器（2026-10-27）

- `imageoracle double-rotate`（题目 M2）：三条件取或 —— IFD1 未同步（`certain`）/
  XMP 与 EXIF 274 冲突（`certain`，复现 sharp #4585）/ 大边启发式（`gray-heuristic` + `suspicion`）。
- 输出 `{condition_hits, certain, heuristic, verdicts}`：**`certain` 与 `heuristic` 分列**，
  不得混进同一得分；每条 verdict 给"软件 × 触发链 × 后果 × evidence"（sharp / jpegtran / ImageMagick 三例）。
- 基线 findings 原样透传：越界/类型错在 `double-rotate` 下仍是 exit 2，不因"换个子命令"被降级。
- 判据与阈值**唯一定义处** = `data/README.md` §8.6；M3 条款原文登记在 §1.10；
  `src/imageoracle/specs/` 增 `SHARP-AUTOORIENT` / `JPEGTRAN-COPYALL` / `IMAGEMAGICK-AUTOORIENT` /
  `GRAY-DECODE-REQUIRED` 四条（`evidence.spec` 必须可查，K8）。
- 两条**刻意**的边界（写进 `data/README` §8.6，不是遗漏）：条件 2 不实现"一方缺失且非 1"那一支
  （会把最常见的正常照片全判成冲突）；条件 3 对规范的手机竖拍形态有已知假阳性，
  只出 `suspicion`、不进退出码。
- 接线三处同改：`modules/IMPLEMENTED` 登记 + `modules/PLANNED` 移除 + CLI 暴露子命令与
  `--json` 字段；`tests/test_cli_contract.py` 新增 `TestModuleRegistration`（登记面从**真 CLI** 采，
  不是两个 dict 互比——K15 的实物）。
- 测试：`tests/test_m3_double_rotate.py`（三条件命中 + 分列 + 无误报 + 台账逐字 + 边界反证）；
  全量 **104 项** `unittest` 绿。三处状态副本 M3 → ✅。**版本升到 `0.2.0`**（交付面变更）。

### M4 color 体检器（2026-10-27）

- `imageoracle color`（题目 M3）对标 `plan/05` §二 M4 出口门：ICC 四种载体（JPEG APP2 多段拼接
  + 段号 `i/n` 连续性 / PNG `iCCP` / WebP `ICCP` / TIFF tag 34675）、128B 头逐字段
  （`ProfileSize` / `ProfileClass@12` / `ColorSpaceData@16` / PCS@20 / `acsp`@36 / `RenderingIntent@64`）、
  PNG `iCCP↔sRGB` 互斥、`gAMA`/`cHRM` 组合、位深三支、CMYK JPEG。
- **R5 双承载行为**：PNG `iCCP` 首期**不解压** → `unknown: compressed_profile_not_inspected`；
  三类损坏（截断 / `size` 错 / `acsp` 坏）各配一份 JPEG APP2 孪生样本证明 `error`。
  两条行为都有样本证明，范围限定不退化成漏实现。
- **默认假设表 7 行**（`data/README` §8.7 为唯一定义处）逐行带 `source`：报告里
  `default_assumptions` 逐行出现；`tests/test_m4_defaults.py` 解析 §8.7 表逐字对账，并断言
  不出现"大家都假设 sRGB"这类笼统措辞（`plan/00` D2）。
- 新增条款 `ICC-CARRIERS` / `ICC-NOT-INSPECTED` / `ICC-DEFAULTS` / `CMYK-APP14` /
  `PNG-COLOR-CHUNKS` / `COLOR-BITDEPTH`，原文登记在 `data/README.md` §1.11；
  §8.2 表补齐 M4 全部结果码与级别。
- 两条**刻意**的收窄：`cmyk_jpeg` 只认"四分量 JPEG"（APP14 字段不单独作触发依据，
  否则常见 YCbCr Adobe JPEG 会误报——`plan/06` D19）；TIFF 位深不在三支范围内 → `unknown`。
- fixtures：M4 族从 11 份扩到 **14 份**（加多段拼接正/反两支 + TIFF 34675 载体），
  四族合计 **54 份**；`fixtures/lib/build.py` 增 `tiff_with_icc`。
- 接线三处同改：`modules/IMPLEMENTED` 登记 `color` + `modules/PLANNED` 移除 + CLI 暴露
  `color` 与 `--json` 字段（`icc` / `color_markers` / `default_assumptions`）；
  `readers/` 补 TIFF tag 34675 载体采集（四种载体之一之前只落了 JPEG/PNG/WebP）。
- 测试：`tests/test_m4_color.py`（出口门三轮 + R5 双行为 + 级别纪律 + 台账逐字 + 载体面 + 无误报）
  与 `tests/test_m4_defaults.py`（7 行 + 每行 `source` + §8.7 对账）；全量 **146 项** `unittest` 绿。
  三处状态副本 M4 → ✅。**版本升到 `0.3.0`**（交付面变更）。

### M5 container 校验器（2026-10-27）

- `imageoracle container`（题目 M4）对标 `plan/05` §二 M5 出口门：
  PNG chunk 顺序（PNG-3 Table 7）+ CRC（`chunk type + data`，**不含 length**）+ `IDAT` 连续；
  APNG `num_frames` / 序号（`fcTL`+`fdAT` 共享序列）/ `delay_den==0→100`；
  WebP `ANIM`（BGRA + Loop u16，载荷固定 6 字节）/ `ANMF` 内部边界；
  GIF disposal 4–7 + GCE 作用域；JPEG 帧头（SOF）必须在首个 SOS 之前 + APP14 位置。
- **跨格式帧时长归一化**（`data/README` §8.3）：GIF / APNG / WebP 的 100 ms 样本
  （`10` / `10/100` / `100`）归一化后**都等于 100 ms**；`unit_mismatch` 按"假读值恰为 100 ms
  而声明单位不是"判 10× / 1×，假阳性代价写进 §8.3。
- `readers/png.py` 增 APNG 帧切片（`fcTL` → `Frame`，整数 ms）；`Frame` 增 `raw_den`。
  判决层只读 `chunks` / `frames`，不重解析字节。
- 新增条款 `JPEG-T81-FRAME`（ITU-T T.81 §B.2.1）/ `GIF89A-GCE-SCOPE`（GIF89a §23）/
  `FRAME-UNITS`（§1.9 口径），原文登记在 `data/README.md` §1.12；§8.8 补齐 M5 全部结果码与级别。
- **fixture 修正**：旧 `m5_webp_anim_loop_swap.webp` 的 `ANIM`（loop=0）与好样本**逐字节相同**，
  任何判定器都无法区分（M5 实测）。改为"Loop Count 写成 u32、置于 Background 之前"的 8 字节形态，
  判据是**长度**这一结构事实；生成器加自检，禁止两份样本再出现字节相同。
- 接线三处同改：`modules.IMPLEMENTED` 登记 `container` + `modules.PLANNED` 移除 + CLI 暴露
  `container` 与 `--json` 字段（`frames` / `container_facts`）。
- 测试：`tests/test_m5_container.py`（15 份样本逐条对标 + CRC 已知向量 `b"IEND"`→`0xAE426082`
  + 三格式归一化 + `unit_mismatch` 双向 + `delay_den==0` + §1.12/§8.8 逐字对账 + 无误报）；
  全量 **178 项** `unittest` 绿。三处状态副本 M5 → ✅。**版本升到 `0.4.0`**（交付面变更）。

### M6 consumers 矩阵（2026-10-27）

- `imageoracle consumers`（题目 M5）：**9 行 × 6 列**消费者矩阵（Chrome / Safari / Firefox /
  macOS Preview / Windows 照片 / ImageMagick / libvips / sharp / exiftran ×
  会应用方向? / 会应用 ICC? / 会丢哪些 chunk? / 双重旋转风险 / 动画帧时长解读 / 依据）。
- **风险清单 13 条**（`{consumer, risk, severity, trigger, confidence, evidence}`）：severity 走
  `high/medium/low/unknown`（risk 词表，不是 finding 的 error/warning）；`trigger` 是机器可读条件，
  工具按这张图的字节事实筛出"命中了哪几条"（APNG → `--strip all`；`gAMA`/`cHRM` → `--strip safe`；
  IFD1 → jpegtran；XMP 残留 → sharp；PNG `eXIf` → Chrome/Safari 缺口）。
- **处理前后 diff 6 条**（≥4 条硬验收）：`oxipng --strip safe`（丢 `gAMA`/`cHRM`，保留集
  `cICP, iCCP, sRGB, pHYs, acTL, fcTL, fdAT`）/ `oxipng --strip all`（APNG 变静态 PNG）/
  `oxipng --fix`（不做 CRC 校验）/ `sharp.rotate()`（移除 EXIF 方向 tag、XMP 旧方向留着）/
  `exiftran`（JPEG only，连缩略图一起转）/ `jpegtran -copy all -rotate 90`（缩略图不转）。
- **证据纪律**：每行 `evidence.kind ∈ {spec, tool-doc, hn-quote}`，`tool-doc` **必须** URL + 原文片段。
  本棒逐字复核了两页并把地址写进 `data/README` §3.1（sharp `rotate()` 页 ✅；
  ImageMagick `-auto-orient` 页 ⚠️ 第三句措辞已漂移，按 §3 原文保留判据并登记漂移）。
  取不到页面的工具（exiftran / oxipng / jpegtran / libvips 参数页）**不挂 `tool-doc`**，
  改挂已登记条款或 HN 原话，并在 §9 #13 登记——不拿"看起来像官方页"的地址充数。
- 取不到第一方文档的行（Firefox / macOS Preview / Windows 照片 / libvips autorot）一律
  `unknown` + `confidence: gray`，并在 §9 #11–#13 显式登记；**不猜**。
- `selftest_evidence_complete` 扩到三张表（`consumers` / `risks` / `process_diffs`）：
  缺 evidence、`tool-doc` 缺 URL、`confidence` 不在词表都会让 `--selftest-evidence` 失败。
- 接线三处同改：`modules.IMPLEMENTED` 登记 `consumers` + `modules.PLANNED` **清空** + CLI 暴露
  `consumers` 与 `--json` 字段（`matrix` / `consumers` / `risks` / `process_diffs`）；
  `tests/test_cli_contract.py` 增"末棒 `PLANNED` 必须为空"的显式断言（否则旧判据退化成空跑）。
- `consumers` 的 finding **只出 `info`**：它预言"你若跑某条命令会发生什么"，不是文件缺陷；
  风险清单的 severity 因此不进退出码（§8.9 末段写明了要改的先决条件）。
- 测试：`tests/test_m6_consumers.py`（42 项：§1.13/§8.9 三张表逐格对账 + 矩阵/风险/diff 形态 +
  54 份样本逐个跑真 CLI + 缺证据反证 + 接线）；全量 **222 项** `unittest` 绿。
  **版本升到 `0.5.0`**（交付面变更）。
- **发布状态**：`plan/RELEASE-M6.md` 已写（§一 tag 前事实 / §二 tag 后待回填 / §三 出口门对账）；
  **tag / 公开仓库 / Release 未执行**（本机无远端，发布动作待显式授权）。三处状态副本的 M6
  因此保持 ⬜——不把"未执行"写成已完成。

### 已知边界

- 不解码像素（硬约束）：所有"像素实际如何"的结论落 `gray` / `suspicion`。
- PNG `iCCP` 压缩流首期**不解压** → `unknown: compressed_profile_not_inspected`。
- AVIF 帧时长在 ISOBMFF track 时序里，不在图像样本内 → 只报 `not-in-band`。
- fixtures 是**结构性**样本：工具读的字段精确，但像素数据不可解码（`manifest.json` 的 `notes` 已写明）。
