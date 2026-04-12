#!/usr/bin/env python3
"""
Generate a manifest.json for the FAISS cache directory.
This tracks hashes of source PDFs to validate cache freshness.

Issue #239: FAISS Cache Persistence & Binary Bloat
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, UTC


def hash_file(filepath: Path) -> str:
    """Generate SHA256 hash of file contents."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_manifest(data_dir: Path = Path("data"), output_path: Path = Path(".pdf_cache/manifest.json")) -> dict:
    """Generate manifest of all PDFs in data directory."""
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "version": "1.0",
        "sources": {}
    }
    
    # Find all PDF files in data directory
    pdf_files = sorted(data_dir.rglob("*.pdf"))
    
    for pdf_path in pdf_files:
        relative_path = pdf_path.relative_to(data_dir)
        manifest["sources"][str(relative_path)] = {
            "hash": hash_file(pdf_path),
            "size_bytes": pdf_path.stat().st_size
        }
    
    # Write manifest
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    return manifest


def validate_cache(data_dir: Path = Path("data"), manifest_path: Path = Path(".pdf_cache/manifest.json")) -> bool:
    """Validate that cache matches current source PDFs."""
    if not manifest_path.exists():
        print("ERROR: No manifest.json found. Run generate_cache_manifest.py first.")
        return False
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    current_pdfs = {str(p.relative_to(data_dir)): hash_file(p) for p in data_dir.rglob("*.pdf")}
    
    errors = []
    
    # Check for new/modified files
    for pdf_path, current_hash in current_pdfs.items():
        if pdf_path not in manifest["sources"]:
            errors.append(f"NEW: {pdf_path} (not in manifest)")
        elif manifest["sources"][pdf_path]["hash"] != current_hash:
            errors.append(f"MODIFIED: {pdf_path} (hash mismatch)")
    
    # Check for removed files
    for pdf_path in manifest["sources"]:
        if pdf_path not in current_pdfs:
            errors.append(f"REMOVED: {pdf_path} (in manifest but not in data/)")
    
    if errors:
        print("Cache validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print(f"Cache validation PASSED: {len(current_pdfs)} PDFs match manifest")
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        success = validate_cache()
        sys.exit(0 if success else 1)
    else:
        manifest = generate_manifest()
        print(f"Generated manifest.json with {len(manifest['sources'])} PDFs")
