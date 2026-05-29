# syntax=docker/dockerfile:1
FROM python:3.11

WORKDIR /app

# 安装 uv
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple uv

# 时区设置
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 先复制 requirements.txt，利用 Docker 层缓存
COPY requirements.txt .

# 安装依赖（gcc/g++ 已内置）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --index-strategy unsafe-best-match \
    -r requirements.txt

# 复制项目代码
COPY . .

RUN mkdir -p /app/data/db /app/data/cache

CMD ["python", "scripts/run_dashboard.py"]
