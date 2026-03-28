import json
import time
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING
from src.vexilon import config, loader

if TYPE_CHECKING:
    import faiss
    import numpy as np

def embed_texts(texts: list[str]) -> "np.ndarray":
    """Embed a list of texts using the local sentence-transformers model."""
    import numpy as np
    model = loader.get_embed_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.astype(np.float32)

def build_index(chunks: list[dict]) -> "faiss.IndexFlatIP":
    """Build a FAISS inner-product index from chunks."""
    import faiss
    texts = [c["text"] for c in chunks]
    print(f"[index] Embedding {len(texts)} chunks locally…")
    t0 = time.time()
    vectors = embed_texts(texts)
    print(f"[index] Embeddings complete in {time.time() - t0:.1f}s")
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(config.EMBED_DIM)
    index.add(vectors)
    return index

def save_index(index: "faiss.IndexFlatIP", chunks: list[dict]) -> None:
    """Persist the FAISS index and chunks to disk."""
    import faiss
    config.PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(config.INDEX_PATH))
    with open(config.CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)
    print(f"[index] Saved index to {config.PDF_CACHE_DIR}")

def load_precomputed_index() -> tuple["faiss.IndexFlatIP", list[dict]] | tuple[None, None]:
    """Load pre-computed index if both index and chunks exist."""
    if not config.INDEX_PATH.exists() or not config.CHUNKS_PATH.exists():
        return None, None
    import faiss
    index = faiss.read_index(str(config.INDEX_PATH))
    with open(config.CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"[startup] Loaded pre-computed index ({index.ntotal} vectors).")
    return index, chunks

def search_index(index: "faiss.IndexFlatIP", chunks: list[dict], query: str, top_k: int = config.SIMILARITY_TOP_K) -> list[dict]:
    """Return top-k most similar chunks for a query."""
    import faiss
    query_vec = embed_texts([query])
    faiss.normalize_L2(query_vec)
    _scores, indices = index.search(query_vec, top_k)
    return [chunks[i] for i in indices[0] if i < len(chunks)]

def build_index_from_sources(force: bool = False) -> tuple["faiss.IndexFlatIP", list[dict]]:
    """Smart Refresh: Build index from all source files in hierarchical layout."""
    all_files = loader.get_all_source_files()
    if not all_files:
        print("[build] No source files found to index!")
        return None, []

    # Manifest hash comparison
    current_manifest = {}
    for source_file in all_files:
        hasher = hashlib.sha256()
        with open(source_file, "rb") as f:
            while chunk := f.read(65536): hasher.update(chunk)
        current_manifest[source_file.name] = hasher.hexdigest()

    if not force and config.MANIFEST_PATH.exists():
        try:
            with open(config.MANIFEST_PATH, "r") as f:
                if json.load(f) == current_manifest and config.INDEX_PATH.exists() and config.CHUNKS_PATH.exists():
                    print("[build] Smart Refresh: No changes detected.")
                    return load_precomputed_index()
        except: pass

    print(f"[build] Scanning Sources in {config.LABOUR_LAW_DIR}…")
    chunks = []
    for f in all_files:
        if f.suffix.lower() == ".pdf": chunks.extend(loader.load_pdf_chunks(f))
        elif f.suffix.lower() == ".md": chunks.extend(loader.load_md_chunks(f))

    print(f"[build] Loaded {len(chunks)} chunks from {len(all_files)} files.")
    index = build_index(chunks)
    save_index(index, chunks)
    with open(config.MANIFEST_PATH, "w") as f: json.dump(current_manifest, f, indent=2)
    return index, chunks

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    build_index_from_sources(force=args.rebuild)
