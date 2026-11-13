FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai

# 先拷贝依赖，利用docker缓存层（优先单独copy requirements.txt，改动代码不重新装包）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 一次性拷贝当前目录全部内容到 /app
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
