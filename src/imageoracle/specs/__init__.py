# -*- coding: utf-8 -*-
"""规范条款库：`evidence.spec` 的**唯一来源**。

每条 = ID + 原文片段 + 来源 URL。判决层只准引用这里的 ID，测试断言
`evidence.spec` 必须能在本表里查到（`selftest_evidence_complete`）。

**条款原文一律逐字来自 `data/README.md`**（§1 台账 / §8 口径），不得改写、不得意译——
改了就不是证据，而是转述。新增条款必须同时在 `data/README.md` 登记来源与三态
（M3 的四条登记在 §1.10，测试解析该表逐字比对）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecClause:
    id: str
    title: str
    quote: str
    source: str


CLAUSES: dict[str, SpecClause] = {
    # ── EXIF / TIFF ────────────────────────────────────────────────────────
    "EXIF-TAG274": SpecClause(
        id="EXIF-TAG274",
        title="EXIF Orientation（tag 274 = 0x0112，int16u）语义",
        quote=(
            "1 Horizontal (normal); 2 Mirror horizontal; 3 Rotate 180; "
            "4 Mirror vertical; 5 Mirror horizontal and rotate 270 CW; "
            "6 Rotate 90 CW; 7 Mirror horizontal and rotate 90 CW; 8 Rotate 270 CW"
        ),
        source="https://exiftool.org/TagNames/EXIF.html",
    ),
    "TIFF-BYTEORDER": SpecClause(
        id="TIFF-BYTEORDER",
        title="TIFF 字节序由头部 II/MM 决定",
        quote="int16u 按 TIFF 头声明的字节序读，不得固定小端",
        source="data/README.md §1.1",
    ),
    # ── 双重旋转（M3）：`data/README.md` §1.10 表的机器可读副本 ────────────────
    # 原文是**工具文档/issue 原话**（"需求依据"），逐字取自 §1.10；测试解析该表对账。
    "SHARP-AUTOORIENT": SpecClause(
        id="SHARP-AUTOORIENT",
        title="sharp 只按 EXIF Orientation 归一（其余位置携带的方向不处理）",
        quote="Only the EXIF Orientation tag is considered; orientation carried in other places",
        source="sharp rotate()/autoOrient() 文档；lovell/sharp#4585",
    ),
    "JPEGTRAN-COPYALL": SpecClause(
        id="JPEGTRAN-COPYALL",
        title="jpegtran -copy all 时缩略图原样复制、不参与变换",
        quote="Thumbnails are copied as-is and not transformed",
        source="jpegtran -copy all man 页",
    ),
    "IMAGEMAGICK-AUTOORIENT": SpecClause(
        id="IMAGEMAGICK-AUTOORIENT",
        title="ImageMagick -auto-orient 对「已修正但 tag 未重置」的图会再转一次",
        quote="images already corrected without resetting the tag may be rotated wrongly a second time",
        source="ImageMagick -auto-orient 文档",
    ),
    "GRAY-DECODE-REQUIRED": SpecClause(
        id="GRAY-DECODE-REQUIRED",
        title="需要解码像素才能确认的结论一律 gray / suspicion",
        quote='需要解码像素才能确认（如"像素实际是否已被转过"）',
        source="data/README.md 第 8.4 节第 1 条",
    ),
    # ── ICC ───────────────────────────────────────────────────────────────
    "ICC-HEAD": SpecClause(
        id="ICC-HEAD",
        title="ICC profile 128 字节头字段与偏移",
        quote=(
            "ProfileSize@0(BE u32); ProfileCMMType@4; ProfileVersion@8; ProfileClass@12; "
            "ColorSpaceData@16; ProfileConnectionSpace@20; ProfileDateTime@24; "
            "ProfileFileSignature@36(=acsp); PrimaryPlatform@40; CMMFlags@44; "
            "DeviceManufacturer@48; DeviceModel@52; DeviceAttributes@56; "
            "RenderingIntent@64; ConnectionSpaceIlluminant@68; ProfileCreator@80; "
            "ProfileID@84; 100–127 保留"
        ),
        source="https://exiftool.org/TagNames/ICC_Profile.html",
    ),
    # ── 色彩体检（M4）：`data/README.md` §1.11 表的机器可读副本 ────────────────
    # 原文逐字取自 §1.11；`tests/test_m4_color.py` 解析该表对账（不另抄一份）。
    "ICC-CARRIERS": SpecClause(
        id="ICC-CARRIERS",
        title="ICC profile 的四种载体",
        quote=(
            "ICC carrier: JPEG APP2 ICC_PROFILE\\0 (multi-segment, index i/n); PNG iCCP; "
            "WebP ICCP; TIFF tag 34675"
        ),
        source="ExifTool ICC_Profile 页；ICC 规范 APP2 分片约定（data/README §1.11）",
    ),
    "ICC-NOT-INSPECTED": SpecClause(
        id="ICC-NOT-INSPECTED",
        title="PNG iCCP 压缩流首期不解压",
        quote="PNG iCCP carries a zlib-compressed profile; first release does not decompress it",
        source="data/README.md §8.2 末行（plan/00 D9）",
    ),
    "ICC-DEFAULTS": SpecClause(
        id="ICC-DEFAULTS",
        title="无 profile 时 libvips 不假设 sRGB（默认假设表依据）",
        quote="Otherwise, libvips will try to pick a compatible profile from the set of built-in profiles",
        source="libvips icc_import 文档；data/README.md §3",
    ),
    "CMYK-APP14": SpecClause(
        id="CMYK-APP14",
        title="CMYK JPEG 跨浏览器渲染不一致（需求依据，非技术依据）",
        quote=(
            "CMYK JPEGs are the bane of my existence. A recent annoyance was a realization "
            "that they don't render consistently in different browsers."
        ),
        source="HN @amiantos 29284352（data/README.md §4.2）",
    ),
    "PNG-COLOR-CHUNKS": SpecClause(
        id="PNG-COLOR-CHUNKS",
        title="PNG 色彩 chunk 的位置约束",
        quote="cHRM/cICP/gAMA/iCCP/sBIT/sRGB before PLTE and IDAT",
        source="https://www.w3.org/TR/png-3/ Table 7",
    ),
    "COLOR-BITDEPTH": SpecClause(
        id="COLOR-BITDEPTH",
        title="不解码即可读到的位深字段",
        quote=(
            "PNG: IHDR bit depth (single byte); JPEG: SOF precision (single byte, 8 or 12); "
            "WebP: bit depth lives in the bitstream and needs unpacking"
        ),
        source="W3C PNG-3 IHDR；ITU T.81 SOF（data/README.md §1.11）",
    ),
    # ── PNG ───────────────────────────────────────────────────────────────
    "PNG3-T7": SpecClause(
        id="PNG3-T7",
        title="PNG 3rd ed Table 7 — chunk 顺序",
        quote=(
            "The IHDR chunk shall be the first chunk; IEND shall be last; "
            "PLTE before first IDAT; Multiple IDAT chunks shall be consecutive; "
            "cHRM/cICP/gAMA/iCCP/sBIT/sRGB before PLTE and IDAT; "
            "acTL/eXIf/pHYs/sPLT before IDAT; bKGD/hIST/tRNS after PLTE and before IDAT; "
            "fcTL: one may occur before IDAT, all others shall be after IDAT; fdAT after IDAT"
        ),
        source="https://www.w3.org/TR/png-3/",
    ),
    "PNG3-CRC": SpecClause(
        id="PNG3-CRC",
        title="PNG CRC 覆盖范围",
        quote=(
            "A four-byte CRC calculated on the preceding bytes in the chunk, "
            "including the chunk type field and chunk data fields"
        ),
        source="https://www.w3.org/TR/png-3/",
    ),
    "PNG3-CRC-PRESENT": SpecClause(
        id="PNG3-CRC-PRESENT",
        title="PNG CRC 恒存在",
        quote="The CRC is always present, even for chunks containing no data.",
        source="https://www.w3.org/TR/png-3/",
    ),
    "PNG3-ICCP-SRGB": SpecClause(
        id="PNG3-ICCP-SRGB",
        title="iCCP 与 sRGB 互斥（should not）",
        quote="If the iCCP chunk is present, the sRGB chunk should not be present",
        source="https://www.w3.org/TR/png-3/",
    ),
    # ── APNG ──────────────────────────────────────────────────────────────
    "APNG-SEQ": SpecClause(
        id="APNG-SEQ",
        title="APNG 序号与 num_frames 规则",
        quote=(
            "The first fcTL chunk must contain sequence number 0; "
            "sequence numbers must be in order, with no gaps or duplicates; "
            "Decoders must treat out-of-order APNG chunks as an error; "
            "num_frames must equal the number of fcTL chunks; "
            "acTL must appear in the stream before any IDAT chunks"
        ),
        source="https://wiki.mozilla.org/APNG_Specification",
    ),
    "APNG-DELAY": SpecClause(
        id="APNG-DELAY",
        title="APNG delay_den=0 按 100 处理",
        quote="delay_den of 0 is treated as if it were 100",
        source="https://wiki.mozilla.org/APNG_Specification",
    ),
    # ── WebP ──────────────────────────────────────────────────────────────
    "WEBP-ANMF": SpecClause(
        id="WEBP-ANMF",
        title="WebP ANMF Frame Duration = uint24 毫秒",
        quote=(
            "Frame Duration | 24 (uint24) | The time to wait before displaying "
            "the next frame, in 1-millisecond units."
        ),
        source="https://www.rfc-editor.org/rfc/rfc9649",
    ),
    "WEBP-ANIM": SpecClause(
        id="WEBP-ANIM",
        title="WebP ANIM = Background Color(u32, BGRA) + Loop Count(u16)",
        quote="Background Color (u32, [Blue, Green, Red, Alpha]) + Loop Count (u16, 0 = infinite)",
        source="https://www.rfc-editor.org/rfc/rfc9649",
    ),
    # ── GIF ───────────────────────────────────────────────────────────────
    "GIF89A-GCE": SpecClause(
        id="GIF89A-GCE",
        title="GIF89a Graphic Control Extension：disposal 与 delay 单位",
        quote=(
            "Disposal Method: 0 No disposal specified; 1 Do not dispose; "
            "2 Restore to background color; 3 Restore to previous; 4-7 To be defined. "
            "Delay Time is in 1/100 second units."
        ),
        source="https://www.w3.org/Graphics/GIF/spec-gif89a.txt",
    ),
    "GIF89A-GCE-SCOPE": SpecClause(
        id="GIF89A-GCE-SCOPE",
        title="GIF89a Graphic Control Extension 的作用域 = 紧随其后的第一个渲染块",
        quote="The scope of this extension is the first graphic rendering block to follow.",
        source="GIF89a spec §23, https://www.w3.org/Graphics/GIF/spec-gif89a.txt",
    ),
    # ── 容器结构（M5）：ITU-T T.81 / GIF89a 原文 ─────────────────────────────
    "JPEG-T81-FRAME": SpecClause(
        id="JPEG-T81-FRAME",
        title="JPEG 帧以帧头开始；帧头/扫描头之前可放表或杂项（APPn）段",
        quote=(
            "The second level of Figure B.2 specifies that a frame shall begin with a frame header "
            "and shall contain one or more scans. A frame header may be preceded by one or more "
            "table-specification or miscellaneous marker segments as specified in B.2.4. "
            "Each scan header may be preceded by one or more table-specification or miscellaneous "
            "marker segments."
        ),
        source="ITU-T T.81 §B.2.1, https://www.w3.org/Graphics/JPEG/itu-t81.pdf",
    ),
    # ── 跨格式帧时长单位（M5）：`data/README.md` §1.9 / §8.3 的机器可读副本 ──────
    "FRAME-UNITS": SpecClause(
        id="FRAME-UNITS",
        title="跨格式帧时长归一化口径（整数 ms）",
        quote=(
            "GIF: delay * 10; APNG: delay_num / (delay_den == 0 ? 100 : delay_den) * 1000; "
            "WebP: duration (already ms); AVIF: not-in-band"
        ),
        source="data/README.md §1.9 / §8.3",
    ),
    # ── 消费者矩阵（M6）：`data/README.md` §1.13 表的机器可读副本 ────────────────
    # 前五条逐字来自 §3；三条 HN-* 逐字来自 §4；CONSUMER-MATRIX 是 §8.9 的内部口径。
    # `tests/test_m6_consumers.py` 解析 §1.13 表逐字对账（不另抄一份）。
    "OXIPNG-STRIP-SAFE": SpecClause(
        id="OXIPNG-STRIP-SAFE",
        title="oxipng --strip safe 的保留集（gAMA/cHRM 不在其中）",
        quote="cICP, iCCP, sRGB, pHYs, acTL, fcTL, fdAT",
        source="oxipng --strip safe 文档（data/README.md §3）",
    ),
    "OXIPNG-STRIP-ALL": SpecClause(
        id="OXIPNG-STRIP-ALL",
        title="oxipng --strip all 会把 APNG 转成静态 PNG",
        quote="CAUTION: 'all' will convert APNGs to standard PNGs.",
        source="oxipng --strip all 文档（data/README.md §3）",
    ),
    "OXIPNG-FIX": SpecClause(
        id="OXIPNG-FIX",
        title="oxipng --fix 不做 CRC 校验",
        quote="Do not perform checksum validation of PNG chunks.",
        source="oxipng --fix 文档（data/README.md §3）",
    ),
    "SHARP-AUTOORIENT-REMOVE": SpecClause(
        id="SHARP-AUTOORIENT-REMOVE",
        title="sharp rotate()（无参 = autoOrient）按 EXIF 方向转正后移除该 tag",
        quote="Auto-orient based on the EXIF Orientation tag, then remove the tag.",
        source="https://sharp.pixelplumbing.com/api-operation（data/README.md §3 / §3.1）",
    ),
    "IMAGEMAGICK-AUTOORIENT-RESET": SpecClause(
        id="IMAGEMAGICK-AUTOORIENT-RESET",
        title="ImageMagick -auto-orient 读并重置 EXIF Orientation",
        quote="reads and resets the EXIF image profile setting 'Orientation'",
        source="https://imagemagick.org/command-line-options/（data/README.md §3 / §3.1）",
    ),
    "EXIFTRAN-ROTATE": SpecClause(
        id="EXIFTRAN-ROTATE",
        title="exiftran 读方向、连缩略图一起转、把方向写回 1；JPEG only",
        quote=(
            "can rotate images automatically by checking the exif orientation tag; "
            "it also rotates the exif thumbnail; "
            "By default exiftran sets the orientation to '1'; JPEG only"
        ),
        source="exiftran 文档（data/README.md §3）",
    ),
    "HN-ORIENTATION-PNG": SpecClause(
        id="HN-ORIENTATION-PNG",
        title="PNG 的 EXIF 方向在浏览器的 image-orientation: from-image 下未被采用（需求依据）",
        quote="EXIF orientation info in PNGs isn't used for image-orientation: from-image",
        source="HN 107pts 2025-11-21 item 46004364（data/README.md §4.1）",
    ),
    "HN-ICC-RENDER": SpecClause(
        id="HN-ICC-RENDER",
        title="同一张 PNG 在 Chrome 与 Safari 的呈现不同（需求依据）",
        quote="PNG in Chrome shows a different image than in Safari or any desktop app",
        source="HN 70pts item 46403048（data/README.md §4.2）",
    ),
    "HN-SOFTWARE-EITHER": SpecClause(
        id="HN-SOFTWARE-EITHER",
        title="软件对 EXIF 方向的支持因软件而异（需求依据）",
        quote=(
            "Random software package either supports the EXIF orientation or it doesn't. "
            "If it doesn't, Joe User just sees the photo rotated wrong, and they want to fix it."
        ),
        source="HN 5026565 2013-01-08（data/README.md §4.1）",
    ),
    "HN-COLOR-IGNORED": SpecClause(
        id="HN-COLOR-IGNORED",
        title="大量软件忽略色彩管理（需求依据）",
        quote=(
            "Browsers, chat apps, social media apps, Outlook and all other email clients, "
            "Teams, Zoom, Adobe Photoshop (really!), DaVinci Resolve (a colorist tool ffs)"
        ),
        source="HN 38978724 2024-01-13（data/README.md §4.2）",
    ),
    "CONSUMER-MATRIX": SpecClause(
        id="CONSUMER-MATRIX",
        title="消费者矩阵的行/列口径（内部口径）",
        quote=(
            "rows = chrome, safari, firefox, macos_preview, windows_photos, imagemagick, "
            "libvips, sharp, exiftran; columns = applies_orientation, applies_icc, "
            "dropped_chunks, double_rotate_risk, frame_duration, evidence"
        ),
        source="data/README.md §8.9",
    ),
}


def get(spec_id: str) -> SpecClause:
    """取条款；未知 ID 直接抛 KeyError——宁可炸在测试里，不要产出无依据的判决。"""
    return CLAUSES[spec_id]


def known_ids() -> frozenset[str]:
    return frozenset(CLAUSES)
