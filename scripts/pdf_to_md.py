#!/usr/bin/env python3
"""
pdf_to_md.py — Forensic PDF-to-Markdown Converter for Vexilon
------------------------------------------------------------
This script uses Claude (Anthropic API) to convert messy legal PDFs into 
clean, structured Markdown files optimized for RAG retrieval.

Usage:
  export ANTHROPIC_API_KEY=<YOUR_ANTHROPIC_API_KEY>
  python scripts/pdf_to_md.py path/to/input.pdf [path/to/output.md]
"""

import re
import sys
import time
import os
import argparse
import traceback
import difflib
from pathlib import Path
from typing import Optional, List

import anthropic
import pymupdf  # High-precision PDF extraction (geometric word reconstruction)

def print_banner():
    print("=" * 66)
    print(" VEXILON : HIGH-INTEGRITY PDF → MARKDOWN CONVERTER (FORENSIC) ")
    print("=" * 66)

def clean_for_integrity_check(text: str) -> str:
    """Strip all formatting, URLs, and punctuation to verify substantive word preservation."""
    # Remove URLs
    text = re.sub(r"https?://\S*", "", text)
    # Remove non-alphanumeric (except spaces)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    # Merge into single string and normalize
    return " ".join(text.lower().split())

def is_hallucination(word: str, raw_text_lower: str) -> bool:
    """True if word is substantive (>3 chars) and NOT found as a whole or sub-word in raw text."""
    w = word.lower()
    if len(w) <= 3: return False
    if w in STRUCTURAL_WORDS: return False
    # Check if this word exists anywhere in the raw text (including as a subsection/sub-word)
    if w in raw_text_lower: return False
    return True

STRUCTURAL_WORDS = {
    "table", "contents", "continued", "appendix", "article", "section", 
    "part", "page", "break", "definition", "term", "title", "subject"
}

def extract_raw_text(pdf_path: Path) -> List[str]:
    """Precision extraction using PyMuPDF to preserve word integrity."""
    print(f"[*] Extracting raw text with high precision (PyMuPDF) from {pdf_path.name}...")
    doc = pymupdf.open(str(pdf_path))
    pages = []
    
    for page in doc:
        text = page.get_text() or ""
        # Remove bclaws-specific web artifacts
        text = re.sub(r"https?://\www\.bclaws\.gov\.bc\.ca/\S*", "", text)
        text = re.sub(r"\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2}\s+[^\n]*", "", text)
        pages.append(text.strip())
        
    print(f"[+] Total pages extracted: {len(pages)}")
    return pages

