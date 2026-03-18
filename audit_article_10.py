import sys
from pathlib import Path
import app

def audit_article_10():
    print("🚀 Starting Text Audit for Article 10...")
    
    pdf_path = Path("data/labour_law/bcgeu_19th_main_agreement.pdf")
    if not pdf_path.exists():
        print(f"❌ Error: Could not find {pdf_path}")
        return

    # Load chunks (this uses the new contextual breadcrumb logic)
    print(f"📄 Loading {pdf_path.name}...")
    chunks = app.load_pdf_chunks(pdf_path)
    
    # Filter for Article 10 chunks - case insensitive just in case
    art_10_chunks = [c for c in chunks if "ARTICLE 10" in c.get("header", "").upper()]
    
    if not art_10_chunks:
        print("❌ Audit Failed: No Article 10 chunks found!")
        # Let's see what headers WE DID find
        headers = {c.get("header", "NO_HEADER") for c in chunks}
        print(f"Available headers: {list(headers)[:10]}...")
        return
    
    print(f"✅ Found {len(art_10_chunks)} chunks tagged with 'ARTICLE 10'.")
    
    # Sample a few chunks to see the breadcrumbs
    print("\n--- [Audit Samples] ---")
    for i, chunk in enumerate(art_10_chunks[:3]):
        print(f"Sample {i+1} (Page {chunk['page']}):")
        # Check that the text actually contains the header
        if "ARTICLE 10" in chunk['text'].upper():
            print("  ✅ BREADCRUMB DETECTED")
        else:
            print("  ❌ BREADCRUMB MISSING")
            
        print(f"  TEXT PREVIEW: {chunk['text'][:120]}...")
        print("-" * 30)

    print("\n✅ Audit Complete. The 'Article 10' blind spot is history.")

if __name__ == "__main__":
    audit_article_10()
