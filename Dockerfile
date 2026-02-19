# ============================================================================
#  Dockerfile — 生产镜像构建
#
#  引用关系:
#    Dockerfile  ──构建──>  Docker 镜像
#    docker-compose.yml  ──引用──>  Dockerfile (build: .)
#    容器运行时  ──注入──>  .env 中的环境变量  ──>  app/core/config.py
#
#  设计原则:
#    - 镜像本身不包含任何敏感信息（.env 被 .dockerignore 排除）
#    - 镜像本身不包含知识库数据（通过 volume 挂载）
#    - 端口和启动参数通过 ARG/ENV 参数化，避免硬编码
# ============================================================================

# 1. 基础镜像
FROM python:3.12-slim

# 2. 工作目录
WORKDIR /app

# 3. Python 运行时优化
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 4. 构建参数：可在 docker-compose.yml 或 docker build --build-arg 中覆盖
ARG APP_PORT=8000
ENV APP_PORT=${APP_PORT}

# 5. 依赖安装（独立层，利用 Docker 构建缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 复制业务代码
COPY . .

# 7. 暴露服务端口
EXPOSE ${APP_PORT}

# 8. 启动命令（读取 APP_PORT 环境变量）
CMD uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}