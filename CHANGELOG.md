# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)；日期为 UTC。

## [Unreleased] — v0.1.0

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
  - CLI `imagineoracle`（`python -m imageoracle`）：子命令 `orientation`（已实现）；
    退出码唯一出口 `exit_code_for`（0/1/2/3）。
- fixtures：`fixtures/lib/build.py` 纯字节构造 + `fixtures/lib/manifest.py` 冻结真值；
  `fixtures/gen_orientation.py` 产出 22 个 orientation 族样本与 `fixtures/manifest.json`；
  `--check` 两层断言（manifest + 冻结产物）。
- 测试：47 项，标准库 `unittest`；含 6=CW90 单测、分层 AST 守门、零依赖/零网络守门、
  双跑逐字节确定性、只读不改源文件、退出码优先级。
- CI：`.github/workflows/ci.yml`（3.10/3.12 × ubuntu/windows + offline 作业）。
  **未接远端，CI 待首推验证**。

### 已知边界

- 不解码像素（硬约束）：所有"像素实际如何"的结论落 `gray` / `suspicion`。
- PNG `iCCP` 压缩流首期**不解压** → `unknown: compressed_profile_not_inspected`。
- AVIF 帧时长在 ISOBMFF track 时序里，不在图像样本内 → 只报 `not-in-band`。
- fixtures 是**结构性**样本：工具读的字段精确，但像素数据不可解码（`manifest.json` 的 `notes` 已写明）。
