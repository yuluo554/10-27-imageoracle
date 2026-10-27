# 数据与依据：ImageOracle（图像呈现预言机）

本文件是本题的**依据底座**与**数值口径唯一定义处**。`plan/` 下的文档引用本文件，不重复定义数值；如有冲突，以本文件为准。

- 检索窗口（代理实际检索）：**2026-10-27T10:56Z – 11:17Z**
- 三态口径：**✅ 已核实**（取到原文并逐字比对）/ **⚠️ 部分核实**（取到页面但关键句只有转述或仅单来源）/ **⬜ 未取**（超时、403、未检索）
- 星数为可过期事实，标注采集日期；不得当作长期事实使用。

---

## 0. 三态总览

| 类别 | 状态 | 备注 |
|---|---|---|
| EXIF tag 274 语义（1–8） | ✅ | 逐字取到 ExifTool 原文 |
| ICC 128B 头字段偏移与名 | ✅ | ExifTool ICC_Profile 页 |
| PNG-3 Table 7 chunk 顺序 | ✅ | W3C 原文 |
| PNG CRC 定义 | ✅ | W3C 原文 |
| PNG `iCCP` / `sRGB` 互斥 | ✅ | W3C 原文（措辞为 "should not"） |
| APNG 字段与序列号规则 | ✅ | Mozilla spec 原文 |
| WebP `ANIM`/`ANMF` 与 ms 单位 | ✅ | RFC 9649 |
| GIF89a disposal / delay 单位 | ✅ | GIF89a spec |
| 工具覆盖矩阵（10 工具） | ✅ | 官方文档页 + 星数快照 |
| 需求原话（HN / GitHub） | ✅ | 原帖链接 + 评论 ID |
| 开源空白 9 条 0 结果 | ⬜ 软论据 | `gh api` 检索式可复现，但"0 结果"不等于"无需求/无实现" |
| Reddit 检索 | ⬜ | 窗口内超时，未取 |
| StackOverflow 网页 | ⬜ | WebFetch 403，未取 |
| image-size 是否应用 orientation | ⬜ | 原文未取 |
| Pillow `ImageOps.exif_transpose` / `ImageCms` 页 | ⬜ | 原文未取 |
| libvips autorot 页 | ⬜ | 原文未取（`icc_import` 页已取 ✅） |
| ImageMagick `-profile` 段 | ⬜ | 原文未取（`-auto-orient` 段已取 ✅） |
| AVIF 帧时长容器位置 | ⬜ | 未实测；仅按 ISOBMFF 常识记为 "not-in-band" |
| Safari 对 PNG `iCCP` 的行为 | ⚠️ 单来源 | 仅 lr0 案例一处 |

---

## 1. 规范事实台账

> 每条 = 事实 + 原文片段 + 来源。**未取到原文的一律不进台账，进第 7 节清单。**

### 1.1 EXIF / TIFF Orientation（tag 274 = 0x0112，类型 int16u）

来源：ExifTool 官方标签页 <https://exiftool.org/TagNames/EXIF.html> ✅

| 值 | ExifTool 原文 |
|---|---|
| 1 | Horizontal (normal) |
| 2 | Mirror horizontal |
| 3 | Rotate 180 |
| 4 | Mirror vertical |
| 5 | Mirror horizontal and rotate 270 CW |
| 6 | **Rotate 90 CW** |
| 7 | Mirror horizontal and rotate 90 CW |
| 8 | **Rotate 270 CW** |

- **核对点（必须单测）**：`6` 是**顺时针 90°**（Rotate 90 CW），不是逆时针 90°；`8` 是顺时针 270°（等价逆时针 90°）。
- **核对点**：5 与 7 的差异不是"转多少"，而是镜像后**旋转方向相反**（5 = 镜像后 CW270，7 = 镜像后 CW90）。
- TIFF 字节序（`II`/`MM`）决定 274 的读法：`int16u` 按 TIFF 头声明的字节序读，不得固定小端。

### 1.2 ICC profile 128 字节头

来源：ExifTool ICC_Profile 标签页（字段名与偏移）✅

