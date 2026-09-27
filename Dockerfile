# ---- Stage 1: frontend build ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend + static ----
FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
# deps only first (cache-friendly)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
# app code + root modules required by app/services/pubmed_service.py
COPY app/ ./app/
COPY pubmed_client.py models.py ./
COPY README.md ./
COPY --from=frontend /build/dist ./frontend/dist
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]