#!/usr/bin/env python3
"""
pdf_to_md.py — Forensic PDF-to-Markdown Converter for Vexilon
------------------------------------------------------------
This script uses Claude (Anthropic API) to convert messy legal PDFs into 
clean, structured Markdown files optimized for RAG retrieval.

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python scripts/pdf_to_md.py path/to/input.pdf [path/to/output.md]
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Optional

# Reuse configuration if possible, otherwise define defaults
LABOUR_LAW_DIR = Path("./data/labour_law")

def print_banner():
    print("=" * 60)
    print(" VEXILON : PDF → MARKDOWN CONVERTER ")
    print("=" * 60)

def extract_raw_text(pdf_path: Path) -> list[str]:
    """Basic extraction using pypdf to get page-by-page raw content."""
    from pypdf import PdfReader
    import re

    print(f"[*] Extracting raw text from {pdf_path.name}...")
    reader = PdfReader(str(pdf_path))
    pages = []
    
    # Simple cleanup to remove obvious junk before sending to LLM
    # (Similar to app.py logic)
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        # Remove bclaws URL noise
        text = re.sub(r"https?://www\.bclaws\.gov\.bc\.ca/\S*", "", text)
        # Remove date/time stamps
        text = re.sub(r"\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2}\s+[^\n]*", "", text)
        pages.append(text.strip())
        
    print(f"[+] Total pages extracted: {len(pages)}")
    return pages

def convert_to_md(raw_pages: list[str], source_name: str) -> str:
    """Use Claude to restructure the raw text into clean Markdown."""
    import anthropic
    
    client = anthropic.Anthropic() # Reads ANTHROPIC_API_KEY
    model = os.getenv("CONVERT_MODEL", "claude-3-5-sonnet-20241022") # High quality for structure
    
    print(f"[*] Converting to MD using {model}...")
    
    # We'll process in batches to keep context clean and handle tokens
    # For forensic accuracy, we process 3-5 pages at a time so Claude sees the transition
    batch_size = 5
    full_markdown = []
    
    system_prompt = f"""You are a specialized legal document formatter. 
Your task is to convert messy raw text extracted from a PDF of the '{source_name}' into perfectly structured GitHub Flavored Markdown.

Rules:
1. Preserve every Article, Section, and Clause number EXACTLY as written.
2. Use proper Markdown headers (#, ##, ###) for Articles and Sections.
3. Clean up broken words (de-hyphenate) caused by line breaks.
4. Convert lists and sub-clauses into proper Markdown bullet or numbered lists.
5. If you see a table, format it as a Markdown table.
6. REMOVE all footers, page numbers, and website URLs.
7. Do NOT summarize. Every sentence of substance must be preserved.
8. Output ONLY the Markdown content. No preamble."""

    for i in range(0, len(raw_pages), batch_size):
        batch = raw_pages[i:i+batch_size]
        batch_text = "\n\n--- PAGE BREAK ---\n\n".join(batch)
        
        print(f"    [>] Processing pages {i+1} to {min(i+batch_size, len(raw_pages))}...")
        
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Here is the raw text for pages {i+1}-{i+batch_size}:\n\n{batch_text}"}
                ]
            )
            full_markdown.append(response.content[0].text)
        except Exception as e:
            print(f"    [!] Error processing batch {i}: {e}")
            # Fallback to raw if LLM fails
            full_markdown.append(batch_text)
            
        # Small delay to avoid rate limits
        time.sleep(0.5)

    return "\n\n".join(full_markdown)

def main():
    parser = argparse.ArgumentParser(description="Convert PDF to RAG-optimized Markdown")
    parser.add_argument("input", help="Path to input PDF file")
    parser.add_argument("output", nargs="?", help="Path to output MD file (optional)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File {input_path} not found.")
        sys.exit(1)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".md")
    
    print_banner()
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print("-" * 60)

    try:
        raw_pages = extract_raw_text(input_path)
        markdown_content = convert_to_md(raw_pages, input_path.stem)
        
        # Save output
        output_path.write_text(markdown_content, encoding="utf-8")
        print("-" * 60)
        print(f"[SUCCESS] Markdown saved to {output_path}")
        print(f"Size: {len(markdown_content)} characters")
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
