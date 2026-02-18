# 1. 采用 Python 3.12 的精简版官方镜像作为基础，大幅减小打包后的体积
FROM python:3.12-slim

# 2. 设置容器内的工作目录
WORKDIR /app

# 3. 设置环境变量：防止 Python 生成 .pyc 文件，并强制控制台输出不带缓冲（方便看日志）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 4. 优化构建缓存：先单独复制 requirements.txt 并安装依赖
# 这样只要依赖没变，每次改代码重新打包时，Docker 都会直接复用依赖层的缓存，极速秒级构建！
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 把当前目录下的所有业务代码复制到容器的 /app 目录下
COPY . .

# 6. 暴露 FastAPI 运行的 8000 端口
EXPOSE 8000

# 7. 容器启动时执行的终极命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]