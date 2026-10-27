> 方法论：`ai-tool-project-sprint`（装订 2026-10-27）｜布局门：`python tools/check_sprint_layout.py`｜续接对话第一件事 = 跑它

# 10-27-imageoracle —— 计划总览

图像呈现预言机（ImageOracle）：**只读字节**，预言一张图在 Chrome / Safari / Firefox / macOS Preview / Windows 照片 / ImageMagick / libvips / sharp / exiftran 各自会显示成什么样、会不会被转两次、颜色会不会变、动画帧时长会不会被理解错。

- 性质：不参赛项目题；GitHub **公开仓库**；署名 **yuluo554**
- 形态：纯本地 CLI；**不联网、不解码像素、不做颜色变换、不写回源文件**
- 版本：v1（2026-10-27 定稿）
- 与字体题切割：本题做**像素/元数据/色彩层**（Orientation 语义、ICC 字节、容器 chunk 顺序、帧时序）；字体题做**字形层**（sfnt 表结构、glyph 计数）。解析器、规范依据、样本渠道均不重叠。

## 文档索引

| 文档 | 内容 |
|---|---|
| [`plan/01-题目文档.md`](01-题目文档.md) | 十段式题面：定位宣言、工具覆盖矩阵、规范事实、需求原话分层、开源空白、M1–M5 模块（含输入/输出/确定性纪律/验收）、提交材料、评分表、含金量锚点、边界与非目标 |
| [`plan/02-架构与技术选型.md`](02-架构与技术选型.md) | 分层（容器层 → 语义层 → 判决层 → 呈现层）、字节读取边界、模块依赖方向、构建与发布形态 |
| [`plan/03-模块详设.md`](03-模块详设.md) | M1–M5 的输入/输出契约、数据结构、判定规则到规范条款的映射、退出码落点 |
| [`plan/04-数据计划.md`](04-数据计划.md) | 样本清单与触发矩阵、真值纪律（不依赖本机工具链）、生成器 `--check` 位级一致、manifest 口径 |
| [`plan/05-里程碑与发布.md`](05-里程碑与发布.md) | 里程碑状态表、M0–M6 的 DoD、发布动作序列、已知未验证项 |
| [`plan/06-交付对标与决策.md`](06-交付对标与决策.md) | 评分对标表、缺口表、风险登记、决策记录追加 |
| [`plan/00-README总览.md`](00-README总览.md) | 本文件：索引、决策记录、弃选项、承诺-证据台账、里程碑与 DoD |
| [`data/README.md`](../data/README.md) | 查证记录（三态 + 检索窗口）、规范事实台账（逐条来源）、工具能力矩阵、数据源可获取性、合成数据纪律、**数值口径唯一定义处**、未取到原文清单 |

> 数值口径（8 元变换矩阵 / ICC 校验项 / 帧单位 / gray 条件 / 退出码）**只在 `data/README.md` 定义一次**，其他文档引用不复述。

---

## 决策记录

