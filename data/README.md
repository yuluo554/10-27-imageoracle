# 数据与依据：ImageOracle（图像呈现预言机）

本文件是本题的**依据底座**与**数值口径唯一定义处**。`plan/` 下的文档引用本文件，不重复定义数值；如有冲突，以本文件为准。

- 检索窗口（代理实际检索）：**2026-10-27T10:56Z – 11:17Z**
- M6 期工具文档复核（**装订窗口之外**，只为给 `tool-doc` 证据补页面地址）：**2026-10-27**，结论与措辞漂移写在 §3.1
- 三态口径：**✅ 已核实**（取到原文并逐字比对）/ **⚠️ 部分核实**（取到页面但关键句只有转述或仅单来源）/ **⬜ 未取**（超时、403、未检索）
- 星数为可过期事实，标注采集日期；不得当作长期事实使用（M6 报告头写出快照日期 `2026-10-27`）。

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
| JPEG 段序（SOF 在首个 SOS 前 / APPn 位置） | ✅ | ITU-T T.81 §B.2.1（原文见 §1.12） |
| GIF GCE 作用域 | ✅ | GIF89a §23（原文见 §1.12） |
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
| macOS Preview / Windows 照片 的方向与色彩行为 | ⬜ | 未取第一方文档（§9 #11 / #12）；M6 矩阵里这些行标 `gray` |

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

### 1.10 双重旋转的软件侧依据（M3 用，**需求依据**而非技术依据）

来源：第 3 节工具原文（逐字，未改写）+ 第 8.4 节第 1 条。这四个 ID 是 `src/imageoracle/specs/`
里对应条款的**唯一定义处**；`tests/test_m3_double_rotate.py` 解析本表逐字对账。

| 条款 ID | 原文 |
|---|---|
| SHARP-AUTOORIENT | Only the EXIF Orientation tag is considered; orientation carried in other places |
| JPEGTRAN-COPYALL | Thumbnails are copied as-is and not transformed |
| IMAGEMAGICK-AUTOORIENT | images already corrected without resetting the tag may be rotated wrongly a second time |
| GRAY-DECODE-REQUIRED | 需要解码像素才能确认（如"像素实际是否已被转过"） |

- 三行英文原话与第 3 节同名条目**逐字相同**（测试断言 `quote` 也在第 3 节出现，防"顺手改写"）。
- `GRAY-DECODE-REQUIRED` 取自第 8.4 节第 1 条，原文的 Markdown 强调记号（`**`）不计入 quote——
  测试对账时先剥标记再比。
- 它们是"为什么会转两次"的**需求依据**；判据本身（`IFD1≠IFD0` / 两来源不一致）落在 EXIF tag 274 语义上，
  不靠这几句原话支撑。

### 1.11 色彩体检的条款依据（M4 用）

来源：ExifTool ICC_Profile 页 ✅ + 第 3 节工具原文（逐字，未改写）+ 第 4.2 节需求原话。
这六个 ID 是 `src/imageoracle/specs/` 里对应条款的**唯一定义处**；
`tests/test_m4_color.py` 解析本表逐字对账（不在测试里另抄一份）。

| 条款 ID | 原文 |
|---|---|
| ICC-CARRIERS | ICC carrier: JPEG APP2 ICC_PROFILE\0 (multi-segment, index i/n); PNG iCCP; WebP ICCP; TIFF tag 34675 |
| ICC-NOT-INSPECTED | PNG iCCP carries a zlib-compressed profile; first release does not decompress it |
| ICC-DEFAULTS | Otherwise, libvips will try to pick a compatible profile from the set of built-in profiles |
| CMYK-APP14 | CMYK JPEGs are the bane of my existence. A recent annoyance was a realization that they don't render consistently in different browsers. |
| PNG-COLOR-CHUNKS | cHRM/cICP/gAMA/iCCP/sBIT/sRGB before PLTE and IDAT |
| COLOR-BITDEPTH | PNG: IHDR bit depth (single byte); JPEG: SOF precision (single byte, 8 or 12); WebP: bit depth lives in the bitstream and needs unpacking |

- `ICC-DEFAULTS` 与第 3 节 libvips 行**逐字相同**（测试断言 `quote` 也在第 3 节出现，防"顺手改写"）。
- `CMYK-APP14` 是**需求依据**（@amiantos 原话），不是技术依据：判据落在"四分量 JPEG"这一结构事实上，
  不靠这句原话支撑（见 §8.2 与 `plan/06` D19）。
- ICC 128B 头字段的原文仍以 §1.2 表为准（字段名与偏移），本节不重复登记。

### 1.12 容器结构的条款依据（M5 用）

