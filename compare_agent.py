from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY)

COMPARE_PROMPT = """You are an expert software architect comparing two GitHub repositories.

You will be given two analyst reports for two different repositories.
Your job is to compare them across every dimension and give a final recommendation.

Be direct, specific, and opinionated. Don't sit on the fence.

FORMAT your response exactly like this:

## Quick summary
One sentence describing each repo so the reader knows what they are.

## Head-to-head comparison

| Category | {repo_a_name} | {repo_b_name} | Winner |
|---|---|---|---|
| Code quality | ... | ... | Repo A / Repo B / Tie |
| Tech stack | ... | ... | Repo A / Repo B / Tie |
| Documentation | ... | ... | Repo A / Repo B / Tie |
| Community & activity | ... | ... | Repo A / Repo B / Tie |
| Maintainability | ... | ... | Repo A / Repo B / Tie |
| Beginner friendliness | ... | ... | Repo A / Repo B / Tie |

## Where {repo_a_name} wins
- ...

## Where {repo_b_name} wins
- ...

## Red flags in each
- {repo_a_name}: ...
- {repo_b_name}: ...

## Final recommendation
Which repo should someone use and why. Be specific about WHO should pick which one.
"""


def run_compare(
    report_a: str,
    repo_url_a: str,
    report_b: str,
    repo_url_b: str,
) -> dict:
    try:
        repo_a_name = repo_url_a.replace("https://github.com/", "").strip("/")
        repo_b_name = repo_url_b.replace("https://github.com/", "").strip("/")

        prompt = (
            COMPARE_PROMPT
            .replace("{repo_a_name}", repo_a_name)
            .replace("{repo_b_name}", repo_b_name)
            + f"\n\n---\n\nRepo A ({repo_a_name}) analyst report:\n\n{report_a}"
            + f"\n\n---\n\nRepo B ({repo_b_name}) analyst report:\n\n{report_b}"
        )

        response = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "success": True,
            "comparison": response.choices[0].message.content,
            "repo_a_name": repo_a_name,
            "repo_b_name": repo_b_name,
        }

    except Exception as e:
        return {
            "success": False,
            "comparison": "",
            "error": str(e)
        }