| 偏移 | 字段名（ExifTool 原文） | 长度 | 说明 |
|---|---|---|---|
| 0 | ProfileSize（头前 4B，BE u32） | 4 | 与载体实际长度比对 |
| 4 | ProfileCMMType | 4 | |
| 8 | ProfileVersion | 4 | |
| 12 | ProfileClass | 4 | `mntr`/`scnr`/`prtr`（另有 ICC 合法值见下） |
| 16 | ColorSpaceData | 4 | `RGB `/`CMYK`/`GRAY`/`XYZ `/`Lab ` 等 |
| 20 | ProfileConnectionSpace | 4 | 同上集合 |
| 24 | ProfileDateTime | 12 | |
| 36 | ProfileFileSignature | 4 | **`acsp`** |
| 40 | PrimaryPlatform | 4 | |
| 44 | **CMMFlags** | 4 | 注意：是 CMMFlags，不是 ProfileFlags |
| 48 | **DeviceManufacturer** | 4 | |
| 52 | **DeviceModel** | 4 | |
| 56 | DeviceAttributes | 8 | |
| 64 | RenderingIntent | 4 | 0 Perceptual / 1 media-relative colorimetric / 2 saturation / 3 ICC-absolute colorimetric |
| 68 | ConnectionSpaceIlluminant | 12 | |
| 80 | ProfileCreator | 4 | |
| 84 | ProfileID | 16 | |
| 100–127 | 保留 | 28 | 全 0 |

- `ProfileClass`：`mntr`(display) / `scnr`(input) / `prtr`(output)。ICC 另定义 `spac`(color space)、`abst`(abstract)、`nmcl`(named color) —— 首期报 `info` 不报 `warning`。
- **字段名一律用 ExifTool 原文**，报告 JSON 的 key 与上表一致，避免与 ICC 规范里的 `profileFlags` 混淆。
- 长度不足 128 → `error: icc_header_truncated`；`ProfileSize != 实际长度` → `error: icc_size_mismatch`；`@36 != acsp` → `error: icc_bad_signature`。

### 1.3 PNG 3rd edition（W3C）Table 7 — chunk 顺序

来源：<https://www.w3.org/TR/png-3/> Table 7 ✅

| Chunk | 原文约束 |
|---|---|
| IHDR | "The IHDR chunk shall be the first chunk" |
| IEND | "Shall be last" |
| PLTE | "Before first IDAT"；color type 0/4 **不得出现** |
| IDAT | "Multiple IDAT chunks shall be consecutive" |
| tRNS | "After PLTE; before IDAT"；color type 4/6 **不得出现** |
| acTL / eXIf / pHYs / sPLT | "Before IDAT" |
| cHRM / cICP / gAMA / iCCP / sBIT / sRGB | "Before PLTE and IDAT" |
| bKGD / hIST / tRNS | "After PLTE; before IDAT" |
| **fcTL** | "One may occur before IDAT; all others shall be after IDAT" |
| **fdAT** | "After IDAT" |

- 未知 chunk（ancillary，首字母小写第二位大写以上规则）不判错；关键 chunk 位置错一律 `error`。

### 1.4 PNG CRC

来源：PNG-3 ✅

- 原文："A four-byte CRC calculated on the preceding bytes in the chunk, including the chunk type field and chunk data fields"
  → **CRC 覆盖范围 = chunk type + chunk data，不含 length**。
- 原文："The CRC is always present, even for chunks containing no data." → 空数据 chunk 也必须有 4 字节 CRC。
- 算法：CRC-32（ISO 3309 / ITU-T V.42），多项式 0xEDB88320（反射形式），初值 0xFFFFFFFF，末取反。**已知向量单测**：`b"IEND"` 的 CRC 应为 `0xAE426082`。

### 1.5 PNG `iCCP` 与 `sRGB` 互斥

来源：PNG-3 ✅

- 原文："If the iCCP chunk is present, the sRGB chunk should not be present"
- 措辞为 **should not**（非 shall not）→ 本工具报 `warning: iccp_srgb_conflict`，不报 `error`。这是刻意的规范忠实度：不把 should 升格为 shall。

