# ─── Stage 0: Base System & Package Manager ───────────────────────────────────
FROM python:3.14-slim AS base

# System paths, Hugging Face configurations, and environment variables
ENV HF_HOME=/hf_cache \
    EMBED_MODEL=/model \
    CHAINLIT_FILES_DIR=/tmp/chainlit_files

# Install basic runtime libraries and extraction utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libjpeg62-turbo \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Extract and install uv (in sync with pyproject.toml Renovate tracking)
COPY app/pyproject.toml /tmp/pyproject.toml
RUN pip install --no-cache-dir uv==$(grep -oP 'uv==\K[\d.]+' /tmp/pyproject.toml) && \
    rm /tmp/pyproject.toml

# Create unprivileged container user once
RUN useradd --uid 1000 --create-home --shell /sbin/nologin app
WORKDIR /app

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=10 \
  CMD curl -f http://localhost:7860/ || exit 1

# ─── Stage 1: Model Fetcher ──────────────────────────────────────────────────
# Downloads heavy embedding model weights separately to leverage build caches.
FROM base AS model_fetcher
RUN --mount=type=cache,target=/root/.cache/hf_v4 \
    uv pip install --system --extra-index-url https://download.pytorch.org/whl/cpu torch sentence-transformers && \
    python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('BAAI/bge-small-en-v1.5', cache_folder='/root/.cache/hf_v4'); model.save('/model')" && \
    ls -l /model/modules.json

# ─── Stage 2: Unified Developer & Testing Builder ────────────────────────────
# The primary local build target. Contains build headers, full dev/test environments,
# and compiles the pre-computed FAISS RAG index.
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Build isolated Production and Development virtual environments
COPY app/pyproject.toml app/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/venv uv sync --frozen --no-dev --no-install-project && \
    UV_PROJECT_ENVIRONMENT=/venv-dev uv sync --frozen --no-install-project

# Inherit dev environment path for dev/test container runs
ENV PATH="/venv-dev/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT=/venv-dev

# Compile RAG index (Cached unless data/ or indexing logic changes)
COPY --from=model_fetcher /model /model
COPY app/data/ ./data/
COPY app/indexing.py ./
COPY app/scripts/build_index.py ./scripts/
RUN --mount=type=cache,target=/app/.pdf_cache_mount \
    mkdir -p /app/.pdf_cache && \
    cp -r /app/.pdf_cache_mount/* /app/.pdf_cache/ 2>/dev/null || true && \
    TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 python scripts/build_index.py && \
    cp -r /app/.pdf_cache/* /app/.pdf_cache_mount/ 2>/dev/null || true

# Copy rest of the application files in optimal cache order
COPY app/.chainlit/ ./.chainlit/
COPY app/public/ ./public/
COPY app/chainlit.md app/chainlit_en-US.md ./
COPY app/data/ ./public/docs/
COPY app/main.py ./
COPY app/patches.py ./
COPY app/conftest.py ./
COPY app/prompts/ ./prompts/
COPY app/scripts/ ./scripts/
COPY app/tests/ ./tests/

# Prepare directories for local testing and Chainlit runtime with non-root ownership
RUN mkdir -p /app/reports /app/.pytest_cache /hf_cache /app/.files /app/.pdf_cache && \
    chown -R 1000:1000 /app/reports /app/.pytest_cache /hf_cache /app/.files /app/.pdf_cache /app/.chainlit

# ─── Stage 3: Minimal, Hardened Production Runner ─────────────────────────────
# The clean, locked-down image compiled for production deployments.
FROM base AS runner

ENV CHAINLIT_FILES_DIR=/tmp/chainlit_files \
    PATH="/venv/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT=/venv

# Copy pure production dependencies and built app (with compiled FAISS index)
COPY --chown=app:app --from=builder /venv /venv
COPY --chown=app:app --from=builder /app /app
COPY --from=model_fetcher /model /model

RUN mkdir -p /hf_cache && chown -R app:app /hf_cache
USER 1000

ARG VERSION="Dev mode"
ARG REPO_URL="https://github.com/MinionTech/vexilon"
ENV AGNAV_VERSION=$VERSION \
    AGNAV_REPO_URL=$REPO_URL

CMD ["sh", "-c", "TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=0 chainlit run main.py --host 0.0.0.0 --port 7860 --headless"]
