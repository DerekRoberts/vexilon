# FAISS Cache Workflow

Issue #239: Optimize FAISS Cache Persistence & Resolve Binary Bloat

## Overview

This project uses a FAISS index for fast similarity search over PDF documents. The index is built from source PDFs in `data/` and cached in `.pdf_cache/`.

## Git LFS Configuration

Binary cache files are tracked via Git LFS to prevent repository bloat:

```bash
# .gitattributes
.pdf_cache/*.faiss filter=lfs diff=lfs merge=lfs -text
.pdf_cache/*.pkl filter=lfs diff=lfs merge=lfs -text
.pdf_cache/*.json filter=lfs diff=lfs merge=lfs -text
```

## Cache Validation

The `manifest.json` tracks SHA256 hashes of all source PDFs. This enables:

1. **Automated staleness detection** — CI validates that the cache matches current PDFs
2. **Reproducible builds** — Knowing exactly which source files were indexed
3. **Audit trail** — Tracking when PDFs change

### Regenerating the Manifest

After updating PDFs in `data/`:

```bash
python scripts/generate_cache_manifest.py
```

### Validating the Cache

```bash
python scripts/generate_cache_manifest.py validate
```

## CI Integration

The PR workflow validates the cache before running tests:

1. Checks out code with LFS
2. Runs `generate_cache_manifest.py validate`
3. Fails the build if cache is stale

This ensures the production image always has a current index.

## Future Improvements

- [ ] Decouple cache from Docker image (fetch from S3/HF at runtime)
- [ ] Add automated cache rebuild on PDF changes
- [ ] Compress cache artifacts for faster LFS operations