### 1.6 APNG（Mozilla spec）

来源：<https://wiki.mozilla.org/APNG_Specification> ✅

| 项 | 原文 / 规则 |
|---|---|
| `acTL` 位置 | "must appear in the stream before any IDAT chunks" |
| `acTL.num_frames` | u32 |
| `acTL.num_plays` | u32，0 = 无限循环 |
| 数量一致 | `num_frames` "must equal the number of fcTL chunks"；"If this value does not equal the actual number of frames it should be treated as an error." |
| `fcTL` 字段 | `sequence_number` / `width` / `height` / `x_offset` / `y_offset` / `delay_num` / `delay_den` / `dispose_op` / `blend_op` |
| 首帧序号 | "The first fcTL chunk must contain sequence number 0" |
| 序列号 | "sequence numbers ... must be in order, with no gaps or duplicates" |
| 乱序 | "Decoders must treat out-of-order APNG chunks as an error." |
| `delay_den` | 为 0 时 "treated as if it were 100" |

- 帧时长 = `delay_num / delay_den` 秒；`delay_den == 0` → 按 100 处理。
- **注意**：序号在 `fcTL` 与 `fdAT` 之间**共享**一个计数序列（spec 的 sequence_number 是统一序列）。实现时先按 spec 原文确认，不得凭印象合并/拆分（标 ⚠️ 实现期复核）。

### 1.7 WebP（RFC 9649）

来源：RFC 9649 ✅

| 项 | 原文 |
|---|---|
| `ANIM` 组成 | Background Color (u32) + Loop Count (u16, 0 = 无限) |
| Background Color 字节序 | "[Blue, Green, Red, Alpha]"（注：原文如此，**不是** RGBA） |
| `ANMF` Frame Duration | "24 (uint24) — The time to wait before displaying the next frame, in **1-millisecond units**." |

### 1.8 GIF89a

来源：GIF89a spec（W3C 镜像 / gif89a.txt）✅

| Disposal Method | 原文 |
|---|---|
| 0 | No disposal specified |
| 1 | Do not dispose |
| 2 | Restore to background color |
| 3 | Restore to previous |
| 4–7 | To be defined |

- Delay Time 单位：**1/100 秒**（百分之一秒）。

### 1.9 由 1.6–1.8 得出的可判定事实（跨格式帧时长单位）

| 格式 | 单位 | 换算到 ms |
|---|---|---|
| GIF | 1/100 s | `delay * 10` |
| APNG | `delay_num/delay_den` s（den=0→100） | `num/den * 1000` |
| WebP | 1 ms | 原值 |
| AVIF | **不在图像样本内**（ISOBMFF track 时序） | 报 `not-in-band` ⬜ 未实测 |

→ **跨格式转帧时长的量级错误（10× / 1×）可被静态检出**：同一段 100 ms 动画应为 GIF=10、APNG=10/100、WebP=100；写错即成 `unit_mismatch`。

---

## 2. 工具能力矩阵

星数快照：**2026-10-27**（`gh api repos/<owner>/<repo>` 的 `stargazers_count`）。能力列依据官方文档原文，原文片段见第 3 节。

| 工具 | 星数 | 读方向 | 修方向 | 读 ICC | 转 ICC | 容器结构 | APNG 序列 | 跨消费者预言 | 跨来源一致性 |
|---|---|---|---|---|---|---|---|---|---|
| ExifTool | 5213 | ✅ | ❌ | ✅ | ❌ | ⚠️ | ❌ | ❌ | ⚠️ |
| ImageMagick | 17746 | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ❌ |
| libvips | 11767 | ✅ | ⚠️ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Pillow | 13930 | ✅ | ⚠️ | ✅⬜ | ✅ | ❌ | ❌ | ❌ | ❌ |
| exiv2 | 1168 | ✅ | ❌ | ✅ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| jpegtran (libjpeg-turbo) | 4460 | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ |
| exiftran (fbida) | — | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| sharp | 32798 | ✅ | ⚠️ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| image-size | 2228 | ⚠️⬜ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| oxipng | 4300 | ❌ | ❌ | ⚠️ | ❌ | ⚠️ | ❌ | ❌ | ❌ |

