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
| D6 | **首期实现语言** | 待定（Python 优先，理由：`struct`/`zlib` 易控字节、fixtures 生成生态成熟；若性能/单文件分发成为诉求再评估 Rust） | ⚠️ 未定稿。实施时在 `plan/02-实现方案.md` 落定；本文不锁死，避免骨架期过早约束。 |
| D7 | **许可证** | 待定（MIT 或 Apache-2.0） | ⚠️ 未定稿。发布前必须在 M6 前落定，否则 README 缺项。 |
| D8 | **AVIF/HEIC 处理深度** | 只做"元数据位置说明"，不解析容器 | 理由：转码不是预言；libheif/libavif（2208★）已占位；AVIF 帧时长在 ISOBMFF track 时序里，不在图像样本内 → 只能报 `not-in-band`。 |
| D9 | **PNG `iCCP` 是否解压** | 首期不解压，标 `unknown: compressed_profile_not_inspected` | 避免 zlib 依赖与"解压后仍不可判"的灰区；`iCCP` 的存在性/长度/互斥已可判，足够支撑 lr0 案例的形态复现。 |
| D10 | **`eXIf` chunk 是否含 `Exif\0\0` 前缀** | 按 PNG 规范处理：`eXIf` 数据直接是 TIFF 结构，无前缀；WebP `EXIF` 做前缀探测 | ⚠️ 实施时用 fixtures 双向验证（带前缀/不带前缀各一例），确认后再固化为解析分支。 |

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

| 里程碑 | 内容 | DoD（完成定义） |
|---|---|---|
| **M1 数据先行** | 用 `exiftool -Orientation#=N` 造 1–8 八样本；Pillow 造双重旋转；`jpegtran` 造缩略图不同步；sharp 造 XMP 残留；ICC 正常/截断/size 错/`acsp` 坏；CMYK JPEG；PNG 错序/坏 CRC/IDAT 非连续；APNG 跳号；GIF `dispose=4..7` 与单位错；WebP `ANMF` duration 异常 | `fixtures/manifest.json` 存在且**哈希稳定**（重跑生成脚本哈希不变）；每个样本写入"它要触发哪条验收项"；生成脚本确定性（固定输入、无时间戳、无随机） |
| **M2 `orientation`** | M1 判定器 | 8 个取值逐项对 ExifTool 语义；**6=CW90 单测绿**；有效宽高 5/6/7/8 交换正确；`absent` 与 `=1` 分列 |
| **M3 双重旋转** | M2 探测器 | 复现 sharp #4585（XMP 残留）与 jpegtran `-copy all`（缩略图未同步）；`certain`/`heuristic` 分列 |
| **M4 `color`** | M3 体检器 | lr0 形态复现；三类损坏 profile 各命中；默认假设表逐行带 `source` |
| **M5 `container`** | M4 校验器 | 每类 2 例；跨格式帧时长归一化后一致、错写必报 `unit_mismatch`；CRC 已知向量单测 |
| **M6 发布** | M5 矩阵 + 发布 | M5 每行有依据（`selftest_evidence_complete` 绿）；**M6 DoD = git tag + GitHub Release 附产物 + 发布留档三件套（README/CHANGELOG/依据表）**；发布为 **GitHub 公开仓库** |

> M1 排在实现之前是刻意的：样本先于判定器，才能避免"探测器按样本实现"的循环论证。每个模块实现前先跑 M1 样本确认基线。

---

## 工作纪律（本项目通用）

- 只读输入；`out/`、`fixtures/out/` 不入仓。
- 真实照片不入仓（隐私红线）；样本全部程序化合成。
- 零网络：运行时不发起任何网络请求；文档里的 URL 只作为依据引用。
- 判决必须带 `evidence`；无依据的行 CI 判失败。
- 星数/版本是可过期事实：报告头部必须写生成时间与工具版本。
- 不提名任何其他同系列项目。
