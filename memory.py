import json
import os
from datetime import datetime

MEMORY_FILE = "memory.json"


def _load() -> dict:
    """Load memory from disk. Returns empty dict if file doesn't exist."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(memory: dict):
    """Write memory to disk."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, default=str)


def get_memory(repo_url: str) -> dict | None:
    """
    Get past memory for a repo.
    Returns None if this repo has never been analyzed before.
    """
    memory = _load()
    return memory.get(repo_url.strip("/"), None)


def save_memory(repo_url: str, report: str, metadata: dict = {}):
    """
    Save analysis results to memory after each run.

    Args:
        repo_url: The GitHub repo URL
        report:   The full analyst report text
        metadata: Optional dict with repo stats (stars, forks, last_commit)
    """
    memory = _load()
    key = repo_url.strip("/")

    previous = memory.get(key, {})
    analysis_count = previous.get("analysis_count", 0) + 1

    memory[key] = {
        "last_analyzed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analysis_count": analysis_count,
        "last_report_summary": report[:500],  # first 500 chars as summary
        "last_stars": metadata.get("stars"),
        "last_forks": metadata.get("forks"),
        "last_commit": metadata.get("last_commit"),
    }

    _save(memory)


def build_memory_context(repo_url: str) -> str:
    """
    Build a memory context string to inject into the agent's prompt.
    Returns empty string if no memory exists for this repo.
    """
    past = get_memory(repo_url)

    if not past:
        return ""

    lines = [
        f"MEMORY — This repo was analyzed before:",
        f"- Last analyzed: {past.get('last_analyzed', 'unknown')}",
        f"- Times analyzed: {past.get('analysis_count', 1)}",
        f"- Stars at last analysis: {past.get('last_stars', 'unknown')}",
        f"- Forks at last analysis: {past.get('last_forks', 'unknown')}",
        f"- Last commit at previous analysis: {past.get('last_commit', 'unknown')}",
        f"- Previous report summary: {past.get('last_report_summary', '')}",
        f"",
        f"Compare current findings with above. Note what has changed since last analysis.",
    ]

    return "\n".join(lines)


def format_memory_for_ui(repo_url: str) -> dict | None:
    """
    Returns memory data formatted for display in Streamlit UI.
    Returns None if no memory exists.
    """
    past = get_memory(repo_url)
    if not past:
        return None

    return {
        "last_analyzed": past.get("last_analyzed", "unknown"),
        "analysis_count": past.get("analysis_count", 1),
        "last_stars": past.get("last_stars"),
        "last_forks": past.get("last_forks"),
        "summary": past.get("last_report_summary", ""),
    }