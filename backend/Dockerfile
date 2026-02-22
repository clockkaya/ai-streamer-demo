# ============================================================================
#  Dockerfile (v1.1) — 生产镜像构建
#
#  设计原则:
#    - 采用多阶段构建（Multi-stage build）减小最终镜像体积
#    - 镜像本身不包含敏感信息（.env 被 .dockerignore 排除）
#    - 使用非 root 用户运行，提升安全性
# ============================================================================

# ── 阶段 1: 构建依赖 ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装系统级编译依赖（如果有需要编译的 C 扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── 阶段 2: 运行环境 ──────────────────────────────────────────────────
FROM python:3.12-slim

# 创建非 root 用户
RUN useradd -m -s /bin/bash app_user

WORKDIR /app

# Python 运行时优化
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# 复制构建好的虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制业务代码并修改所有权
COPY --chown=app_user:app_user . .

# 切换为非 root 用户
USER app_user

# 构建参数与环境变量
ARG APP_PORT=8000
ENV APP_PORT=${APP_PORT}

EXPOSE ${APP_PORT}

CMD uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}