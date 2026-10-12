# Afterparty: one image, the web app built into the Python package that serves it.
#   docker build -t afterparty .
#   docker build -t afterparty --build-arg EXTRAS=gcp .   # adds Google Cloud KMS support

FROM node:22-alpine AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
# vite.config.ts writes to ../src/afterparty/static
RUN mkdir -p /build/src/afterparty && npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv
ARG EXTRAS=""
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project ${EXTRAS:+--extra $EXTRAS}
COPY src ./src
COPY --from=web /build/src/afterparty/static ./src/afterparty/static
# The connector source. /afterparty-extension.zip is built from it for PUBLIC_URL.
COPY extension ./extension
RUN uv sync --frozen --no-dev ${EXTRAS:+--extra $EXTRAS}
ENV PATH=/app/.venv/bin:$PATH CONNECTOR_DIR=/app/extension
USER nobody
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn afterparty.app:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
