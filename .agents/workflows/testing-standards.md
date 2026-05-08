---
description: Testing architecture, mocking requirements, and CI/CD testing gates
---

# Testing Standards

This document defines the testing protocols for Vexilon. **All agents must verify changes against these standards before reporting success.**

## 1. The "Mock-First" Rule

### Hugging Face (HF) Isolation
- **MANDATORY**: All unit tests must mock `get_embed_model()` and `SentenceTransformer` to prevent 3GB model downloads in CI.
- **Fixture**: Use the `mock_embedding_model` fixture in `conftest.py`.

### LLM Client Mocking
- **Fixture**: Use `mock_llm_client` for all non-integration tests. 
- **Constraint**: Mocks must support both streaming (`unified_chat_stream`) and non-streaming (`unified_chat_create`) calls.

## 2. Test Categorization

### Unit Tests (`tests/`)
- **Location**: `tests/test_*.py`
- **Focus**: UI logic, regex sanitizers, rate limiters, and chunking math.
- **Run**: `pytest tests/ -v`

### Integration Tests (`tests/integration/`)
- **Environment**: REQUIRES `ollama` profile.
- **Focus**: Full RAG pipeline flow from query to response.
- **Run**: `docker compose --profile integration up test-integration`

### E2E / Smoke Tests (`scripts/smoke_e2e.py`)
- **Environment**: REQUIRES `ollama` profile.
- **Focus**: Functional validation of the Gradio interface and final response integrity.

## 3. Coverage & Verification

### Mandatory Coverage
- **Core Logic**: `app.py` and `agnav/indexing.py` must maintain >80% coverage.
- **Report**: Coverage reports are automatically uploaded as artifacts in `pr-open.yml`.

### Deployment Integrity
- **Script**: `tests/test_deploy_integrity.py`
- **Rule**: This test checks for GHCR lowercasing and HF metadata compliance. Never skip this test.