来源：ITU-T T.81 §B.2.1 ✅（`https://www.w3.org/Graphics/JPEG/itu-t81.pdf`）；
GIF89a spec §23 ✅（`https://www.w3.org/Graphics/GIF/spec-gif89a.txt`）；
跨格式单位口径 = 本文件 §1.9 / §8.3（内部定义）。
这三个 ID 是 `src/imageoracle/specs/` 里对应条款的**唯一定义处**；
`tests/test_m5_container.py` 解析本表逐字对账（不在测试里另抄一份）。

| 条款 ID | 原文 |
|---|---|
| JPEG-T81-FRAME | The second level of Figure B.2 specifies that a frame shall begin with a frame header and shall contain one or more scans. A frame header may be preceded by one or more table-specification or miscellaneous marker segments as specified in B.2.4. Each scan header may be preceded by one or more table-specification or miscellaneous marker segments. |
| GIF89A-GCE-SCOPE | The scope of this extension is the first graphic rendering block to follow. |
| FRAME-UNITS | GIF: delay * 10; APNG: delay_num / (delay_den == 0 ? 100 : delay_den) * 1000; WebP: duration (already ms); AVIF: not-in-band |

- `JPEG-T81-FRAME` 支持两条判据：帧头（SOF）必须在首个扫描（SOS）之前（"a frame shall begin with a
  frame header"）；APPn 属于"miscellaneous marker segments"，只能出现在帧头/扫描头**之前**，
  因此 `SOS` 之后的 `APP14` 违反语法（`jpeg_app14_position`）。
- `GIF89A-GCE-SCOPE` 支持 `gif_gce_position`：GCE 的作用域是"紧随其后的第一个渲染块"，
  GCE 后面不是图像块（或连续两个 GCE）即无作用域。
- `FRAME-UNITS` 是内部口径（§1.9 表的机器可读形态），不是外部原文；登记它的目的是让
  `unit_mismatch` / `frame_duration_normalized` 的 `evidence.spec` 可查（K8）。

### 1.13 consumers 的条款依据（M6 用）

来源：§3 工具原文（逐字）+ §4 需求原话（逐字）+ 本文件 §8.9（矩阵与 diff 的内部口径）。
这十一条 ID 是 `src/imageoracle/specs/` 里对应条款的**唯一定义处**；
`tests/test_m6_consumers.py` 解析本表逐字对账（不在测试里另抄一份）。

| 条款 ID | 原文 |
|---|---|
| OXIPNG-STRIP-SAFE | cICP, iCCP, sRGB, pHYs, acTL, fcTL, fdAT |
| OXIPNG-STRIP-ALL | CAUTION: 'all' will convert APNGs to standard PNGs. |
| OXIPNG-FIX | Do not perform checksum validation of PNG chunks. |
| SHARP-AUTOORIENT-REMOVE | Auto-orient based on the EXIF Orientation tag, then remove the tag. |
| IMAGEMAGICK-AUTOORIENT-RESET | reads and resets the EXIF image profile setting 'Orientation' |
| EXIFTRAN-ROTATE | can rotate images automatically by checking the exif orientation tag; it also rotates the exif thumbnail; By default exiftran sets the orientation to '1'; JPEG only |
| HN-ORIENTATION-PNG | EXIF orientation info in PNGs isn't used for image-orientation: from-image |
| HN-ICC-RENDER | PNG in Chrome shows a different image than in Safari or any desktop app |
| HN-SOFTWARE-EITHER | Random software package either supports the EXIF orientation or it doesn't. If it doesn't, Joe User just sees the photo rotated wrong, and they want to fix it. |
| HN-COLOR-IGNORED | Browsers, chat apps, social media apps, Outlook and all other email clients, Teams, Zoom, Adobe Photoshop (really!), DaVinci Resolve (a colorist tool ffs) |
| CONSUMER-MATRIX | rows = chrome, safari, firefox, macos_preview, windows_photos, imagemagick, libvips, sharp, exiftran; columns = applies_orientation, applies_icc, dropped_chunks, double_rotate_risk, frame_duration, evidence |

- 前六条逐字来自 §3（`oxipng` 三条、`sharp rotate()` 一条、`exiftran` 一条、ImageMagick `-auto-orient` 一条）。
  `EXIFTRAN-ROTATE` 是把 §3 里分开的四段原文用 `; ` 串起来的一条，**不做改写**；
  `IMAGEMAGICK-AUTOORIENT-RESET` 取自 §3 那条 `-auto-orient` 原文的**第一句**（§3.1 复核过该句逐字仍在页面上）。
  与之相对的"再转一次"那句在页面上已改写，因此那条（`IMAGEMAGICK-AUTOORIENT`）**不挂 `tool-doc`**
  ——见 §3.1 的漂移登记。
- 三条 `HN-*` 逐字来自 §4.1 / §4.2；它们支撑的是**需求面**结论（"浏览器对 PNG 的 `eXIf`
  方向有缺口"、"Chrome 与 Safari 的 `iCCP` 呈现不同"），不是技术判据。
