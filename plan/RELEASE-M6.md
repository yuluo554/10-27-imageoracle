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
> 已公开的历史**不删不改写**：v0.5.0 的 tag run 失败原样留在下面。

| 步骤 | 事实 | 状态 |
|---|---|---|
| 1. `commit` | `312d8ea`（M1–M6 交付，48 文件 / +8200 行）；`b92a767`（CI 配置修复，仅 `.github/`）；`<v0.5.1>`（版本与留档，本提交） | ✅ |
| 2. `git tag -a` | `v0.5.0` → `312d8ea`；`v0.5.1` → `<v0.5.1>`（含 CI 修复） | ✅ |
| 3. 建 GitHub 公开仓库 | <https://github.com/yuluo554/10-27-imageoracle>（`gh repo create --public`） | ✅ |
| 4. `push` | `origin/main`（`312d8ea`→`b92a767`→…），`origin/v0.5.0`，`origin/v0.5.1` | ✅ |
| 5. `git archive` 附件 | `v0.5.0`：`imageoracle-v0.5.0.tar.gz`，**215387 字节**，sha256 `30351fed8c7b77e1cd817d36999dab029effd5dedf69a78a1bcc476e5b4cf15c`（两次构建 `cmp` 逐字节相同）；`v0.5.1`：见下一行回填 | ✅ / ⬜ |
| 5b. v0.5.1 附件 sha256 | `imageoracle-v0.5.1.tar.gz`，**217536 字节**，sha256 `b4e327f3eb38cda80d6a57ecec7812297d77f64d5427ee234fb8241c9ebe5642`（两次构建 `cmp` 逐字节相同） | ✅（tag 之后回填：该值不能出现在 tag 树内） |
| 6. `gh release create` | `v0.5.0` → <https://github.com/yuluo554/10-27-imageoracle/releases/tag/v0.5.0>（正文含附件 sha256）；`v0.5.1` → 见 6b | ✅ / ⬜ |
| 6b. v0.5.1 Release | <https://github.com/yuluo554/10-27-imageoracle/releases/tag/v0.5.1>；v0.5.0 的正文已加"已被 v0.5.1 取代（仅 CI 配置修复，`src/` 未变）" | ✅（tag 之后回填） |
| 7. Actions run id | **main**：`40530041670` = **failure**（首推，暴露三处配置缺陷）；`40530725648` = **success（7/7）**（`b92a767`）；`40532561921` = **success（7/7）**（`v0.5.1` 提交）。**tag v0.5.0**：`40530040806` = **failure**（tag 树内是旧版 `ci.yml`）。**tag v0.5.1**：`40532972661` = **success（7/7）**。发布后的纯文档提交（`plan/`）同样每次触发一条 run，至今全为 success（例：`40533376903`）——本行不再逐个追加，避免"记录本身又产生一条 run"的无穷回填 | ✅ |
| 8. `git log --oneline v0.5.1..HEAD` 逐条核对 | 发布后只剩"§二 回填 + 收官交接单同步"这一个提交，只动 `plan/`（非交付面） | ✅ |

**首推暴露的三处 CI 配置缺陷（修复提交 `b92a767`，只动 `.github/`）**

1. `gates-and-tests` 的 CLI smoke 报 `No module named imageoracle` —— 本仓是 `src` 布局、不装包
   → job 级 `PYTHONPATH=src`；
2. `windows-latest` 上门的四字节中文输出触发 `UnicodeEncodeError: 'charmap'` →
   `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`；
3. 零依赖断言把 `__main__`（解释器自身）与 `_distutils_hack`（setuptools site hook，3.10 出现）
   当成第三方 → 改用 `python -S` 并显式排除 `__main__`；offline 镜像补 `ENV PYTHONPATH=/work/src`。

→ 这就是 `plan/05` §四 #1 写"CI 待首推验证"的理由：**本地全绿不等于 CI 全绿**，首推才把
"配置面"的缺陷炸出来。v0.5.1 是这个修复的载体；`src/`、`pyproject.toml` 的代码面与 v0.5.0 相同。

**发布后必做的一步（已做）**：三处状态副本 M6 → ✅ 与本节回填同一个提交（`plan/` 与 `README.md`
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
