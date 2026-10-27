# RELEASE-M6 —— 发布留档（v0.5.0）

> 发布里程碑：**M6**（`consumers` 矩阵 + 发布）。本文件两栏格式由 `plan/05` §三 规定：
> §一 在 tag **之前**写完；§二 在 tag **之后**逐行追加（附件 sha256、真实 run id）。
> **附件 sha256 只写在本文件的 Release 正文里，不写进 tag 树内的任何文档**（自指失效，D13）。

## 一、tag 前事实

| 项 | 事实（本机实测，2026-10-27） |
|---|---|
| 版本（两处一致） | `0.5.0` —— `src/imageoracle/__init__.py` + `pyproject.toml`；`README.md` 状态行同步 |
| 报告 schema | `1`（判决口径未变，只新增模块） |
| 测试 | `py -3.12 -m unittest discover -s tests -t .` → **222 项 OK**（M6 新增 42 项） |
| 布局门 | `py -3.12 tools/check_sprint_layout.py` → **全绿**（10 条判据） |
| 脱敏门 | `py -3.12 tools/check_desensitized.py` → **全绿**（扫 63 份文本） |
| 门自证 | `py -3.12 tools/verify_gates.py` → **18/18 符合预期** |
| fixtures | 54 份（四族：M2 22 / M3 3 / M4 14 / M5 15），`fixtures/manifest.json` 冻结 sha256 |
| CLI 命令面 | `orientation` / `double-rotate` / `color` / `container` / `consumers` —— 五个子命令全部落地，`modules.PLANNED` 为空 |
| 交付面清单 | `src/`、`pyproject.toml`（+ `README.md` / `LICENSE` / `CHANGELOG.md` / `data/` / `plan/` / `fixtures/` / `tests/` / `tools/` / `.github/`） |
| 附件 | **尚未产出**：`git archive --format=tar.gz v0.5.0` 只在 tag 之后可做（D13 手工出包） |
| 状态副本 | 三处（`plan/00` / `plan/05` §二 / `README.md`）**此刻仍为 M6 ⬜**——按纪律，"tag + Release + 留档"未执行前不得写 ✅ |

**诚实口径（必须原样保留）**：仓库**无远端**，**CI 从未实跑**——本文件与所有文档都不得写"CI 绿"。
本地等价校验 = 全量 `unittest`（222 项）+ 两道门 + `verify_gates.py` 变异验证，均在无网络下可跑。

## 二、tag 后追加

> 本节在发布动作执行时逐行回填；未执行的项保持 ⬜（**不许把未执行写成已完成**）。

| 步骤 | 事实 | 状态 |
|---|---|---|
| 1. `commit` | 待执行（工作区当前未提交） | ⬜ |
| 2. `git tag -a v0.5.0` | 待执行 | ⬜ |
| 3. 建 GitHub 公开仓库（`yuluo554/10-27-imageoracle`） | 待执行（`gh auth status` 已登录 `yuluo554`，scope 含 `repo`） | ⬜ |
| 4. `git push origin main` / `git push origin v0.5.0` | 待执行 | ⬜ |
| 5. `git archive --format=tar.gz v0.5.0` → 附件 | 待执行；产出后在此写 **sha256**（只写 Release 正文） | ⬜ |
| 6. `gh release create v0.5.0 <tarball> --notes-file …` | 待执行 | ⬜ |
| 7. Actions run id（branch + tag 两条） | 待首推后回填真实 run id（当前 `plan/05` §四 #1 = 未接远端） | ⬜ |
| 8. `git log --oneline v0.5.0..HEAD` 逐条核对 | 待发布后执行：只允许非交付面（`plan/`、`docs/`、`tests/`、`tools/`、`README.md`、`AGENTS.md`） | ⬜ |

**发布后必做的一步**：三处状态副本 M6 → ✅ 与本节回填**同一个提交**（`plan/` 与 `README.md`
属于允许的 POST_TAG 面）。

## 三、第 7 阶段出口门覆盖对账

> 对齐 `plan/05` §五 的预置表；每行写"本项目怎么满足 / 为什么不适用"。

| 出口门 | 本项目形态 | 状态 |
|---|---|---|
| 附件与 tag 树逐字节同源 | 附件 = `git archive --format=tar.gz v0.5.0` 直接产出；重建一次 `cmp` 比对 | 实现 |
| 源码包自足（`MANIFEST.in`） | 无 sdist 发布面，附件即源码包（`pyproject.toml` 单一构建面） | 不适用（不发 sdist） |
| 无本地数据缓存分支 | 无下载件、无外部数据目录；fixtures 全部程序化生成且产物不入仓 | 不适用（`plan/04` §四） |
| 多平台原生构建 | 纯 Python、零第三方依赖，无交叉编译 | 不适用 |
| Actions job 容器 + `--network none` | CI 用嵌套 `docker run --network none` 跑 offline 作业，不把 job 放容器里 | 实现 |
| 安装面七面对账 | 只用 `pyproject.toml`（无 `setup.cfg` / `MANIFEST.in` / `setup.py`），面数少但逐条写清 | 实现 |
| `POST_TAG` 范围 | `git diff --name-only v0.5.0..HEAD` 只允许 `plan/` `docs/` `tests/` `tools/` `README.md` `AGENTS.md` | 实现 |
| push 数 = run 数 | 无远端期不适用；首推后按"每次 push 恰好一条 run"不变量核对 | 待首推 |
