# RELEASE-M7 —— 发布留档（v0.5.2，M6.1 收口）

> 发布里程碑：**M6**（延续；本文件记第二次发布的收口）。格式仍按 `plan/05` §三：
> §一 在 tag **之前**写完；§二 在 tag **之后**逐行追加（附件 sha256、真实 run id）。
> **附件 sha256 只写在 Release 正文里，不写进 tag 树内的任何文档**（自指失效，D13）。
> 本文件受 `LAYOUT.RELEASE_PLACEHOLDER` 约束：**不许留任何尖括号版本占位符**。

## 一、tag 前事实

| 项 | 事实（本机实测，2026-10-28） |
|---|---|
| 版本（两处一致） | `0.5.2` —— `src/imageoracle/__init__.py` + `pyproject.toml`；`README.md` 状态行同步 |
| 报告 schema | `1`（判决口径未变；本轮 `src/` 一行未改） |
| 测试 | `py -3.12 -m unittest discover -s tests -t .` → **226 项 OK**（222 → 226：+3 自述数字守门 +1 CI action 版本断言） |
| 布局门 | `py -3.12 tools/check_sprint_layout.py` → **全绿**（11 条判据，新增 `LAYOUT.RELEASE_PLACEHOLDER`） |
| 脱敏门 | `py -3.12 tools/check_desensitized.py` → **全绿**（`update/` 已收编进 `SKIP_DIRS`） |
| 门自证 | `py -3.12 tools/verify_gates.py` → **19/19 符合预期，SKIP = 0** |
| fixtures | 54 份不变；`fixtures/gen_all.py --check` → **一致**（本版未动 `src/` 与 `fixtures/`） |
| 元数据 | `license = "MIT"` + `license-files = ["LICENSE"]`（PEP 639）；`requires-python = ">=3.12"`；`setuptools>=77` |
| 构建告警 | `python -m build --sdist --wheel` → **0 条 WARNING**（改前 2 类，各多次） |
| CI 矩阵 | `["3.12", "3.13"]` × ubuntu / windows + `zero-dependency-check` + `offline` |
| actions | `actions/checkout@v7` / `actions/setup-python@v7` |
| 交付面清单 | `src/`、`pyproject.toml`（+ `README.md` / `LICENSE` / `CHANGELOG.md` / `data/` / `plan/` / `fixtures/` / `tests/` / `tools/` / `.github/`） |
| 附件 | **尚未产出**：`git archive --format=tar.gz v0.5.2` 只在 tag 之后可做（D13 手工出包） |

**本轮修的是什么（对应 `update/00-诊断报告.md` 的 D1–D10）**：D1 占位符 / D2 CHANGELOG 与事实相反 /
D3 门的变异永久 SKIP / D4 floor EOL / D5 license 弃用元数据 / D6 自述数字无门 / D8 actions 版本 /
D9 CHANGELOG 段结构 / D7 与 D10 登记为未做（见下）。

**诚实口径（必须原样保留）**：
· 本机**没有 Python 3.10 / 3.11 解释器**（`py -0p` 只列 3.8 与 3.12），抬 floor 后的兼容性只由
  `ast.parse(feature_version=(3,12))` 与 CI 腿覆盖，**不得写"本地 3.12 与 3.13 都实测通过"**。
· `3.13` 腿在本机**没有**对应解释器，只有 CI 能验。

## 二、tag 后追加

> 本节在发布动作执行时逐行回填；未执行的项保持 ⬜（**不许把未执行写成已完成**）。
> 已公开的历史**不删不改写**：v0.5.0 的 tag run 失败原样留在 `plan/RELEASE-M6.md` §二。

| 步骤 | 事实 | 状态 |
|---|---|---|
| 1. `commit` | `aa8e6ef130ddcf6099f461a5304a2ba7fbb372c3`（提交信息以 `v0.5.2` 开头；16 文件 / +512 / −50） | ✅ |
| 2. `git tag -a` | annotated，tag 对象 `cdaaab156f9b388b1ac9fdd47ebc4b80cab8628a`，剥壳指向 `aa8e6ef` | ✅ |
| 3. `push` | `origin/main` `e20f6ec..aa8e6ef`；`origin/v0.5.2` 新推；`git ls-remote --tags origin` 见到 tag 对象与 `^{}` 剥壳两条 | ✅ |
| 4. `git archive` 附件 | `imageoracle-v0.5.2.tar.gz` **226752 字节**，sha256 `c9afab4d014b27b9839a9b47a24d187d2c6016887dff355a2c6d59a8f6565239`；不带 `--prefix`；两次构建 `cmp` = BYTE_IDENTICAL；包内 84 条目 | ✅ |
| 5. `gh release create` | https://github.com/yuluo554/10-27-imageoracle/releases/tag/v0.5.2 （非 draft / 非 prerelease；`/releases/latest` 返回 `v0.5.2`）；附件名与字节数同第 4 行 | ✅ |
| 6. Actions run id | main push = `40681167828`，tag push = `40681227323`，两条 run 各 7 个 job 全 success；本提交的 check-run 共 14 条（2 run × 7）全 success；Node20 弃用注解：两条新 run 日志 `grep -c 'Node.js 20 is deprecated'` = **0**（日志 1897 / 2013 行，非空跑），负向对照旧 run `40533933285` = **7** | ✅ |
| 7. 下载件复验 | `gh release download v0.5.2` → sha256 与正文一致；与 `git archive v0.5.2` 重建件 `cmp` = BYTE_IDENTICAL；解包（无 `.git`）`unittest` → **Ran 226 / OK**，布局门全绿 / 门自证 19/19 / 脱敏门 66 份全绿 / fixtures 一致；M6 留档的 v0.5.1 尖括号占位计数 = **0**；`发布动作待显式授权` = **1**（v0.5.2 条目里对旧措辞的引用，非陈旧断言）；CHANGELOG 已发布版本段 = 3 | ✅ |

## 三、第 7 阶段出口门覆盖对账

> 对齐 `plan/05` §五 的预置表；每行写"本项目怎么满足 / 为什么不适用"。

| 出口门 | 本项目形态 | 状态 |
|---|---|---|
| 附件与 tag 树逐字节同源 | 附件 = `git archive --format=tar.gz v0.5.2` 直接产出；重建一次 `cmp` 比对 | 实现 |
| 源码包自足（`MANIFEST.in`） | 无 sdist 发布面，附件即源码包（`pyproject.toml` 单一构建面） | 不适用（不发 sdist） |
| 无本地数据缓存分支 | 无下载件、无外部数据目录；fixtures 全部程序化生成且产物不入仓 | 不适用（`plan/04` §四） |
| 多平台原生构建 | 纯 Python、零第三方依赖，无交叉编译 | 不适用 |
| Actions job 容器 + `--network none` | CI 用嵌套 `docker run --network none` 跑 offline 作业，不把 job 放容器里 | 实现 |
| 安装面七面对账 | 只用 `pyproject.toml`（无 `setup.cfg` / `MANIFEST.in` / `setup.py`），面数少但逐条写清 | 实现 |
| `POST_TAG` 范围 | `git diff --name-only v0.5.2..HEAD` 只允许 `plan/` `docs/` `tests/` `tools/` `README.md` `AGENTS.md` | 实现（已核对：v0.5.2 之后唯一提交只动 `plan/RELEASE-M7.md`） |
| push 数 = run 数 | 每次 push 恰好一条 run；tag push 另起一条 | 实现（run id 见 §二 第 6 行） |
