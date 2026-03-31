from github_tools import (
    fetch_repo_metadata,
    fetch_file_tree,
    fetch_file_content,
    fetch_recent_commits,
)

TOOLS: dict[str, dict] = {
    "fetch_repo_metadata": {
        "fn": fetch_repo_metadata,
        "description": "Get repo stats: stars, forks, language, topics, license, activity dates",
        "args": ["repo_url"],
    },
    "fetch_file_tree": {
        "fn": fetch_file_tree,
        "description": "Get the file/folder structure at repo root and detect key signals",
        "args": ["repo_url"],
    },
    "fetch_file_content": {
        "fn": fetch_file_content,
        "description": "Read a specific file's content (e.g. README.md, requirements.txt, main.py)",
        "args": ["repo_url", "file_path"],
    },
    "fetch_recent_commits": {
        "fn": fetch_recent_commits,
        "description": "Get the last 10 commit messages, dates, authors to assess activity",
        "args": ["repo_url"],
    },
}


def get_tool_descriptions() -> str:
    return "\n".join(
        f"- {name}: {meta['description']}"
        for name, meta in TOOLS.items()
    )


def run_tool(tool_name: str, args: dict) -> dict:
    """Execute a tool by name and return its result."""
    if tool_name not in TOOLS:
        return {"error": f"Unknown tool: '{tool_name}'. Available: {list(TOOLS.keys())}"}
    return TOOLS[tool_name]["fn"](**args)