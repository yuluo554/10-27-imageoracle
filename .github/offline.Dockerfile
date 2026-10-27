# 离线作业镜像：用于证明"运行期零网络"这条红线。
#
# 注意（ai-tool-project-sprint 阶段 7 实测坑）：
# **不要**把 `--network none` 写进 workflow 的 `container.options`——Actions 建 job 容器时
# 总会先建 user-defined network，与 `--network none` 互斥，报
# `docker: conflicting options: cannot attach both user-defined and non-user-defined network-modes`，
# 整步红在 `Initialize containers`（一行断言都没跑）。
# 正解 = 普通 runner + 嵌套 `docker run --network none`（见 .github/workflows/ci.yml 的 offline job）。
#
# 镜像里**不装任何依赖**：判定路径零第三方依赖，所以 `COPY . /work` 之后直接能跑，
# 这顺带把"零第三方依赖"也一起证明了。

FROM python:3.12-slim

WORKDIR /work
COPY . /work

# 不 pip install：本项目运行时零依赖。
# **但必须把 src/ 放进 PYTHONPATH**——首推实测：不加这一行，`python -m imageoracle`
# 报 `No module named imageoracle`（镜像里没装包，本仓是 src 布局）。
ENV PYTHONPATH=/work/src \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8

CMD ["python", "-m", "imageoracle", "--help"]
