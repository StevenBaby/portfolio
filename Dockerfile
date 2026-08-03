# ── Stage 1: build frontend ──
FROM docker.io/node:22-alpine AS frontend-builder

WORKDIR /app
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ ./
RUN npm run build

# ── Stage 2: runtime ──
FROM docker.io/python:3.14-slim

WORKDIR /app

# System deps
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    nginx curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY api/requirements.txt ./
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    -r requirements.txt

# Backend code
COPY api/ ./api/

# Frontend static from stage 1
COPY --from=frontend-builder /app/dist /app/static

# Nginx config
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Startup script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

CMD ["/entrypoint.sh"]