- `CONSUMER-MATRIX` 是**内部口径**（§8.9 表体的机器可读形态），不是外部原文；登记它是为了让
  `consumer_matrix` 这条 finding 的 `evidence.spec` 可查（K8）。
- `tool-doc` 证据的页面地址只给 §3.1 已复核的两页（`sharp` / ImageMagick）；其余工具页未取到，
  相应行**不挂** `tool-doc`（§9 #13）。

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

### 3.1 官方文档页与 M6 期复核（2026-10-27）

> 本表此前只记了原文片段、没记页面地址。M6 造消费者矩阵时 `tool-doc` 证据要求 "URL + 原文片段"，
> 因此本棒（装订窗口之外）对两页做了**逐字复核**。取不到页面的一律保持 ⬜ 并进 §9，
> **不拿"看起来像官方页"的地址充数**。

| 工具 | 官方文档页 | 复核结论 |
|---|---|---|
| sharp `rotate()` / `autoOrient()` | <https://sharp.pixelplumbing.com/api-operation> | ✅ 逐字命中："Auto-orient based on the EXIF Orientation tag, then remove the tag." 与 "Only the EXIF Orientation tag is considered; orientation carried in other places" |
| ImageMagick `-auto-orient` | <https://imagemagick.org/command-line-options/> | ⚠️ 前段逐字命中："reads and resets the EXIF image profile setting 'Orientation'"；**§3 记的第三句在当前页已改写**为 "orientation 'corrected' without resetting this setting, may be 'corrected' again"。M3 的条款按 §3 原文保留（改动会打挂 M3 单测），此处只登记**页面措辞漂移**，判据不动 |

- 取不到的页面（本棒实测）：`exiftran` man 页（302 到 `dyn.manpages.debian.org` 后 404）、
  `oxipng` README（连接被重置）、libvips `icc_import` 参数页（只取到索引页，无参数细节）、
  `jpegtran` man 页（未取）。→ 这些工具的行**不挂 `tool-doc`**，改挂已登记条款或 HN 原话，
  并在 §9 #13 登记。

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
| 载体存在 | 无任何 ICC 载体（APP2 / `iCCP` / `ICCP` / tag 34675） | `info: icc_missing` |
| 载体存在 | 有载体 | `info: icc_present` |
| JPEG APP2 分片 | 段号 `i/n` 不连续，或声明总数 ≠ 实到段数 | `error: icc_segment_gap` |
| 头长度 | `< 128` | `error: icc_header_truncated` |
| 签名 | `@36 != "acsp"` | `error: icc_bad_signature` |
| 长度一致 | 头前 u32 != 载体长度 | `error: icc_size_mismatch` |
| class | ∉ {mntr, scnr, prtr, spac, abst, nmcl} | `warning: icc_unknown_class` |
| class | ∈ {spac, abst, nmcl} | `info: icc_class_legal` |
| colorspace/PCS | ∉ {RGB , CMYK, GRAY, XYZ , Lab } | `warning: icc_unknown_space` |
| rendering intent | ∉ 0..3 | `warning: icc_bad_intent` |
| iCCP+sRGB 并存 | 两者皆有 | `warning: iccp_srgb_conflict` |
| iCCP 压缩流 | 首期不解压 | `unknown: compressed_profile_not_inspected` |
| PNG 色彩标记 | `gAMA`/`cHRM` 有无 + `iCCP`/`sRGB` 有无（逐组合） | `info: color_markers` |
| 位深（JPEG SOF 精度 / PNG IHDR bit depth） | 不解码能读到 | `info: color_bit_depth` |
| 位深（WebP 等需解包） | 不解码读不到 | `unknown: color_bit_depth_unknown` |
| CMYK JPEG | **四分量** JPEG（`components == 4`） | `warning: cmyk_jpeg` |
| 默认假设表 | 每次运行逐行带出（见 §8.7） | `info: color_default_assumption` |

- **`icc_missing` 是 `info` 而非 `error`**：无 profile 不是错误（绝大多数图都没有），它是"必须内嵌默认假设表"的触发条件（§8.7 / D2）。
- **`risk` 字段**（`plan/03` §三 / `plan/01` §3 M3 的确定性纪律："风险只出 `risk: high/medium/low/unknown` + 依据，**绝不出具体色值**"）：每条 finding 额外带 `risk`，取值只由下面的映射决定，**不由"我觉得这张图会难看"决定**——本工具不做颜色变换、不出色值。

  | severity | `risk` | 含义 |
  |---|---|---|
  | `error` | `high` | 已确证的元数据缺陷，消费者会据此得到错误呈现 |
  | `warning` | `medium` | 可能改变呈现，但依实现而异（如 should not 级互斥、CMYK） |
  | `unknown` | `unknown` | 不解压/不解码就无法判读 → 风险**不可估**，不假装为零 |
  | `info` | `low` | 观察到的形态，本身不代表风险 |
  | `suspicion` | `low` | 启发式命中（M3 条件 3），只提示不判错 |