补充星数：imagemin 5715、ImageOptim 10016、libpng 1670、libwebp 2417、libavif 2208、mozjpeg 5739、zopfli 3602、iccDEV 187、pngcheck（无星数记录）、jsColorEngine 42、strypt 41、go-jpeg-image-structure 77。

矩阵结论：**没有一行同时具备"判决"与"跨消费者预言"**。

---

## 3. 工具原文片段（证据）

| 工具 | 原文 | 用于 |
|---|---|---|
| ExifTool | "ExifTool is not designed as an image validator"（FAQ 25，并指向 JHOVE）；`-validate` 自 10.97 起主要覆盖 JPEG/TIFF | M5 依据；非目标说明 |
| ImageMagick | `-auto-orient`："reads and resets the EXIF image profile setting 'Orientation'"、"performs the appropriate 90 degree rotation"、"images already corrected without resetting the tag may be rotated wrongly a second time"、"If the EXIF profile has already been removed, the -auto-orient operator will do nothing." | M2 条件链；M5 双重旋转 |
| libvips | `icc_import`：embedded → `input_profile` 文件 → "Otherwise, libvips will try to pick a compatible profile from the set of built-in profiles" | M3 默认假设表（D2） |
| exiv2 | `-pS`："Image structure information (jpg, png, tiff, webp, cr2 and jp2 types only)"；`-pR` 递归结构仅 debug build | M4 能力边界 |
| jpegtran | `-rotate 90`："Rotate image 90 degrees clockwise."；`-copy all`："Thumbnails are copied as-is and not transformed"；man 页建议用 exiftran 代替 | M2 条件 1 复现；M4 段顺序 |
| exiftran | "can rotate images automatically by checking the exif orientation tag"、"it updates the exif informations if needed (image dimension, orientation)"、"it also rotates the exif thumbnail"、"By default exiftran sets the orientation to '1'"；**JPEG only** | M5 exiftran 行；非目标 |
| sharp | `rotate()` 无参 = `autoOrient()`："Auto-orient based on the EXIF Orientation tag, then remove the tag."；"Only the EXIF Orientation tag is considered; orientation carried in other places" | M2 条件 2；#4585 |
| oxipng | `--strip safe` 保留集："cICP, iCCP, sRGB, pHYs, acTL, fcTL, fdAT"；`--strip all`："CAUTION: 'all' will convert APNGs to standard PNGs."；`--fix`："Do not perform checksum validation of PNG chunks." | M5 diff（D3） |

---

## 4. 需求原话台账（分层）

### 4.1 方向 / 呈现

| 来源 | 原话 / 链接 |
|---|---|
| HN 107pts 2025-11-21 | "EXIF orientation info in PNGs isn't used for image-orientation: from-image" <https://news.ycombinator.com/item?id=46004364>（→ Bugzilla 1627423） |
| 同上评论 @Linkd | "EXIF orientation has always been a massive pain to deal with. Specially with HEIC that keeps getting updated libheifs and causing all sorts of compatibility issues." id=46005116 |
| HN 78pts 2025-09-09 | "Resizing images in Rust, now with EXIF orientation support" <https://news.ycombinator.com/item?id=45180094> |
| HN 21208568 2019-10-09 | "Surely someone can create a neural network that reorients the image, even if the Exif orientation is wrong (JPEG lets you can do this without re-encoding)." |
| HN 5026565 2013-01-08 | "Random software package either supports the EXIF orientation or it doesn't. If it doesn't, Joe User just sees the photo rotated wrong, and they want to fix it." |
| GitHub | `margelo/react-native-vision-camera#1891` $3,000 悬赏、90 reactions；`photoprism/photoprism#464` 179；`flutter/flutter#31225` 214；`lovell/sharp#1784`；`lovell/sharp#4585`；`lovell/sharp#3024` |

### 4.2 色彩 / ICC