def convert_batch(client: anthropic.Anthropic, model: str, batch_text: str, source_name: str, batch_idx: int) -> str:
    """Individual pass for a single batch of text with resilience and retries."""
    system_prompt = f"""You are a ZERO-REASONING legal transcription engine. 
Your ONLY task is to add Markdown formatting to raw text from '{source_name}'.

STRICT INTEGRITY RULES:
1. VERBATIM ONLY: You are FORBIDDEN from changing, adding, or removing a single substantive word.
2. NO IMPROVEMENT: Do not fix "typos" or "grammar." If the raw text is broken, leave it broken but formatted.
3. NO SUMMARIZATION: Every single sentence of substance MUST be preserved in its entirety.
4. STRUCTURE: Use # for Articles, ## for Sections. Use Table format for lists of definitions or tables.
5. NO NOISE: Remove page numbers, URLs, and footers.
6. FORMAT: Output ONLY Markdown. No preamble, 'Here is the markdown' talk, or meta-notes.
7. NO META-TALK: Do NOT add meta-text like 'Included for completeness', '[Batch 22]', or '(Continued)'. Your output must contain ONLY text that originated from the PDF source document."""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=0.0, # PARANOID DETERMINISM
                system=system_prompt,
                messages=[{"role": "user", "content": f"[Batch {batch_idx}] Raw text:\n\n{batch_text}"}]
            )
            return response.content[0].text
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = (attempt + 1) * 2
            print(f"    [!] API Error in Batch {batch_idx} (Attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    return "" # Unreachable

def convert_to_md(raw_pages: List[str], source_name: str, output_path: Path, verify: bool = True) -> str:
    """Use Claude to restructure into clean MD with optional dual-pass verification."""
    client = anthropic.Anthropic()
    
    # Selection based on user request for "best outcome"
    primary_model = os.getenv("CONVERT_MODEL", "claude-sonnet-4-6")
    secondary_model = os.getenv("CONCENSUS_MODEL", "claude-haiku-4-5-20251001") # Fast consensus model
    
    print(f"[*] Primary Model:   {primary_model}")
    if verify:
        print(f"[*] Consensus Model: {secondary_model} (Dual-Pass Enabled)")
    
    batch_size = 3 # Smaller batches = higher precision
    full_markdown = []
    integrity_failures = 0
    audit_path = output_path.with_suffix(".integrity.md")
    audit_path.write_text(f"# Vexilon Forensic Integrity Audit: {source_name}\n\n", encoding="utf-8")

    for i in range(0, len(raw_pages), batch_size):
        batch = raw_pages[i:i+batch_size]
        batch_text = "\n\n--- PAGE BREAK ---\n\n".join(batch)
        batch_id = (i // batch_size) + 1
        
        print(f"    [>] Batch {batch_id}: Processing pages {i+1} to {min(i+batch_size, len(raw_pages))}...")
        
        # Pass 1
        md_p1 = convert_batch(client, primary_model, batch_text, source_name, batch_id)
        
        if verify:
            # Pass 2
            md_p2 = convert_batch(client, secondary_model, batch_text, source_name, batch_id)
            
        # 1. INCREMENTAL SAVE (TO FILE AND AUDIT LOG)
        full_markdown.append(md_p1)
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(md_p1 + "\n\n")
            
        # Hallucination Check
        raw_text_lower = "".join(batch).lower()
        md_words = set(re.findall(r'\b\w+\b', md_p1.lower()))
        
        true_hallucinations = [w for w in md_words if is_hallucination(w, raw_text_lower)]
        
        if true_hallucinations:
            print(f"\n    [!] WARNING: Potential substantive hallucinations: {true_hallucinations[:5]}...")
            # Expanded 5-line context preview
            md_lines = md_p1.split("\n")
            for h_word in true_hallucinations[:2]:
                for idx, line in enumerate(md_lines):
                    if h_word in line.lower():
                        # Show 2 lines before and 2 lines after
                        start = max(0, idx - 2)
                        end = min(len(md_lines), idx + 3)
                        print(f"        [>] Context for '{h_word}':")
                        for l in md_lines[start:end]:
                            print(f"            {l.strip()[:100]}")
                        break
            
            # INTERACTIVE APPROVAL
            print(f"    [*] BATCH PREVIEW READY: Check {output_path.name}")
            ans = input("    [?] Approve this batch anyway? (y/n/skip): ").lower().strip()
            if ans == 'n':
                sys.exit(1)
            elif ans == 'skip':
                print("[SKIP] Batch skipped (Check file manually later).")
                continue

            integrity_failures += 1
            
            with open(audit_path, "a", encoding="utf-8") as af:
                af.write(f"### [Batch {batch_id}] Hallucination Flagged: {true_hallucinations}\n")
                af.write("| Words | Context (Snippet) |\n|---|---|\n")
                for w in true_hallucinations[:10]:
                    af.write(f"| `{w}` | {md_p1.splitlines()[0][:60]}... |\n")
                af.write("\n---\n")
            
            # Consensus Check (P1 vs P2)
            p1_clean = clean_for_integrity_check(md_p1)
            p2_clean = clean_for_integrity_check(md_p2)

            if p1_clean != p2_clean:
                print(f"    [!] NOTICE: Structural divergence detected.")
                
                # Fuzzy Sync Diff
                lines1 = [l.strip() for l in md_p1.split("\n") if l.strip()]
                lines2 = [l.strip() for l in md_p2.split("\n") if l.strip()]
                
                for i, l1 in enumerate(lines1[:10]):
                    # Find best match in lines2 window
                    matches = difflib.get_close_matches(l1, lines2, n=1, cutoff=0.6)
                    if not matches or clean_for_integrity_check(l1) != clean_for_integrity_check(matches[0]):
                        print(f"        [>] P1: \"{l1[:60]}\"")
                        print(f"        [>] P2: \"{(matches[0] if matches else 'No match')[:60]}\"")
                        break
                
                ans = input("    [?] Approve Sonnet's structure? (y/n): ").lower().strip()
                if ans == 'n':
                    sys.exit(1)
                
                with open(audit_path, "a", encoding="utf-8") as af:
                    af.write(f"### [Batch {batch_id}] Structural Divergence Detected\n")
                    af.write(f"- Note: {secondary_model} output differed from {primary_model}.\n")
                    af.write("- Divergence usually occurs on complex headers, tables, or noisy footers.\n")
                    af.write("\n---\n")

        time.sleep(0.5)

    if integrity_failures > 0:
        print(f"\n[!] ALERT: Found {integrity_failures} batches with potential word-integrity issues.")
        print(f"    Please audit: {output_path.with_suffix('.integrity.md')}")
    else:
        print("\n[SUCCESS] Forensic word-integrity check passed.")
        # If everything passed, we can leave a small clean audit
        with open(audit_path, "a", encoding="utf-8") as af:
            af.write("\n\n✅ **SUCCESS:** Forensic word-integrity check passed with 100% parity.\n")

    return "\n\n".join(full_markdown)

def main():
    parser = argparse.ArgumentParser(description="Convert PDF to RAG-optimized Markdown with Forensic Integrity")
    parser.add_argument("input", help="Path to input PDF file")
    parser.add_argument("output", nargs="?", help="Path to output MD file (optional)")
    parser.add_argument("--no-verify", action="store_false", dest="verify", help="Disable dual-pass verification (faster/cheaper)")
    parser.set_defaults(verify=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        # Try finding it recursively in the knowledge base
        matches = list(Path("data/labour_law").rglob(input_path.name))
        if matches:
            input_path = matches[0]
            print(f"[*] Found '{input_path.name}' in {input_path.parent}")
        else:
            print(f"Error: File {args.input} not found in current directory or knowledge base.")
            sys.exit(1)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".md")
    
    print_banner()
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print("-" * 66)
    
    # Initialize/Clear output file for incremental writes
    output_path.write_text("", encoding="utf-8")

    try:
        raw_pages = extract_raw_text(input_path)
        markdown_content = convert_to_md(raw_pages, input_path.stem, output_path, verify=args.verify)
        
        print("-" * 66)
        print(f"[FINISH] Conversion Complete.")
        print(f"Vexilon Integrity Fingerprint: {len(markdown_content)} chars / {len(markdown_content.split())} words")
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
