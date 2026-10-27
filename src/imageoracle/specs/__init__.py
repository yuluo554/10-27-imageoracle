# -*- coding: utf-8 -*-
"""规范条款库：`evidence.spec` 的**唯一来源**。

每条 = ID + 原文片段 + 来源 URL。判决层只准引用这里的 ID，测试断言
`evidence.spec` 必须能在本表里查到（`selftest_evidence_complete`）。

**条款原文一律逐字来自 `data/README.md` §1 台账**，不得改写、不得意译——
改了就不是证据，而是转述。新增条款必须同时在 `data/README.md` 登记来源与三态。
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
}


def get(spec_id: str) -> SpecClause:
    """取条款；未知 ID 直接抛 KeyError——宁可炸在测试里，不要产出无依据的判决。"""
    return CLAUSES[spec_id]


def known_ids() -> frozenset[str]:
    return frozenset(CLAUSES)
