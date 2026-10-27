# AGENTS.md

本仓库遵循 **`ai-tool-project-sprint`** 方法论（装订日期：2026-10-27）。

## 任何新对话的第一件事

```bash
python tools/check_sprint_layout.py    # 布局门（方法论装订）；必须绿，红了先修布局再干活
python tools/check_desensitized.py     # 脱敏门；改过文档就必须跑
```

- 续接对话：读 `plan/HANDOFF-M<k>.md`（那是第 k 棒的收尾交接单），**先跑上面两条门**。
- 接手对话（无 HANDOFF）：先读 `plan/00`、`plan/05`、`plan/06` 与各 HANDOFF，重建「当前状态 + K 口径清单」再动手。
- **门不存在 = 本项目没装订** → 先补第零步（锚点 + 门 + `plan/00` 顶部一行），再做别的。
- 本机实测环境坑（2026-10-27）：`python` 指向 Microsoft Store 占位符且为 3.8.8，**必须用 `py -3.12`**；
  本机**没有** `exiftool` / `jpegtran` / `sharp` / `magick` → 所有 fixture 必须**纯 Python 字节构造**，
  不得依赖外部工具链（见 `data/README.md` §7 与 `plan/04` §二）。

## 强制布局（布局门逐条断言，改动前先看这里）

| 项 | 位置 | 判据 |
| --- | --- | --- |
| 计划套件 | `plan/00`–`plan/06` + `data/README.md` + 根 `README.md` | 存在且各含必需小节（标题关键词） |
| 数据台账 | `data/README.md` | 台账在位（三态 ✅/⚠️/⬜ + 来源 + 数值口径唯一定义处） |
| 交接单 | `plan/HANDOFF-M<k>.md` | 每个 ✅ 里程碑一份，**七节**齐（含「当前事实·状态不变量」） |
| 里程碑状态副本 | `plan/00` 里程碑表 + `plan/05` 状态表 + `README.md` 状态行 | **逐处一致**，表格行才机读 |
| 承诺-证据台账 | `plan/00`「承诺-证据台账」 | 已成 ✅ 的里程碑不得在台账里挂 ⬜ |
| 缺口表 | `plan/06`「缺口」表 | 缺口格不得再提已成 ✅ 的里程碑 |
| 发布留档 | `plan/RELEASE-M6.md` 或 `plan/WRAPUP-M6.md` | 仅在 M6 翻 ✅ 后要求（未完成时报「尚不适用」） |
| 文档点名的工具 | `tools/*.py` | 文档提到就必须有实物（在位的脚本逐个断言存在） |

**已声明的豁免与冻结规则**（门必须复用，不许另立更严的一套）：

1. **M0（计划与骨架）不单出交接单**：其收尾记录 = 计划套件本身（`plan/00`–`06` + 两道门 + `plan/HANDOFF-M1.md`）。
2. **里程碑编号口径**：`M0` 计划与骨架 / `M1` 数据先行 / `M2` orientation 判定器 / `M3` 双重旋转探测器 /
   `M4` color 体检器 / `M5` container 校验器 / `M6` consumers 矩阵 + 发布。
   题目文档（`plan/01`）里的「M1–M5」指**模块名**（orientation/double-rotate/color/container/consumers），
   与本表的里程碑号错开一位；映射表固定在 `plan/05` §一，**以 `plan/05` 为准**。
3. **不是交付面的目录**：`tests/`、`tools/`、`docs/`、`plan/` 可以随时改；`src/`、`rules/`、`pyproject.toml`
   是交付面，改它们要同步升版本号（`src/imageoracle/__init__.py` 与 `pyproject.toml` 两处一起改）。

## 环境事实与禁忌

- 本机（2026-10-27 实测）：Python 3.12.10 可用（`py -3.12`）；Node v24.15.0；git 2.54.0.windows.1。
  外部图像工具链（exiftool / jpegtran / sharp / ImageMagick）**全部缺失**。
- 运行时不联网、不解码像素、不写回源文件：这是产品红线，也是测试断言的判据面。
- **禁止**把「未执行」写成已完成。无远端期间，CI 相关 DoD 一律写「本地等价校验（未接远端，CI 待首推验证）」，
  不许写「CI 绿」。
- 门命令只能改判据实现，不能靠删引用消红（删引用 = 静默取消出口门）。
