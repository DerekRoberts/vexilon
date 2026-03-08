# ─── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Install system deps: libgomp1 for FAISS, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Store HuggingFace model cache in /tmp so the non-root user can write to it.
# TRANSFORMERS_OFFLINE=1 suppresses network checks and cache-miss writes at runtime
# since the model is baked into the image; HF_DATASETS_OFFLINE silences a related warning.
ENV HF_HOME=/tmp/hf_cache \
    TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1

# Install Python deps in a separate layer so code changes don't bust the cache
COPY requirements.txt .
# Install CPU-only torch first to avoid pulling the 3 GB CUDA variant that
# sentence-transformers would otherwise resolve via the default PyPI index.
RUN pip install --no-cache-dir \
        torch \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# ─── Pre-download the embedding model so cold starts don't hit the network ────
# The model is ~90 MB; baking it into the image eliminates the HF Hub download
# on every container start. HF_HOME is already set above.
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
    && echo "[build] Embedding model cached."

# ─── App layer ────────────────────────────────────────────────────────────────
COPY app.py manifest.json ./
COPY pdf_cache/ ./pdf_cache/

# ─── Non-root user ────────────────────────────────────────────────────────────
RUN useradd --uid 1001 --no-create-home --shell /sbin/nologin vexilon \
    && chown -R 1001:1001 /app

USER 1001

# Gradio listens on 7860 by default
EXPOSE 7860

CMD ["python", "app.py"]