- **`cmyk_jpeg` 的触发条件被收窄为"四分量 JPEG"**（`plan/06` D19）：题目原文写"存在 Adobe APP14 `transform` 字段即告警"，但最常见的 YCbCr Adobe JPEG 也带 APP14（`transform=1`，见 `m5_jpeg_app14_pos.jpg` 一类），照抄会把**好样本**误报。APP14 `transform` 仍作为 fact 报出（`facts.app14_transform`），只是不作触发依据。判据本身（"四分量"）落在 SOF 的 `components` 字段上，不靠 @amiantos 原话支撑。
- `icc_header_truncated` / `icc_bad_signature` / `icc_size_mismatch` **在 PNG `iCCP` 上不可达**（不解压，见 D9）：PNG 侧一律走 `unknown: compressed_profile_not_inspected`。三类损坏各配一份 JPEG APP2 孪生样本，**两条行为都被样本证明**（R5）。

### 8.3 帧时长归一化

- `to_ms(gif, delay) = delay * 10`
- `to_ms(apng, num, den) = num / (den == 0 ? 100 : den) * 1000`（用整数运算：`num * 1000 / den`，den=0→100）
- `to_ms(webp, duration) = duration`（已是 ms）
- `to_ms(avif, *) = not-in-band`（首期不判）
- 归一化结果**一律整数毫秒**（`//` 整除），不得出现浮点（`tests/test_cli_contract.py::TestDeterminism::test_json_has_no_floats`）。

**`unit_mismatch` 的判据（唯一实现处）**

§1.9 给出了同一段 **100 ms** 动画的规范取值：`GIF=10`（1/100 s）、`APNG=10/100`（num/den）、
`WebP=100`（ms）。工具对每一帧同时算两个读法：

1. **声明单位**归一化值 `ms`（按上面的 `to_ms`）；
2. **另一单位的量级**假读值 `alt_ms`：GIF 把 `delay` 当 ms（`alt_ms = delay`）；
   APNG 把 `delay_num` 当 ms（`alt_ms = num`）；WebP 把 `duration` 当 1/100 s（`alt_ms = duration * 10`）。

**当 `alt_ms == 100` 且 `ms != 100` 时报 `warning: unit_mismatch`**，facts 固定给
`{raw, raw_unit, ms, expected_ms: 100, factor, scale}`：`factor` 是两者差的倍数（整数，10），
`scale` 是方向（`"10x"` = 声明值大了 10 倍；`"1/10x"` = 声明值小了 10 倍）。
GIF `delay=100` → 声明 1000 ms、假读 100 ms → `10x`；WebP `duration=10` → 声明 10 ms、假读 100 ms → `1/10x`。

**已声明的假阳性代价**：合法的 1 秒 GIF 帧（`delay=100`）与 10 ms WebP 帧在数值上与"单位写错"
不可区分，同样会报 `unit_mismatch`。这是**刻意接受**的：报告同时给出两个读法与 `factor`，
让读者自己看到"归一化值 × 倍率与声明单位自相矛盾"，而不是工具替作者猜意图。
要收紧它，必须先在本节改判据（例如引入同一动画的其它格式副本做交叉比对），不得在代码里就地加阈值。

- `unit_mismatch` 是 `warning`（不是 `error`）：数值本身仍可归一化，错的只是"作者可能写错了单位"。
- **不引入启发式**：本节之外的 M5 判据全部是结构事实（长度 / 序号 / 偏移 / ordinals），
  没有"看起来可疑"型的判断；`unit_mismatch` 的触发条件就是上面这条数值判据，不含主观阈值。


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

### 8.6 `double-rotate` 的三条件、级别与启发式阈值（**唯一定义处**）

**三条件取或**（`condition_hits` 报命中的编号，`certain` / `heuristic` **分列**，不得混算）：

| # | 判据 | confidence | severity |
|---|---|---|---|
| 1 | IFD0 与 IFD1 的 274 **都存在**且值不同 | `certain` | `warning` |
| 2 | XMP `tiff:Orientation` 与 EXIF 274 冲突：两者都存在且值不同；或一方存在且 **≠1** 而另一方缺失 | `certain` | `warning` |
| 3 | 大边启发式命中（定义见下） | `gray-heuristic` | `suspicion` |

**条件 1 / 2 的边界（为什么这么写）**

