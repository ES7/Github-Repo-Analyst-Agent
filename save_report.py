import os
import re
from datetime import datetime
from config import REPORTS_DIR


def _slug(repo_url: str) -> str:
    """Turn a GitHub URL into a safe filename slug."""
    path = repo_url.replace("https://github.com/", "").strip("/")
    return re.sub(r"[^a-zA-Z0-9_-]", "_", path)


def save_report(repo_url: str, report: str) -> str:
    """
    Save a report to reports/<owner>_<repo>_<timestamp>.md
    Returns the file path it was saved to.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_slug(repo_url)}_{timestamp}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# GitHub Repo Analysis\n")
        f.write(f"**Repo:** {repo_url}  \n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
        f.write("---\n\n")
        f.write(report)

    return filepath