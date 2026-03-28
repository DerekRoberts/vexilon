import re
from pathlib import Path
from typing import TYPE_CHECKING
from src.vexilon import config

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_embed_model: "SentenceTransformer | None" = None

def get_embed_model() -> "SentenceTransformer":
    global _embed_model
    if _embed_model is None:
        print(f"[embed] Loading local embedding model '{config.EMBED_MODEL}'…")
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(config.EMBED_MODEL)
        _embed_model.max_seq_length = 100000
        if hasattr(_embed_model, "tokenizer"):
            _embed_model.tokenizer.model_max_length = 100000
        print("[embed] Embedding model ready.")
    return _embed_model

def embed_texts(texts: list[str]) -> "np.ndarray":
    import numpy as np
    model = get_embed_model()
    # Ensure it's a list for sentence-transformers
    if isinstance(texts, str):
        texts = [texts]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return np.array(embeddings, dtype=np.float32)

def _get_source_name(stem: str) -> str:
    parts = stem.split("_", 2)
    if len(parts) == 3:
        return parts[2]
    elif len(parts) == 2:
        return parts[1]
    return stem.replace("_", " ").title()

def _is_toc_or_index_page(page_text: str) -> bool:
    lines = [l.strip() for l in page_text.split("\n") if l.strip()]
    if not lines:
        return False
    # Heuristic 1: 3+ dot-leader lines (..........)
    dot_leader_count = sum(1 for l in lines if l.count(".") >= 8 and ".." in l)
    if dot_leader_count >= 3:
        return True
    # Heuristic 2: >40% of lines match index-style pattern "Some Text ... NN"
    index_line_re = re.compile(r".{10,}\.\s*\d{1,3}\s*$")
    index_count = sum(1 for l in lines if index_line_re.search(l))
    return len(lines) >= 5 and index_count / len(lines) > 0.4

def _clean_page_text(page_text: str) -> str:
    page_text = re.sub(r"https?://www\.bclaws\.gov\.bc\.ca/\S*", "", page_text)
    page_text = re.sub(r"\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2}\s+[A-Z][^\n]*", "", page_text)
    return re.sub(r"\n{3,}", "\n\n", page_text).strip()

def chunk_text(full_text: str, token_data: list[tuple[int, int, int, str]], source_name: str) -> list[dict]:
    chunks = []
    if not token_data:
        return chunks
    idx = 0
    start = 0
    while start < len(token_data):
        end = min(start + config.CHUNK_SIZE, len(token_data))
        char_start, _, page_num, header = token_data[start]
        _, char_end, _, _ = token_data[end - 1]
        prefix = f"[{source_name} - {header}] " if header else f"[{source_name}] "
        chunks.append({
            "text": prefix + full_text[char_start:char_end],
            "page": page_num,
            "source": source_name,
            "header": header,
            "chunk_index": idx,
        })
        idx += 1
        start += config.CHUNK_SIZE - config.CHUNK_OVERLAP
    return chunks

def load_md_chunks(md_path: Path) -> list[dict]:
    content = md_path.read_text(encoding="utf-8")
    source_name = _get_source_name(md_path.stem)
    tokenizer = get_embed_model().tokenizer
    token_metadata = []
    current_header, char_offset = "", 0
    for line in content.split("\n"):
        if line.strip().startswith("#"):
            current_header = line.strip().lstrip("#").strip().upper()
        encoding = tokenizer(line, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
        for start_off, end_off in encoding.offset_mapping:
            token_metadata.append((char_offset + start_off, char_offset + end_off, 1, current_header))
        char_offset += len(line) + 1
    return chunk_text(content, token_metadata, source_name)

def load_pdf_chunks(pdf_path: Path) -> list[dict]:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    source_name = _get_source_name(pdf_path.stem)
    tokenizer = get_embed_model().tokenizer
    full_text, token_metadata = "", []
    current_header = ""
    header_pattern = re.compile(r"^\s*(ARTICLE|APPENDIX)\s+(\d+|[A-Z]+)", re.IGNORECASE)
    for page_idx, page in enumerate(reader.pages):
        page_num, page_text = page_idx + 1, page.extract_text() or ""
        if not page_text.strip() or _is_toc_or_index_page(page_text):
            continue
        page_text = _clean_page_text(page_text)
        if not page_text.strip():
            continue
        for line in page_text.split("\n")[:50]:
            if ".........." in line: continue
            match = header_pattern.search(line)
            if match:
                current_header = match.group(0).strip().upper()
                break
        page_offset = len(full_text)
        full_text += page_text + "\n"
        encoding = tokenizer(page_text, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
        for start, end in encoding.offset_mapping:
            token_metadata.append((page_offset + start, page_offset + end, page_num, current_header))
    return chunk_text(full_text, token_metadata, source_name)

def get_all_source_files() -> list[Path]:
    """Scan root and subdirectories for PDF and MD files recursively."""
    if not config.LABOUR_LAW_DIR.exists():
        return []
    # Recursive glob for all tiers
    pdfs = list(config.LABOUR_LAW_DIR.rglob("*.pdf"))
    mds = list(config.LABOUR_LAW_DIR.rglob("*.md"))
    # Filter out hidden folders and tests
    all_files = [
        f for f in pdfs + mds 
        if "tests" not in f.parts and not any(p.startswith(".") for p in f.parts)
    ]
    return sorted(all_files, key=lambda p: p.name)
