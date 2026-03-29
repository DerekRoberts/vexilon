#!/usr/bin/env python3
"""
check_parity.py — Knowledge Base Integrity Monitor
--------------------------------------------------
Ensures every PDF in data/labour_law/ has a corresponding .md file.
Used as a CI gate to force Markdown conversion for RAG optimization.
"""

import sys
from pathlib import Path

DATA_DIR = Path("data/labour_law")

def check_parity():
    if not DATA_DIR.exists():
        print(f"Directory {DATA_DIR} not found. Skipping parity check.")
        return 0

    # Skip the tests/ and .pdf_cache directories
    skip_dirs = {DATA_DIR / "tests", DATA_DIR / ".pdf_cache"}
    
    pdfs = [
        p for p in DATA_DIR.rglob("*.pdf") 
        if not any(p.is_relative_to(s) for s in skip_dirs)
    ]
    
    missing_md = []
    for pdf in pdfs:
        md_file = pdf.with_suffix(".md")
        if not md_file.exists():
            missing_md.append(pdf)
            
    if missing_md:
        print("❌ KNOWLEDGE BASE INTEGRITY ERROR:")
        print("The following PDFs are missing a corresponding .md file for RAG retrieval:")
        for m in missing_md:
            print(f"  - {m}")
        print("\nAction required: Run `scripts/pdf_to_md.py` on these files and commit the Markdown.")
        return 1
    
    print(f"✅ Parity check passed: {len(pdfs)} PDFs found, all have Markdown equivalents.")
    return 0

if __name__ == "__main__":
    sys.exit(check_parity())