| 来源 | 原话 |
|---|---|
| HN 70pts 2025-12-27 | "PNG in Chrome shows a different image than in Safari or any desktop app" <https://news.ycombinator.com/item?id=46403048> → lr0.org：`chunk iCCP at offset 0x00025, length 5147`；`Gamma: 0.454545` 被点名 "ImageMagick's assumption, not file metadata"；`pngcrush -ow -rem gAMA -rem cHRM -rem iCCP -rem sRGB` 无效 |
| HN 643pts 2022-04-21 @kloch | "There are several ways colorspace metadata can be included in a PNG. - No colorspace metadata (software should assume sRGB) - Built-in sRGB format chunk - gAMA chunks - cHRM chunks - ICC profile chunks." id=31112951 |
| HN 32663226 2022-08-31 @account42 | "zopflipng typically beats pngcrus and optipng ... but by default it drops auxillary PNG chunks which can result in browsers (and other applications) using a different color space" |
| HN 29284352 2021-11-20 @amiantos | "CMYK JPEGs are the bane of my existence. A recent annoyance was a realization that they don't render consistently in different browsers." |
| HN 48254156 @190n | "the initial implementation of this stripped ICC profiles" |
| HN 38978724 2024-01-13 | "Browsers, chat apps, social media apps, Outlook and all other email clients, Teams, Zoom, Adobe Photoshop (really!), DaVinci Resolve (a colorist tool ffs)" 忽略色彩管理 |

### 4.3 解码器分歧

| 来源 | 原话 |
|---|---|
| HN 136pts 2021-11-19 | "all look the same and be called a JPEG but have wildly different decoding compatibility with some bits of kit."、"the hardware decoder also does not accept APP2 headers (EXIF and friends), and does not deal with 4:4:4 sampling."、"Don't ever expect two decoders (especially hardware assisted) to give you identical outputs." <https://news.ycombinator.com/item?id=29276300> |
| HN 50137766 @meindnoch | "Gamma is assumed to be sRGB gamma by default. Default color space is likewise sRGB." |

> 注：HN 70pts 那条的日期按检索命中的条目元数据记为 2025-12-27；题面已加脚注说明以页面显示为准。

---

## 5. 开源空白检索记录

命令形态：`gh api -X GET search/repositories -f q='<query>' -f per_page=1`（读 `total_count`）。
窗口：2026-10-27T10:56Z – 11:17Z。

| 检索式 | total_count | 备注 |
|---|---|---|
| `auto orient exif cli` | 0 | ⬜ 软论据 |
| `image orientation fixer tool` | 0 | ⬜ |
| `orientation tiff mirrored validation` | 0 | ⬜ |
| `icc profile validator inspect` | 0 | ⬜ |
| `cmyk jpeg conversion` | 0 | ⬜ |
| `png apng gif animation metadata` | 0 | ⬜ |
| `apng validator` | 0 | ⬜ |
| `animated webp avif frame duration` | 0 | ⬜ |
| `image metadata validator lint` | 0 | ⬜ |
| `exif orientation in:name,description,readme` | 13978 | 噪声主导（filepond 16394★） |
| `exif viewer cli` | 2 | 1★/0★ |
| `png chunk validator tool` | 3 | pngpeek 0★ |
| `jpeg segment parser` | 8 | go-jpeg-image-structure 77★ |
| `image metadata diff compare` | 5 | 全 ≤2★ |
| `image metadata inspector exif xmp iptc` | 5 | 全 0★ |
| `image forensic structural analysis` | 4 | — |
| `image preflight validation upload` | 1 | 0★ |
| `icc profile color management` | 9 | iccDEV 187★、jsColorEngine 42★ |
| `display p3 wide gamut image` | 1 | 6★ |
| `exif remove strip metadata` | 40 | strypt 41★ → 明确不做 |

Issue 检索：`exif orientation` 197453（噪声大）；top reactions: flutter#31225=214、photoprism#464=179、ImageMagick#507=125、vision-camera#1891=90（$3000）；`icc profile stripped color shift` 141（kirby#2537）；`repo:lovell/sharp orientation in:title` 29。

