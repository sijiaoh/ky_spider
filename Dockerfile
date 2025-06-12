FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install uv
RUN uv sync --frozen

# 安装Playwright浏览器
RUN uv run playwright install chromium
RUN uv run playwright install-deps

# 创建输出目录
RUN mkdir -p downloads

# 暴露端口
EXPOSE 8080

# 启动命令 - 生产环境使用Gunicorn
CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "web_app:app"]