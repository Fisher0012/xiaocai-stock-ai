FROM python:3.11-slim

WORKDIR /app

# 系统依赖(tushare 依赖 pandas/numpy, 用系统级 gcc 加速安装)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖(先复制 requirements 用 Docker layer 缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 项目代码
COPY core/ ./core/
COPY serve_http.py serve_mcp.py ./

# 默认端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "serve_http:app", "--host", "0.0.0.0", "--port", "8080"]
