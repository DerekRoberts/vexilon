import html
from pathlib import Path
from src.vexilon import config, loader

def get_knowledge_manifest() -> str:
    """Dynamically scan the labour_law tiers and build a formatted list."""
    files = loader.get_all_source_files()
    if not files:
        return "No documents available."

    lines = []
    for f in files:
        stem, tier = f.stem, f.parent.name
        source_name = loader._get_source_name(stem)
        tier_label = config.AUTHORITY_TIERS.get(tier, tier.title())
        
        parts = stem.split("_", 2)
        if len(parts) == 3:
            idx, _, _ = parts
            lines.append(f"{idx}. {source_name} ({tier_label})")
        elif len(parts) == 2:
            idx, _ = parts
            lines.append(f"{idx}. {source_name} ({tier_label})")
        else:
            lines.append(f"- {source_name} ({tier_label})")

    return "\n".join(lines)

def build_pdf_download_links() -> str:
    """Generate HTML for download links, grouped by hierarchy tier."""
    files = loader.get_all_source_files()
    if not files: return ""

    # Group files by tier
    grouped = {}
    for f in files:
        tier = f.parent.name
        grouped.setdefault(tier, []).append(f)

    html_out = ["<b>Knowledge Base by Authority Tier:</b>"]
    
    # Sort tiers by priority (primary, statutory, resources, jurisprudence)
    tier_order = ["primary", "statutory", "resources", "jurisprudence"]
    for tier in [t for t in tier_order if t in grouped] + [t for t in grouped if t not in tier_order]:
        tier_label = config.AUTHORITY_TIERS.get(tier, tier.title())
        html_out.append(f"<p style='margin-bottom: 4px; font-weight: 600;'>{tier_label}:</p>")
        html_out.append("<ul style='margin-top: 0;'>")
        
        for f in sorted(grouped[tier], key=lambda x: x.name):
            stem = f.stem
            source_name = loader._get_source_name(stem)
            # Relative path within data/labour_law
            rel_path = f.relative_to(config.LABOUR_LAW_DIR.parent)
            display_name = source_name
            parts = stem.split("_", 2)
            if len(parts) >= 2:
                display_name = f"{parts[0]}. {source_name}"
            
            html_out.append(
                f'<li><a href="/gradio_api/file={rel_path}" target="_blank">{html.escape(display_name)}</a></li>'
            )
        html_out.append("</ul>")

    return "\n".join(html_out)