| # | 决策 | 结论 | 依据 / 状态 |
|---|---|---|---|
| D1 | **Orientation 6 的语义** | `6 = Rotate 90 CW`，即**顺时针 90°**（不是逆时针） | ✅ 已核实：ExifTool `EXIF` 标签页原文 "Rotate 90 CW"；`8 = Rotate 270 CW`。**已写成单测断言**（M1 验收项），并在 `data/README.md` 台账固定。这是最容易搞反的一点，单独记为决策。 |
| D2 | **无 profile 时各软件默认不同** | 必须内嵌「默认假设表」，逐条配出处；**不得写"大家都假设 sRGB"** | ✅ libvips `icc_import` 文档原文：输入 profile 按 **三处搜索**（embedded → `input_profile` 文件 → "Otherwise, libvips will try to pick a compatible profile from the set of built-in profiles"）→ **无 profile 时并不假设 sRGB**。这是"各软件默认不同"的硬证据。表在 M3 第 7 项。 |
| D3 | **oxipng 的两条风险** | 写进 M5 的"处理前后 diff" | ✅ `--strip safe` 保留集原文 = `cICP, iCCP, sRGB, pHYs, acTL, fcTL, fdAT`（**`gAMA`/`cHRM` 不在其中**）→ 过一遍就丢 gamma/chromaticity，颜色会变；✅ `--strip all` 原文 "CAUTION: 'all' will convert APNGs to standard PNGs." → 动图变静图；✅ `--fix` 原文 "Do not perform checksum validation of PNG chunks." → oxipng 自己不查 CRC，所以"用 oxipng 校验过"是伪安全。 |
| D4 | **"像素实际是 bt709 还是 bt2020" 能判吗** | **不能**。只读元数据无法确证，只能给 `gray` | 首期不解码像素（硬约束）。所有"像素实际如何"的结论统一落 `confidence: gray` / `suspicion`，并在报告里标 `unknown`。M2 条件 3、M3 风险等级同此处理。 |
| D5 | **代理未取到的原文** | 一律标 ⬜，不得当已验证 | 未取项：image-size 是否应用 orientation、Pillow `exif_transpose`/`ImageCms` 页、libvips autorot 页、ImageMagick `-profile` 段、AVIF 帧时长容器位置、Safari 对 PNG `iCCP` 行为（仅单来源）。清单见 `data/README.md`。Reddit 检索超时、SO 网页 WebFetch 403，同样标 ⬜。 |
| D6 | **首期实现语言** | **Python 3.12，纯标准库（零第三方依赖）** | ✅ 用户拍板（2026-10-27）。理由：`struct`/`zlib` 可直接控字节，TIFF IFD 与 JPEG 段解析不需要外部库；零依赖同时满足"离线、零网络、易审计"与 CI 双解释器矩阵。`pyproject.toml` 的 `requires-python = ">=3.10"`（CI 跑 3.10 + 3.12）。**不用 `python` 命令**：本机 `python` 是 3.8.8 商店占位符，一律 `py -3.12`。 |
| D7 | **许可证** | **MIT** | ✅ 用户拍板（2026-10-27）。`LICENSE` 一份 + README 一行；发布前归入 tag 树（见 `plan/05` §三）。 |
| D8 | **AVIF/HEIC 处理深度** | 只做"元数据位置说明"，不解析容器 | 理由：转码不是预言；libheif/libavif（2208★）已占位；AVIF 帧时长在 ISOBMFF track 时序里，不在图像样本内 → 只能报 `not-in-band`。 |
| D9 | **PNG `iCCP` 是否解压** | 首期不解压，标 `unknown: compressed_profile_not_inspected` | 避免 zlib 依赖与"解压后仍不可判"的灰区；`iCCP` 的存在性/长度/互斥已可判，足够支撑 lr0 案例的形态复现。 |
| D10 | **`eXIf` chunk 是否含 `Exif\0\0` 前缀** | 按 PNG 规范处理：`eXIf` 数据直接是 TIFF 结构，无前缀；WebP `EXIF` 做前缀探测 | ✅ 已双支落地（2026-10-27）：`fixtures/gen_orientation.py` 造出 `m2_orient6_exif.png`（无前缀）与 `m2_orient6_exif_prefixed.png`（带前缀，工具记 `notes` 而不静默处理）；WebP 两支 `m2_orient6_prefix.webp` / `m2_orient6_noprefix.webp`。实现见 `readers/__init__.py` 的 `_collect_png_metadata` / `_collect_webp_metadata`。 |

> **D11 起（骨架期新增的工程决策）记在 `plan/06-交付对标与决策.md` §四**：测试框架、版本号真源、
> 发布附件口径、CI 矩阵、`generated_at` 默认值、规范条款 ID 体系。

---

## 弃选项（候选 4 与其他）

| 弃选项 | 理由 |
|---|---|
| **跨来源元数据一致性**（作为独立模块） | 与时区漂移、数据往返（round-trip）问题邻接，判定不稳定；且 ExifTool `-j -G -a` 已满足"能列出"的需求 → **降为 M2/M4 的子项**（XMP vs EXIF = M2 条件 2；容器内多来源 = M4）。 |
| **EXIF 剥离 / 隐私清洗** | 已商品化：`exif remove strip metadata` 40+ 仓、strypt 41★、多个 Show HN。无增量。 |
| **C2PA / 内容溯源** | 合规审计禁区，与"呈现"无关。 |
| **色彩校色** | 需硬件（校色仪 + 显示器），纯字节无法完成。 |
| **ELA / 篡改取证** | 结论非确定性，HN 已有公开质疑，与"可复核判决"定位冲突。 |
| **HEIC / AVIF 转码** | 转码不是预言；libheif / libavif 已占位。 |
| **纯 JPEG 段解析器**（独立立项） | go-jpeg-image-structure 77★ 已占位 → 并入 M4。 |
| **IFD1 一致性**（独立立项） | 太窄 → 作为 M2 的条件 1。 |
| **真实颜色变换（引入 lcms）** | 避免与 jsColorEngine 42★、iccDEV 187★ 正面竞争；本题只做"体检 + 预言"。 |

---

## 承诺-证据台账