**判读**：0 结果是**软论据**——检索式的写法本身影响结果，且"搜不到"≠"不存在"。真正强的论据是第 3 节的工具原文（现有工具确实缺少"判决 + 跨消费者预言"这一能力组合）。

---

## 6. 数据源可获取性

| 项 | 结论 |
|---|---|
| 外部数据依赖 | **无**。全部样本程序化生成，零网络。 |
| 参考照片 | **不入仓**（隐私红线）；不使用真实照片。 |
| libheif / libavif | **未测**。AVIF 只按 ISOBMFF 常识说明帧时长位置，并标 ⬜。 |
| 工具二进制 | 生成 fixtures 需 `exiftool`、`jpegtran`、`sharp`(Node)、`Pillow`(Python)、可选 `oxipng`/`pngcheck` 作对照；**运行时 CLI 不依赖它们**（只依赖标准库的字节解析）。 |
| 规范文本 | W3C PNG-3、RFC 9649、GIF89a、Mozilla APNG spec、ExifTool 标签页 —— 只作为引用，不入仓（版权）。 |

---

## 7. 合成数据纪律

1. **全部程序化生成**：不存在手工拍照/下载的样本；生成脚本入仓，产物不入仓。
2. **确定性**：固定输入、固定种子、无时间戳、无随机；`fixtures/manifest.json` 记录每个文件的 `sha256` 与"要触发的验收项"。重跑脚本哈希必须不变。
3. **必造样本清单**：
   - 8 个 Orientation（`exiftool -Orientation#=N`，N=1..8），基础图为 **非正方形**（否则 5/6/7/8 的宽高交换不可观测）；
   - 双重旋转：Pillow 改像素不改 tag / sharp `autoOrient()`（XMP 残留）/ `jpegtran -copy all -rotate 90`（缩略图不同步）；
   - ICC：正常 / 截断（<128B）/ `ProfileSize` 字段错 / `acsp` 坏 ；
   - CMYK JPEG（APP14）；
   - PNG：`gAMA` 在 IDAT 后、第二个 IDAT 非连续、坏 CRC、缺 CRC；
   - APNG：`num_frames` 与实际 `fcTL` 数不符、序号跳号；
   - GIF：`dispose=4`、delay 按 ms 误写；
   - WebP：`ANMF` Frame Duration 异常、`ANIM` Loop Count 位置/字节序错。
4. **样本命名**：`<module>_<case>_<variant>.<ext>`，如 `m1_orient6_portrait.jpg`、`m4_apng-gap_01.png`。
5. **不得用真实人物/可识别信息**：合成图用纯色块 + 方向标记（如左上角红三角），便于人工肉眼核对而不泄露任何真实内容。

---

## 8. 数值口径（**唯一定义处**）

> `plan/` 下的文档只引用本节的名称，不复述数值。

### 8.1 8 元变换矩阵（Orientation 1–8）

定义：对**存储像素**施加的变换，使显示结果正确。`rotate_cw_deg` ∈ {0, 90, 180, 270}；`flip_h`/`flip_v` 为布尔；**应用顺序 = 先翻转（h 再 v），后顺时针旋转**。

| 值 | 语义（ExifTool） | flip_h | flip_v | rotate_cw_deg | 交换 W/H |
|---|---|---|---|---|---|
| 1 | Horizontal (normal) | F | F | 0 | 否 |
| 2 | Mirror horizontal | T | F | 0 | 否 |
| 3 | Rotate 180 | F | F | 180 | 否 |
| 4 | Mirror vertical | F | T | 0 | 否 |
| 5 | Mirror horizontal and rotate 270 CW | T | F | 270 | **是** |
| 6 | **Rotate 90 CW** | F | F | **90** | **是** |
| 7 | Mirror horizontal and rotate 90 CW | T | F | 90 | **是** |
| 8 | Rotate 270 CW | F | F | 270 | **是** |

- **单测锚点**：`6 → rotate_cw_deg=90`（顺时针）；`8 → 270`。断言文案引用 ExifTool 原文，防止日后改反。
- **等价性注记**：`Mirror vertical (4)` 等价于 `Mirror horizontal + Rotate 180`；实现只需上表的规范形式，不做等价化简（避免引入歧义）。
- 有效宽高：仅 5/6/7/8 交换 W/H。

