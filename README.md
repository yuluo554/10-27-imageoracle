# ImageOracle

**图像呈现预言机** —— 在打开一张图之前，预言它在 Chrome / Safari / Firefox / macOS Preview /
Windows 照片 / ImageMagick / libvips / sharp / exiftran 里会显示成什么样。

> **不是校验器，是呈现结果的预言机。**

纯本地 CLI：**只读字节**。不解码像素、不做颜色变换、不联网、不写回源文件。

## 它回答什么问题

- 这张图的 EXIF Orientation 会被哪些软件应用、哪些忽略？会不会被转**两次**？
- 缩略图（IFD1）与主图方向不一致吗？XMP 里那个 `tiff:Orientation` 会不会让下游再转一次？
- PNG 里那个 `iCCP` 是真 ICC 还是残骸？`iCCP` 和 `sRGB` 凭什么同时存在？
- 这段 100 ms 的动画，被写成 GIF / APNG / WebP 时单位对不对？
- 我要是跑一遍 `oxipng --strip safe`，会丢掉哪些让人看出颜色变化的 chunk？

## 它**不是**什么

| 不做 | 理由 |
|---|---|
| EXIF / 隐私剥离 | 已商品化，没有增量 |
| 真实颜色变换（不引 lcms） | 只做体检与预言，不做引擎 |
| 解码像素 | 硬约束：只读字节。"像素实际如何"一律落 `gray` / `suspicion` |
| HEIC / AVIF 转码 | 转码不是预言；AVIF 只报"帧时长不在样本内" |
| C2PA / ELA 取证 / 色彩校色 | 与"可复核判决"的定位冲突 |

## 安装

需要 Python ≥ 3.10（开发与冻结值用 3.12）。**零第三方依赖**。

```bash
git clone https://github.com/yuluo554/10-27-imageoracle && cd 10-27-imageoracle
```

**两种跑法，任选一种**：

```bash
# A. 不安装（推荐先这样试；Windows 上 PYTHONPATH 用 $env:PYTHONPATH="src"）
PYTHONPATH=src py -3.12 -m imageoracle --help

# B. 安装到当前环境
py -3.12 -m pip install -e .
imageoracle --help
```

> Windows 上 `python` 可能是商店占位符；本项目命令一律写 `py -3.12`。

## 首条命令

```bash
PYTHONPATH=src py -3.12 -m imageoracle orientation --json path/to/photo.jpg
PYTHONPATH=src py -3.12 -m imageoracle double-rotate --json path/to/photo.jpg    # M3 已实现
PYTHONPATH=src py -3.12 -m imageoracle color --json path/to/photo.png           # M4 已实现
PYTHONPATH=src py -3.12 -m imageoracle container --json path/to/anim.apng       # M5 已实现
PYTHONPATH=src py -3.12 -m imageoracle consumers --json path/to/photo.jpg       # M6 已实现：9×6 消费者矩阵
```

退出码：`0` 无风险 / `1` 有 warning / `2` 有 error 或不可判 / `3` 输入不可解析。发布：<https://github.com/yuluo554/10-27-imageoracle/releases>。
口径唯一定义处：`data/README.md` §8.5。

## 开发

```bash
py -3.12 -m unittest discover -s tests -t .    # 全量测试（222 项，零依赖）
py -3.12 tools/check_sprint_layout.py          # 布局门（方法论装订）
py -3.12 tools/check_desensitized.py           # 脱敏门
py -3.12 tools/verify_gates.py                 # 两道门的变异验证（18 组必须全部如期变红/绿）
```

**前置条件**：样本不入仓（隐私红线 + 生成物纪律），想就地复算需要先跑生成器：

```bash
py -3.12 fixtures/gen_all.py           # 生成全部 54 个样本到 fixtures/out/，并汇写 fixtures/manifest.json
py -3.12 fixtures/gen_all.py --check   # 只校验：四族内存重生成 vs manifest（+ 冻结产物，若在）
```

## 仓库结构

`plan/` 计划套件（`00`–`06` + `HANDOFF-*`）｜`data/README.md` 依据台账与数值口径唯一定义处｜
`src/imageoracle/` 实现（容器层 readers → 语义层 model → 判决层 modules → 呈现层 report）｜
`fixtures/` 生成器（产物不入仓）｜`tools/` 两道常驻门 + 变异验证｜`tests/` 标准库 unittest。

方法论：本仓库遵循 `ai-tool-project-sprint`（装订 2026-10-27），入口见 `AGENTS.md`。

## 状态

| 里程碑 | 状态 | 备注 |
|---|---|---|
| M0 | ✅ | 计划套件 + 装订 + 骨架 + 两道门（本地等价校验） |
| M1 | ✅ | 数据先行：fixtures 生成器（四族 54 样本 + 冻结 manifest） |
| M2 | ✅ | `orientation` 判定器（22 份样本逐条对账，本地等价校验） |
| M3 | ✅ | 双重旋转探测器（IFD1 未同步 / XMP 残留 / 大边启发式，本地等价校验） |
| M4 | ✅ | `color` 体检器（ICC 载体 + 128B 头 + 默认假设表 7 行，本地等价校验） |
| M5 | ✅ | `container` 校验器（PNG/APNG/WebP/GIF/JPEG 结构 + 帧时长归一化，本地等价校验） |
| M6 | ✅ | `consumers` 矩阵 + 发布（v0.5.0 首发、v0.5.1 CI 修复；留档见 `plan/RELEASE-M6.md`） |

版本：`0.5.1`。CI：已接远端，`main` 上 7/7 job 全绿（run `40530725648`）；v0.5.0 的 tag run 失败经过与修复记在 `plan/RELEASE-M6.md` §二。

## 许可

MIT，见 `LICENSE`。
