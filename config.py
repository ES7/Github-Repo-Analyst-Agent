import os
from dotenv import load_dotenv
 
load_dotenv()
 
 
def _require(key: str) -> str:
    """Get an env variable or raise a clear error if missing."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"\n\n[Config Error] '{key}' is not set.\n"
            f"→ Copy .env.example to .env and fill in your keys.\n"
        )
    return value
 
 
# ── API Keys ──────────────────────────────────
GITHUB_TOKEN: str = _require("GITHUB_TOKEN")
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")
 
# ── Model Settings ────────────────────────────
GEMINI_MODEL: str = "gemini-2.5-flash-lite"
MAX_AGENT_STEPS: int = 8                  # prevent infinite loops
MAX_FILE_CHARS: int = 3000               # token budget per file read
 
# ── Output ────────────────────────────────────
REPORTS_DIR: str = "reports"