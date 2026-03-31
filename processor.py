import re
from pathlib import Path

src_path = Path("/tmp/raw_wca.html")
dest_dir = Path("/home/derek/Repos/vexilon/data/labour_law/02_statutory")

def clean_content(text: str) -> str:
    """Strip HTML and bclaws noise."""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove repeated bclaws boilerplate
    text = re.sub(r'https?://www\.bclaws\.gov\.bc\.ca/\S+', '', text)
    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def process_wca():
    if not src_path.exists():
        print(f"Error: {src_path} not found.")
        return

    content = src_path.read_text(encoding="utf-8")
    
    # Split by anything that looks like "PART 1" or "Part 1" at a boundary
    # This also handles bclaws internal naming conventions
    parts = re.split(r'(?i)(?:\n|>|\s)(Part\s+\d+\s+[^<]{2,})', content)
    
    # Re-assemble partitions
    for i in range(1, len(parts), 2):
        if i + 1 >= len(parts): break
        
        raw_header = parts[i].strip()
        raw_body = parts[i+1]
        
        # Clean both
        header = clean_content(raw_header)
        body = clean_content(raw_body)
        
        # Pull Part Number
        num_m = re.search(r'Part\s+(\d+)', header, re.I)
        if num_m:
            p_num = num_m.group(1)
            filename = f"BC Workers Compensation Act - Part {p_num}.md"
            target = dest_dir / filename
            
            print(f"Writing {filename}...")
            # Prepend a proper header for FAISS
            target.write_text(f"# {header}\n\n{body}", encoding="utf-8")

if __name__ == "__main__":
    process_wca()
    print("Done! Check your folder and run: python3 -c 'from app import startup; startup(force_rebuild=True)'")