- 条件 1 要求**两者都存在**：只有 IFD0 有 274、IFD1 没有，是"缩略图没写方向"，不是"不一致"；
- 条件 2 的"一方缺失"分支要求存在的那一方 **≠1**：一方缺失而另一方是 1 时，两个来源描述的
  呈现结果相同（缺省即正常），不构成冲突——这一条同时保证"只有 EXIF=1 + 无 XMP"的干净样本不误报；
- 条件 2 只比对"EXIF 274 的一个值"与"XMP 的一个值"：多个 EXIF 来源（ifd0/ifd1）互不一致
  由条件 1 报，不在此处重复计数。

**条件 3 的确切定义**

- **评估前提**：声明值 `v ∈ {5,6,7,8}`（90° 类旋转）**且**容器读到了存储宽高
  （JPEG SOF / PNG IHDR / WebP VP8X / TIFF tag 256+257）。不满足前提时**不评估**，
  也不报 `unknown`——这不是"不可判"，是"没有可评估的形状"。
- **命中判据**：**存储宽 > 存储高**（`w > h`，大边在水平）。
- **为什么这正是"可疑"**：`v ∈ {5,6,7,8}` 声明"存储像素需要 90° 类旋转"，旋转后有效尺寸是
  **纵向**（`[h, w]`）。而"像素已被手工转正、tag 却没重置成 1"的图，在字节层面与
  "规范的横向传感器数据 + 正确的 tag 6"**完全相同**——两者只能靠解码像素区分（§8.4 第 1 条）
  ⇒ 一律 `confidence: gray-heuristic` + `severity: suspicion`，**不得**升格成 `certain`。
- **已声明的假阳性代价**：规范的手机竖拍照片（存储横向 + tag 5/6/7/8）同样会命中。
  这是**刻意接受**的：该条件只产出 `suspicion`，不参与退出码，也不进入 `certain` 列表，
  因此不会把"正常图"报成"确定转错"。要收紧它，必须先在本节改判据（例如引入解码证据），
  不得在代码里就地加阈值。

**退出码关系**：条件 1/2 落 `warning` → exit 1；条件 3 的 `suspicion` **不计入** §8.5 的 0/1/2/3 判据，
退出码不受影响。要让 `suspicion` 影响退出码，必须先改本节与 `cli.exit_code_for`（不得就地加分支）。

### 8.7 无 profile 时的默认假设表（**唯一定义处**，7 行）

`color` 体检器的"观念交付物"：**每个情形各自记录"各方默认"，不写"大家都假设 sRGB"**（`plan/00` D2）。
表体在报告里 **逐行** 出现（`default_assumptions`），每行带 `source`；
`tests/test_m4_defaults.py` 断言**恰好 7 行**、每行 `id`/`situation`/`assumed`/`source` 四字段非空，
并与本表逐字对账。

| id | 情形 | 本工具记录的"各方默认" | source |
|---|---|---|---|
| png-no-color-chunk | PNG 无任何色彩 chunk（无 `iCCP`/`sRGB`/`gAMA`/`cHRM`） | 多数软件按 sRGB 解释 | HN @kloch 31112951、@meindnoch 50137766（原话） |
| png-srgb-chunk | PNG 有 `sRGB` chunk | 显式 sRGB，无需猜测 | PNG-3 `sRGB` chunk 定义 |
| png-gama-chrm-no-iccp | PNG 有 `gAMA`/`cHRM` 但无 `iCCP` | 依实现各自解释，常见「只取 gamma」 | lr0 案例：`Gamma: 0.454545` 被点名为 ImageMagick 的假设 |
| png-iccp | PNG 有 `iCCP` | 应应用该 profile；Chrome 与 Safari 的行为有分歧 | lr0 案例（单来源） |
| png-iccp-compressed | PNG 的 `iCCP` 是 zlib 压缩流（首期不解压） | 无法判读色彩语义 → `unknown`，不假设任何默认 | `data/README` §8.2 末行（`plan/00` D9） |
| libvips-icc-import-missing | ICC 缺失且调用 libvips `icc_import` | 不假设 sRGB：按 embedded → input_profile 文件 → 内置兼容 profile 三处搜索 | libvips `icc_import` 文档原文（`data/README` §3） |
| jpeg-no-icc | JPEG 无 ICC | 常见假设 sRGB（非规范强制） | ⬜ 待补原文（`data/README` §9） |

- **D2 的硬约束**：第 6 行（libvips）恰恰说"**不**假设 sRGB"——这张表的存在就是为了打破"大家都假设 sRGB"这种笼统说法；措辞里不得出现"都/一律"。
- 第 4 行（`png-iccp` 的 Chrome/Safari 分歧）标为**单来源**（§9 #7），不升格为 `certain` 级结论；
  表里保留这一行的目的是让报告显式写出"已知分歧"，而非断言谁对。
- 第 7 行原文**未取到**（§9），保留 ⬜ 标记——保留一行"尚未核实"的假设，比悄悄删掉它更诚实。

