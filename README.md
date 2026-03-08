# Vexilon — BCGEU Agreement Assistant

AI chatbot for BCGEU union stewards to look up the 19th Main Public Service Agreement
(Social, Information & Health). Ask questions in plain language; get verbatim quotes with
article and page citations.

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Anthropic Claude (`claude-3-5-haiku-20241022`) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector Store | FAISS (in-memory, rebuilt at startup) |
| PDF Parsing | pypdf — preserves page numbers |
| Web UI | Gradio 5 — `http://localhost:7860` |
| PDF Source | Bundled in `pdf_cache/` |
| Container | Podman + Podman Compose (`compose.yml`) |

## Quick Start

### Prerequisites

- [Podman](https://podman.io/docs/installation) + [Podman Compose](https://github.com/containers/podman-compose)
- An [Anthropic API key](https://console.anthropic.com/) (`ANTHROPIC_API_KEY`)
- An [OpenAI API key](https://platform.openai.com/account/api-keys) (`OPENAI_API_KEY`)
  — used only for embeddings (`text-embedding-3-small`)

### Run

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...

podman-compose up
```

Open <http://localhost:7860> in your browser.

> ⏳ **First run:** the app embeds the entire agreement PDF via the OpenAI API (~30–60 s).
> Subsequent starts take the same amount of time — the FAISS index is rebuilt in memory
> each time (no persistence required at this scale).

### Troubleshooting

**`openai.AuthenticationError: 401`** — `OPENAI_API_KEY` is not set or not exported.
Check with `echo $OPENAI_API_KEY` and re-export before running `podman-compose up`:

```bash
export OPENAI_API_KEY=sk-...
podman-compose up
```

**`anthropic.AuthenticationError`** — same issue with `ANTHROPIC_API_KEY`.

## Usage

The app is ready immediately on page load — no dropdown, no Load button.

1. Type a question in the input field and press **Enter** or tap **Send**
2. Or click one of the suggested question chips on the welcome screen
3. Responses include a plain-language explanation followed by verbatim quotes with citations

> **Note:** Responses cite the agreement text only. This is not legal advice.
> Consult your BCGEU staff representative for complex matters.

## Configuration

All settings are optional — defaults match the product specification.

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `OPENAI_API_KEY` | *(required)* | OpenAI API key (embeddings only) |
| `CLAUDE_MODEL` | `claude-3-5-haiku-20241022` | Claude model for responses |
| `EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `PORT` | `7860` | Gradio listen port |
| `SIMILARITY_TOP_K` | `5` | Chunks retrieved per query |
| `CHUNK_SIZE` | `512` | Tokens per chunk |
| `CHUNK_OVERLAP` | `100` | Token overlap between chunks |

## Hugging Face Spaces Deployment

Set `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` as Spaces secrets. The `pdf_cache/`
directory is committed to the repo and available at runtime. No persistent volume
is required — the FAISS index is rebuilt on each cold start.

## Project Structure

```
vexilon/
├── app.py            # Main application (RAG pipeline + Gradio UI)
├── requirements.txt  # Python dependencies
├── manifest.json     # PWA manifest
├── Containerfile     # Container image definition
├── compose.yml       # Podman Compose — single vexilon service
├── SPEC.md           # Product specification
└── pdf_cache/        # Bundled PDFs (committed to repo)
```
