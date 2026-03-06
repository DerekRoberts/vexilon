# blabot — BCGEU Collective Agreement RAG Chatbot

AI chatbot for answering questions about BC Government / BCGEU collective agreements,
powered by a local LLM via Ollama and a persistent vector index via Chroma DB.

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Ollama `llama3.1:8b` (local) |
| Embeddings | Ollama `nomic-embed-text` (local) |
| RAG Framework | LlamaIndex v0.10+ |
| Vector Store | Chroma DB — persisted in `./chroma_db/` |
| Web UI | Gradio — `http://localhost:7860` |
| PDF Source | [agreements.bcgeu.ca](https://agreements.bcgeu.ca/) |

## Quick Start

### 1 — Install Ollama and pull the required models

```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh

ollama pull llama3.1:8b        # ~4.7 GB
ollama pull nomic-embed-text   # ~274 MB
```

### 2 — Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3 — Run

```bash
python app.py
```

Open <http://localhost:7860> in your browser.

## Usage

1. Select an agreement from the dropdown
   (e.g. *"20th Main Public Service Agreement"*)
2. Click **📥 Load Agreement**
   (~10 s on first load; instant on subsequent loads from the Chroma cache)
3. Ask questions in the chat:

| Example question | What you get |
|------------------|--------------|
| `Article 12 overtime rules?` | Article text + page citation |
| `What is the probationary period?` | Relevant clause + page |
| `health victoria` | Island Health HR: 250-519-3500 |
| `health northern` | Northern Health HR: 250-565-2000 |

> **Note:** All responses are prefixed with *"From document only—not legal advice."*

## BC Contacts

Type any of the following keywords (case-insensitive) to look up HR contacts
without querying the document:

| Keyword | Result |
|---------|--------|
| `health island` / `health victoria` | Island Health HR — 250-519-3500 |
| `health northern` | Northern Health HR — 250-565-2000 |
| `health interior` | Interior Health HR — 1-800-707-8550 |
| `health fraser` | Fraser Health HR — 604-587-4600 |
| `health coastal` | Vancouver Coastal Health HR — 604-875-4111 |
| `health providence` | Providence Health Care HR — 604-682-2344 |
| `health phsa` | PHSA HR — 604-875-2000 |
| `health first nations` | FNHA — 604-693-6500 |
| `bcgeu` | BCGEU Provincial Office — 604-291-9611 |
| `corrections` | BC Corrections Labour Relations — 250-387-5041 |
| `cssea` | CSSEA — 604-942-0505 |

## Manual PDF Upload

If the automatic PDF download fails (e.g. the document URL changes), upload
the PDF directly via the **Upload PDF** file picker in the UI.

## Supported Agreements

| Display Name | Source |
|---|---|
| 20th Main Public Service Agreement | agreements.bcgeu.ca |
| ETO Component Agreement | agreements.bcgeu.ca |
| Health Services Agreement | agreements.bcgeu.ca |
| Community Living Services Agreement | agreements.bcgeu.ca |

## Hugging Face Spaces Deployment

Ollama is not available on HF Spaces out of the box. Options:

- Set `OLLAMA_BASE_URL` to an external Ollama server endpoint
- Swap the LLM / embedding imports for `llama_index.llms.huggingface`
  and `llama_index.embeddings.huggingface`

```bash
# HF Spaces secret / environment variable
OLLAMA_BASE_URL=https://your-ollama-server.example.com
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `PORT` | `7860` | Gradio listen port |

## Project Structure

```
blabot/
├── app.py            # Main application (LlamaIndex + Gradio)
├── requirements.txt  # Python dependencies
├── manifest.json     # PWA manifest
├── chroma_db/        # Chroma vector store (auto-created, git-ignored)
└── pdf_cache/        # Downloaded PDFs (auto-created, git-ignored)
```