### 8.8 container 检查项（报错级别）

| 检查 | 条件 | 级别 |
|---|---|---|
| PNG chunk 顺序 | IHDR 非首 / IEND 非末 / PLTE、tRNS、色彩/动画 chunk 位置违反 Table 7 | `error: png_chunk_order` |
| IDAT 连续 | 两个 IDAT 之间夹其它 chunk | `error: png_idat_nonconsecutive` |
| CRC 值 | 存储 CRC ≠ 计算值（覆盖 chunk type + data） | `error: png_crc_mismatch` |
| CRC 存在 | chunk 缺少 4 字节 CRC（空数据 chunk 也算） | `error: png_crc_missing` |
| APNG 数量 | `acTL.num_frames` ≠ 实际 `fcTL` 数 | `error: apng_num_frames_mismatch` |
| APNG 序号 | 首 `fcTL` 序号 ≠ 0 / 缺口 / 重复 / 乱序（`fcTL`+`fdAT` 共享序列） | `error: apng_sequence_gap` |
| WebP ANMF | 声明长度超出剩余字节，或载荷 < 16 字节 | `error: webp_anmf_truncated` |
| WebP ANIM | 载荷 ≠ 6 字节（Background u32 + Loop u16） | `error: webp_anim_structure` |
| GIF disposal | 4–7（"To be defined"） | `warning: gif_disposal_undefined` |
| GIF GCE 位置 | GCE 之后不是图像块（无作用域）/ 连续多个 GCE | `error: gif_gce_position` |
| JPEG 段序 | 帧头（SOF）出现在首个 SOS 之后 | `error: jpeg_segment_order` |
| JPEG APP14 位置 | APP14 出现在 SOS 之后 | `error: jpeg_app14_position` |
| 帧时长单位 | `alt_ms == 100` 且 `ms != 100`（10× / 1×，§8.3） | `warning: unit_mismatch` |
| 帧时长归一化 | 每帧带出（含 `unit_mismatch` 的正/反两支） | `info: frame_duration_normalized` |

- `gif_disposal_undefined` 是 `warning`：disposal 4–7 是"To be defined"，不是非法值（不是 error）。
- `unit_mismatch` 的假阳性代价已在本节 §8.3 声明，且**不升级 issue 的退出码**之外的任何东西；
  它计入 exit 1（warning），与 `unknown`→exit 2 是两条线（§8.5）。
- 本表只列 M5 的结果码；`severity → risk` 映射沿用 §8.2 的同一张表（`error→high`、`warning→medium`、
  `info→low`、`unknown→unknown`、`suspicion→low`），不另立一套。

### 8.9 consumers 矩阵、风险清单与加工命令 diff（**唯一定义处**）

> `src/imageoracle/modules/consumers.py` 的表体是本节的**机器可读副本**；
> `tests/test_m6_consumers.py` 解析本表逐字对账（不在测试里另抄一份）。
> 矩阵内容只来自 §2（工具能力矩阵）/ §3（工具原文）/ §4（需求原话）/ §1.x（规范事实），
> **不来自运行时猜测**；星数快照日期 **2026-10-27** 写进报告 `matrix.snapshot_date`。

**行 = 9 个消费者**（固定顺序）：`chrome` / `safari` / `firefox` / `macos_preview` /
`windows_photos` / `imagemagick` / `libvips` / `sharp` / `exiftran`

**列 = 6 列**，取值词表（不在词表里的值 = 实现缺陷）：

| 列 | 取值 | 含义 |
|---|---|---|
| `applies_orientation` | `yes` / `partial` / `no` / `unknown` | 是否应用 EXIF 方向；`partial` = 只在某些容器上成立（如 JPEG 成立、PNG `eXIf` 不成立） |
| `applies_icc` | `yes` / `no` / `unknown` | 是否做色彩管理（**不出具体色值**，只管"应不应用"） |
| `dropped_chunks` | 列表（可空） | 该消费者/命令**会丢掉**的元数据载体。`[]` = 不丢（只读消费，或改写而非丢弃）。元素是 PNG chunk 名（大写）或 `exif_orientation_tag` |
| `double_rotate_risk` | `low` / `medium` / `high` / `unknown` | 双重旋转风险；依据必须是 §3 原文或 §4 原话 |
| `frame_duration` | `per-container-unit` / `unknown` / `n/a` | 动画帧时长解读：按容器规范单位读（GIF 1/100 s、APNG `num/den`、WebP ms，见 §1.9）/ 不可判 / 不适用（不处理动画） |
| `evidence` | `{kind, spec, quote, source, url?}` | 该行依据。`kind ∈ {spec, tool-doc, hn-quote}`；`tool-doc` **必须** `url` + 原文片段 |

