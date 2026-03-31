from github import Github, GithubException
from config import GITHUB_TOKEN, MAX_FILE_CHARS

# Single shared GitHub client — initialized once, used everywhere
_client = Github(GITHUB_TOKEN)


def _get_repo(repo_url: str):
    """Parse a GitHub URL and return a PyGithub repo object."""
    repo_path = repo_url.replace("https://github.com/", "").strip("/")
    return _client.get_repo(repo_path)


# ─────────────────────────────────────────────
# Tool 1: Repo metadata
# ─────────────────────────────────────────────

def fetch_repo_metadata(repo_url: str) -> dict:
    """
    High-level stats: stars, forks, language, activity, topics.
    Always called first — gives the agent the big picture.
    """
    try:
        repo = _get_repo(repo_url)
        return {
            "name": repo.full_name,
            "description": repo.description,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "watchers": repo.watchers_count,
            "language": repo.language,
            "topics": repo.get_topics(),
            "license": repo.license.name if repo.license else "None",
            "open_issues": repo.open_issues_count,
            "default_branch": repo.default_branch,
            "last_commit": str(repo.pushed_at),
            "created_at": str(repo.created_at),
            "size_kb": repo.size,
            "is_fork": repo.fork,
            "is_archived": repo.archived,
        }
    except GithubException as e:
        return {"error": f"GitHub API error {e.status}: {e.data}"}


# ─────────────────────────────────────────────
# Tool 2: File tree
# ─────────────────────────────────────────────

def fetch_file_tree(repo_url: str) -> dict:
    """
    Root-level file/folder structure + auto-detected signals.
    Tells the agent: what kind of project is this and what to read next.
    """
    try:
        repo = _get_repo(repo_url)
        contents = repo.get_contents("")

        tree = [
            {"name": item.name, "type": item.type, "size_bytes": item.size}
            for item in contents[:50]
        ]

        names_lower = [f["name"].lower() for f in tree]
        signals = {
            "has_readme":        any("readme" in n for n in names_lower),
            "has_requirements":  "requirements.txt" in names_lower,
            "has_pyproject":     "pyproject.toml" in names_lower,
            "has_dockerfile":    "dockerfile" in names_lower,
            "has_docker_compose":"docker-compose.yml" in names_lower,
            "has_tests":         any("test" in n for n in names_lower),
            "has_github_ci":     ".github" in names_lower,
            "has_license":       any("license" in n for n in names_lower),
            "has_makefile":      "makefile" in names_lower,
            "has_env_example":   any(".env.example" in n for n in names_lower),
        }

        return {"tree": tree, "signals": signals}
    except GithubException as e:
        return {"error": f"GitHub API error {e.status}: {e.data}"}


# ─────────────────────────────────────────────
# Tool 3: Read a specific file
# ─────────────────────────────────────────────

def fetch_file_content(repo_url: str, file_path: str) -> dict:
    """
    Read any file in the repo (README, requirements.txt, main.py, etc.).
    Truncated to MAX_FILE_CHARS to stay within token budget.
    """
    try:
        repo = _get_repo(repo_url)
        file = repo.get_contents(file_path)
        content = file.decoded_content.decode("utf-8", errors="ignore")

        return {
            "file": file_path,
            "content": content[:MAX_FILE_CHARS],
            "truncated": len(content) > MAX_FILE_CHARS,
            "total_chars": len(content),
        }
    except GithubException as e:
        return {"error": f"Could not read '{file_path}': {e.status}"}


# ─────────────────────────────────────────────
# Tool 4: Recent commits
# ─────────────────────────────────────────────

def fetch_recent_commits(repo_url: str, count: int = 10) -> dict:
    """
    Last N commit messages, dates, and authors.
    Tells the agent: is this actively maintained? what's being worked on?
    """
    try:
        repo = _get_repo(repo_url)
        commits = [
            {
                "message": c.commit.message.split("\n")[0],
                "date": str(c.commit.author.date),
                "author": c.commit.author.name,
            }
            for c in repo.get_commits()[:count]
        ]
        return {"recent_commits": commits}
    except GithubException as e:
        return {"error": f"GitHub API error {e.status}: {e.data}"}