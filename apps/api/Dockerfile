# SynLive API 镜像
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 先装依赖（利用层缓存）
COPY requirements.txt .
RUN pip install -r requirements.txt

# 再拷业务代码
COPY app ./app

EXPOSE 8000

# docker compose 里由 env 注入配置；这里只起服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