**per-row 置信度**：`confidence ∈ {certain, single-source, gray}`，描述**该行 evidence 支撑到的那部分结论**的强度。
没有依据的格一律写 `unknown`（值本身即"不可判"的声明），不另立"未核实清单"：
表里出现 `unknown` 就是已声明，`gray` 行必然有 `unknown` 格。

| consumer | kind | 会应用方向? | 会应用 ICC? | 会丢哪些 chunk? | 双重旋转风险 | 动画帧时长 | confidence | 依据 |
|---|---|---|---|---|---|---|---|---|
| `chrome` | browser | partial（JPEG 成立；PNG `eXIf` 不成立） | yes | [] | medium | per-container-unit | single-source | `hn-quote` `HN-ORIENTATION-PNG`（§4.1 item 46004364 → Bugzilla 1627423） |
| `safari` | browser | partial（同 Chrome 的 PNG 缺口） | yes（PNG `iCCP` 的呈现与 Chrome 不同，单来源） | [] | medium | per-container-unit | single-source | `hn-quote` `HN-ICC-RENDER`（§4.2 item 46403048，lr0 案例） |
| `firefox` | browser | unknown | unknown | [] | unknown | per-container-unit | gray | `hn-quote` `HN-SOFTWARE-EITHER`（§4.1）；第一方文档未取 §9 #11 |
| `macos_preview` | app | unknown | unknown | [] | unknown | unknown | gray | `hn-quote` `HN-SOFTWARE-EITHER`（§4.1）；第一方文档未取 §9 #11 |
| `windows_photos` | app | unknown | unknown | [] | unknown | unknown | gray | `hn-quote` `HN-SOFTWARE-EITHER`（§4.1）；第一方文档未取 §9 #12 |
| `imagemagick` | cli | yes（`-auto-orient`） | yes | [] | high | per-container-unit | certain | `tool-doc` `IMAGEMAGICK-AUTOORIENT-RESET` <https://imagemagick.org/command-line-options/>："reads and resets the EXIF image profile setting 'Orientation'" |
| `libvips` | library | unknown（`autorot` 页未取 §9 #4） | yes（无 profile 时按内置 profile 搜索，不假设 sRGB） | [] | unknown | per-container-unit | single-source | `spec` `ICC-DEFAULTS`（§1.11 / §3） |
| `sharp` | library | yes（只认 EXIF，且移除该 tag） | unknown | ["exif_orientation_tag"] | high | per-container-unit | certain | `tool-doc` `SHARP-AUTOORIENT-REMOVE` <https://sharp.pixelplumbing.com/api-operation>："Auto-orient based on the EXIF Orientation tag, then remove the tag." |
| `exiftran` | cli | yes（读方向、连缩略图一起转、写回 1） | no | [] | low | n/a | certain | `spec` `EXIFTRAN-ROTATE`（§1.13 / §3，**JPEG only**） |

**风险清单**（`{consumer, risk, severity, trigger, confidence, evidence}`）。
`severity` 用 §8.2 的 **risk 词表**（`high` / `medium` / `low` / `unknown`），**不是** finding 的
`error/warning/info` 词表——风险清单描述"若你让这个软件处理这张图会发生什么"，不是文件缺陷。
`trigger` 是**机器可读的触发条件**，工具只对命中的风险出 `info` finding（见本节末的退出码口径）。

| # | consumer | risk | severity | trigger | confidence | 依据 |
|---|---|---|---|---|---|---|
| 1 | `imagemagick` | `-auto-orient` 对"已修正但 tag 未重置"的图会再转一次 | high | `exif_orientation_present` | certain | `IMAGEMAGICK-AUTOORIENT`（§1.10） |
| 2 | `sharp` | `autoOrient()` 只认 EXIF 并移除该 tag，XMP 里残留的方向留给下游 → 再转一次 | high | `xmp_orientation_present` | certain | `SHARP-AUTOORIENT-REMOVE` + `SHARP-AUTOORIENT`（§1.10 / §1.13） |
| 3 | `chrome` | PNG 的 `eXIf` 方向不被采用 → 竖拍 PNG 显示成横的 | medium | `png_exif_orientation_present` | single-source | `HN-ORIENTATION-PNG`（§4.1） |
| 4 | `safari` | PNG `iCCP` 的呈现与 Chrome 不同 → 同一文件两处颜色不一致 | medium | `png_iccp_present` | single-source | `HN-ICC-RENDER`（§4.2） |
| 5 | `jpegtran` | `-copy all -rotate 90` 主图转了、缩略图原样复制 → IFD1 双重旋转 | high | `jpeg_ifd1_present` | certain | `JPEGTRAN-COPYALL`（§1.10） |
| 6 | `oxipng` | `--strip safe` 丢掉 `gAMA`/`cHRM`（**不在保留集**）→ 颜色可能改变 | medium | `png_gama_or_chrm` | certain | `OXIPNG-STRIP-SAFE`（§1.13） |
| 7 | `oxipng` | `--strip all` 把 APNG 转成静态 PNG（动画控制 chunk 全丢） | high | `apng_present` | certain | `OXIPNG-STRIP-ALL`（§1.13） |
| 8 | `oxipng` | `--fix` 不做 CRC 校验 → "用 oxipng 校验过"是伪安全 | medium | `always` | certain | `OXIPNG-FIX`（§1.13） |
| 9 | `exiftran` | **JPEG only** → 对 PNG / WebP / GIF 完全无效 | low | `not_jpeg` | certain | `EXIFTRAN-ROTATE`（§1.13） |
| 10 | `firefox` | 方向 / 色彩行为无可取第一方文档 → 只能标不可判 | unknown | `always` | gray | `HN-SOFTWARE-EITHER`（§4.1） |
| 11 | `macos_preview` | 同上（第一方文档未取 §9 #11） | unknown | `always` | gray | `HN-SOFTWARE-EITHER`（§4.1） |
| 12 | `windows_photos` | 同上（第一方文档未取 §9 #12） | unknown | `always` | gray | `HN-SOFTWARE-EITHER`（§4.1） |
| 13 | `libvips` | `autorot` 文档未取（§9 #4）→ 方向行为不可判 | unknown | `always` | gray | `HN-SOFTWARE-EITHER`（§4.1） |