| 承诺（写在题面里的） | 证据 | 状态 |
|---|---|---|
| ExifTool 不校验图像 | FAQ 25 原文 "ExifTool is not designed as an image validator"（并指向 JHOVE） | ✅ |
| ImageMagick 会双重旋转 | `-auto-orient` 文档原文 "images already corrected without resetting the tag may be rotated wrongly a second time" | ✅ |
| ImageMagick 移除 profile 后 `-auto-orient` 无效 | 文档原文 "If the EXIF profile has already been removed, the -auto-orient operator will do nothing." | ✅ |
| sharp 留 XMP | 文档原文 "Only the EXIF Orientation tag is considered; orientation carried in other places" + #4585 | ✅ |
| exiftran 唯一做对、JPEG only | "can rotate images automatically by checking the exif orientation tag"、"it also rotates the exif thumbnail"、"By default exiftran sets the orientation to '1'" | ✅ |
| jpegtran 不读方向、缩略图不转 | `-rotate 90` = "Rotate image 90 degrees clockwise."；`-copy all` 时 "Thumbnails are copied as-is and not transformed" | ✅ |
| libvips 无 profile 不假设 sRGB | `icc_import` 三处搜索原文 | ✅ |
| oxipng `--strip safe` 不含 gAMA/cHRM | 保留集原文 `cICP, iCCP, sRGB, pHYs, acTL, fcTL, fdAT` | ✅ |
| Orientation 6 = CW90 | ExifTool EXIF 标签原文 | ✅ |
| ICC 128B 头字段名与偏移 | ExifTool ICC_Profile 页 | ✅ |
| PNG chunk 顺序 | PNG 3rd ed (W3C) Table 7 | ✅ |
| CRC 不含 length | PNG-3 原文 | ✅ |
| `iCCP` 与 `sRGB` 互斥 | PNG-3 原文 "should not" | ✅ |
| APNG 序号规则 | Mozilla APNG spec 原文 | ✅ |
| WebP 帧单位 ms / ANIM BGRA | RFC 9649 | ✅ |
| GIF delay 单位 1/100s | GIF89a spec | ✅ |
| 9 条 0 结果检索 | `gh api` search/repositories，窗口 2026-10-27T10:56Z–11:17Z | ⬜ 软论据（可复现但非强论据） |
| $3,000 悬赏 | margelo/react-native-vision-camera#1891 | ✅ |
| image-size 是否应用 orientation | 原文未取 | ⬜ |
| Safari PNG `iCCP` 行为 | lr0 单来源 | ⬜ |

---

## 里程碑

> 里程碑号与题目文档「M1–M5 模块名」的映射见 `plan/05` §一。**状态以 Table 为准，本表是状态副本之一。**

| 里程碑 | 内容 | DoD（完成定义） | 状态 |
|---|---|---|---|
| M0 | 计划与骨架：计划套件 `plan/00–06` + 方法论装订（`AGENTS.md` + 两道门）+ 包骨架 + CI | 布局门与脱敏门可跑且变异验证通过；`py -3.12 -m unittest` 绿；`imageoracle --help` 可跑 | ✅ |
| M1 | 数据先行：纯 Python 字节构造全部 fixture（不依赖 exiftool/jpegtran/sharp）；`fixtures/manifest.json` 落 `sha256` 与"触发哪条验收项" | 生成器 `--check` 位级一致（冻结产物 + 重生成两层都断言）；manifest 哈希稳定；每个样本写明触发项 | ⬜ |
| M2 | `orientation` 判定器（题目 M1）：JPEG/TIFF/PNG `eXIf`/WebP `EXIF` 的 tag 274 + XMP，8 元变换矩阵与有效宽高 | 8 值逐项对 ExifTool 语义；**6=CW90 单测绿**；5/6/7/8 交换 W/H；`absent` 与 `=1` 分列 | ⬜ |
| M3 | 双重旋转探测器（题目 M2）：IFD1≠IFD0 / XMP 冲突 / 宽高启发式（只出 `suspicion`） | 复现 sharp #4585（EXIF=1、XMP=N）与 jpegtran `-copy all`（IFD1 未同步）；`certain`/`heuristic` 分列 | ⬜ |
| M4 | `color` 体检器（题目 M3）：ICC 存在性 + 128B 头逐字段 + `iCCP↔sRGB` + 默认假设表 | lr0 形态复现；截断/`size` 错/`acsp` 坏三类各命中；默认假设表逐行带 `source` | ⬜ |
| M5 | `container` 校验器（题目 M4）：PNG chunk 顺序/CRC/IDAT 连续、APNG 序号、WebP ANMF、GIF disposal、JPEG 段序、跨格式帧时长 | 每类 2 例；100 ms 三格式归一化相等；错写报 `unit_mismatch`；CRC 已知向量单测 | ⬜ |
| M6 | `consumers` 矩阵 + 发布（题目 M5）：消费者矩阵 + 处理前后 diff + 退出码；发布 GitHub 公开仓库 | 每行 `evidence` 齐（`selftest_evidence_complete` 绿）；≥4 条加工命令 diff；tag + Release + 发布留档三件套 | ⬜ |

> M1 排在实现之前是刻意的：样本先于判定器，才能避免"探测器按样本实现"的循环论证。每个模块实现前先跑 M1 样本确认基线。

---

## 工作纪律（本项目通用）

- 只读输入；`out/`、`fixtures/out/` 不入仓。
- 真实照片不入仓（隐私红线）；样本全部程序化合成。
- 零网络：运行时不发起任何网络请求；文档里的 URL 只作为依据引用。
- 判决必须带 `evidence`；无依据的行 CI 判失败。
- 星数/版本是可过期事实：报告头部必须写生成时间与工具版本。
- 不提名任何其他同系列项目。