### 8.2 ICC 校验项（报错级别）

| 检查 | 条件 | 级别 |
|---|---|---|
| 头长度 | `< 128` | `error: icc_header_truncated` |
| 签名 | `@36 != "acsp"` | `error: icc_bad_signature` |
| 长度一致 | 头前 u32 != 载体长度 | `error: icc_size_mismatch` |
| class | ∉ {mntr, scnr, prtr, spac, abst, nmcl} | `warning: icc_unknown_class` |
| class | ∈ {spac, abst, nmcl} | `info` |
| colorspace/PCS | ∉ {RGB , CMYK, GRAY, XYZ , Lab } | `warning: icc_unknown_space` |
| rendering intent | ∉ 0..3 | `warning: icc_bad_intent` |
| iCCP+sRGB 并存 | 两者皆有 | `warning: iccp_srgb_conflict` |
| iCCP 压缩流 | 首期不解压 | `unknown: compressed_profile_not_inspected` |

### 8.3 帧时长归一化

- `to_ms(gif, delay) = delay * 10`
- `to_ms(apng, num, den) = num / (den == 0 ? 100 : den) * 1000`（用整数运算：`num * 1000 / den`，den=0→100）
- `to_ms(webp, duration) = duration`（已是 ms）
- `to_ms(avif, *) = not-in-band`（首期不判）

### 8.4 `gray`（不可判）条件

出现以下任一，结论必须落 `confidence: gray` / `suspicion`，不得给确定判决：

1. 需要**解码像素**才能确认（如"像素实际是否已被转过"）；
2. 需要**解压/解包**才能确认，而首期明确不解（PNG `iCCP` 压缩流、AVIF 容器）；
3. 结论仅来自**单来源**（如 Safari 对 PNG `iCCP` 的行为）；
4. 需要**运行消费者软件**才能确认（本工具不运行它们，只按文档预言）。

### 8.5 退出码

| 码 | 含义 |
|---|---|
| 0 | 无 warning / error（可能有 `info`） |
| 1 | 存在 `warning` |
| 2 | 存在 `error`，或存在 `unknown`（不可判项） |
| 3 | 输入不可解析（不是"判决失败"，是"读不了"；不参与判决计数） |

---

## 9. 未取到原文的项清单（⬜，不得当已验证）

| # | 项 | 原因 |
|---|---|---|
| 1 | image-size 是否应用 orientation | 原文未取；仅间接旁证（sharp 另提供 `getNormalSize`） |
| 2 | Pillow `ImageOps.exif_transpose` 文档页 | 未取 |
| 3 | Pillow `ImageCms` 文档页 | 未取 |
| 4 | libvips `autorot` 文档页 | 未取（`icc_import` 页已取 ✅） |
| 5 | ImageMagick `-profile` 段落 | 未取（`-auto-orient` 段已取 ✅） |
| 6 | AVIF 帧时长在容器中的确切位置 | 未实测；按 ISOBMFF 常识记为 track 时序，标 `not-in-band` |
| 7 | Safari 对 PNG `iCCP` 的行为 | 仅 lr0 单来源 |
| 8 | Reddit 相关讨论 | 检索超时 |
| 9 | StackOverflow 相关问答 | WebFetch 403 |
| 10 | APNG `fcTL` 与 `fdAT` 是否共享同一 sequence_number 计数 | 原文需实施期逐字复核（本文件标 ⚠️） |

---

## 10. 引用与复现

- 规范：W3C PNG 3rd ed、RFC 9649（WebP）、GIF89a、Mozilla APNG Specification、ExifTool TagNames（EXIF / ICC_Profile）。
- 需求：HN 条目按 item id 引用；GitHub issue 按 `<owner>/<repo>#<num>` 引用。
- 检索：`gh api search/repositories` + `gh api search/issues`，窗口见文件头。
- 任何引用若与页面现状不符，**以页面现状为准**，并更新本文件（记录更新日期）。
