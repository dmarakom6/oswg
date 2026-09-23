# Stage 1: build the SvelteKit UI
FROM node:20-bookworm-slim AS ui
WORKDIR /build
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# Stage 2: runtime
FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OSWG_DATA_DIR=/data \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY pyproject.toml README.md LICENSE .gitignore ./
COPY src ./src
COPY --from=ui /build/build ./src/oswg/static

RUN pip install --no-cache-dir .[js] \
    && playwright install --with-deps chromium

RUN useradd -m -s /bin/bash oswg \
    && mkdir -p /data /ms-playwright \
    && chown -R oswg:oswg /data /ms-playwright /app

USER oswg

VOLUME ["/data"]
EXPOSE 8000
CMD ["oswg", "ui", "--host", "0.0.0.0", "--no-browser"]