**处理前后 diff（≥4 条加工命令）**。每条给"哪些 chunk 消失 / 哪些字段变" + 依据原文：

| # | 命令 | 容器 | 会消失 / 会变 | 保留 | 依据 |
|---|---|---|---|---|---|
| 1 | `oxipng --strip safe` | png | 消失：`gAMA`、`cHRM`（不在保留集）；变：颜色标记可能改变 | `cICP` `iCCP` `sRGB` `pHYs` `acTL` `fcTL` `fdAT` | `OXIPNG-STRIP-SAFE` |
| 2 | `oxipng --strip all` | png | 消失：全部 ancillary chunk（含色彩与动画控制）→ **APNG 变静态 PNG** | 仅关键 chunk（`IHDR` `PLTE` `IDAT` `IEND`） | `OXIPNG-STRIP-ALL` |
| 3 | `oxipng --fix` | png | 不变；但**不做 CRC 校验**，坏 CRC 不会被它发现 | — | `OXIPNG-FIX` |
| 4 | `sharp.rotate()`（无参 = `autoOrient()`） | jpeg / png / webp / tiff | 变：EXIF Orientation tag 被**移除**；XMP `tiff:Orientation` **保留**（下游仍会读到旧方向） | 其余元数据 | `SHARP-AUTOORIENT-REMOVE` |
| 5 | `exiftran` | jpeg | 变：方向 tag 改写为 `1`；主图与缩略图**一起**转 | 不丢（改写而非丢弃） | `EXIFTRAN-ROTATE` |
| 6 | `jpegtran -copy all -rotate 90` | jpeg | 变：主图转 90°；IFD1 缩略图**原样复制**、不参与变换 | 其它段原样 | `JPEGTRAN-COPYALL` |

**退出码口径**：`consumers` 的 finding **只出 `info`**。它预言的是"你若跑某条命令会发生什么"，
不是文件本身的缺陷；把风险清单的 `severity` 折进退出码会让每张图都 exit 1/2（含 `always` 触发项）。
风险清单的 `severity` 因此**不参与** `exit_code_for`。要让它影响退出码，必须先改本节与
`cli.exit_code_for`（不得就地加分支，K4/K5）。

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
| 11 | macOS Preview 的方向 / 色彩行为 | 未取第一方文档；M6 矩阵该行标 `gray`（`applies_orientation` / `applies_icc` = `unknown`） |
| 12 | Windows 照片的方向 / 色彩行为 | 未取第一方文档；M6 矩阵该行标 `gray` |
| 13 | `exiftran` / `oxipng` / `jpegtran` / libvips `icc_import` 参数页的**页面 URL** | M6 期尝试取页：exiftran man 页 404、oxipng README 连接被重置、libvips 只取到索引页、jpegtran 未取 → 这些行不挂 `tool-doc`（见 §3.1） |

---

## 10. 引用与复现

- 规范：W3C PNG 3rd ed、RFC 9649（WebP）、GIF89a、Mozilla APNG Specification、ExifTool TagNames（EXIF / ICC_Profile）。
- 需求：HN 条目按 item id 引用；GitHub issue 按 `<owner>/<repo>#<num>` 引用。
- 检索：`gh api search/repositories` + `gh api search/issues`，窗口见文件头。
- 任何引用若与页面现状不符，**以页面现状为准**，并更新本文件（记录更新日期）。
