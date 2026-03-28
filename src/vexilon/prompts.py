import threading
from pathlib import Path
from src.vexilon import config, manifest

# ─── System Prompts ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Vexilon, a highly authoritative professional assistant for BCGEU union stewards.

--- HOW YOUR SEARCH WORKS ---
Your library contains the COMPLETE, full text of these documents:
{manifest}

IMPORTANT: For each question you receive, a semantic search retrieves the most relevant excerpts from this library. 
Content that does not appear in the excerpts below may still exist in the library. 
NEVER claim text is "missing" or "not in my documents"; instead, suggest user ask specifically about that article.
--------------------------

Rules:
1. ANSWER FROM EXCERPTS ONLY: Base your answer strictly on the provided excerpts.
2. Every claim must be supported by a verbatim quote followed by its citation: — [Document Name], Article/Section [X], p. [N]
3. Plain-language explanation comes BEFORE the verbatim quote.
4. ALWAYS lead with the Collective Agreement as the primary authority. Statutory and Jurisprudence sources provide supplemental legal weight.
5. Tone: Professional, forensic, and confident. Do NOT be apologetic.
6. Citation format: > "[Verbatim quote]" — [Document Name], Article [X], p. [N]
"""

VERIFY_STEWARD_MESSAGE = "Verify w/ Area Office: 604-291-9611"

REVIEWER_SYSTEM_PROMPT = """You are a Senior BCGEU Staff Representative reviewing a junior steward's output.
Critically evaluate: Citations, Nexus, Procedures, and Gaps.
1-10 Scale: 9-10 (Approved), 7-8 (Minor issues), 5-6 (Significant issues), 1-4 (Escalate).
"""

VERIFIER_SYSTEM_PROMPT = """You are a forensic document auditor. 
Your ONLY task is to check if the claims in the RESPONSE are supported by the provided CONTEXT.
- If a claim is supported, say nothing about it.
- If a claim is NOT supported or contradicts the context, FLAG IT.
- If you find a discrepancy, lead with ⚠️.
- Be extremely nitpicky about article numbers and page counts.
"""

def get_persona_prompt(mode_name: str) -> str:
    paths = {
        "Direct": Path("./prompts/direct_staff_rep.txt"),
        "Defend": Path("./prompts/case_builder.txt"),
    }
    path = paths.get(mode_name)
    if path and path.is_file():
        return path.read_text(encoding="utf-8")
    
    fallbacks = {
        "Direct": "You are a BCGEU Staff Rep providing DIRECT OPERATIONAL GUIDANCE.",
        "Defend": "You are a BCGEU Staff Rep specializing in Grievance Drafting.",
    }
    return fallbacks.get(mode_name, SYSTEM_PROMPT)

# ─── Test Registry ────────────────────────────────────────────────────────────
class TestDoctrine:
    def __init__(self, name: str, keywords: set[str], content: str, file_path: Path):
        self.name, self.keywords, self.content, self.file_path = name, keywords, content, file_path

class TestRegistry:
    def __init__(self):
        self.tests: list[TestDoctrine] = []
        self._lock = threading.Lock()

    def load(self, directory: Path) -> None:
        if not directory.exists(): return
        with self._lock:
            self.tests = []
            for f in directory.glob("*.md"):
                try:
                    text = f.read_text(encoding="utf-8")
                    lines = text.split("\n")
                    keywords, content_start = set(), 0
                    for i, line in enumerate(lines):
                        if line.startswith("**Keywords:**"):
                            kw_line = line.replace("**Keywords:**", "").strip()
                            keywords = {k.strip().lower() for k in kw_line.split(",") if k.strip()}
                            content_start = i + 1
                            break
                    self.tests.append(TestDoctrine(
                        name=f.stem.replace("_", " ").title(),
                        keywords=keywords,
                        content="\n".join(lines[content_start:]).strip(),
                        file_path=f
                    ))
                except Exception as e: print(f"[registry] Error {f.name}: {e}")

    def find_matches(self, query: str) -> list[TestDoctrine]:
        q_lower = query.lower()
        with self._lock:
            return [t for t in self.tests if any(k in q_lower for k in t.keywords)]
