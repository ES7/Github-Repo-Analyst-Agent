from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY)

CRITIC_PROMPT = """You are a senior software engineer and harsh but fair code reviewer.

You will be given an AI-generated analysis report of a GitHub repository.
Your job is to critically review this report and identify:

1. Weak or vague conclusions — where the analyst said something generic without real evidence
2. Missing angles — important things the analyst completely ignored
3. Overstated claims — where the analyst was too positive or too negative without justification
4. Concrete suggestions — specific things a developer should actually go check manually

RULES:
- Be direct and specific, not generic
- Reference actual things from the report when you critique
- If something in the report is genuinely good analysis, say so briefly
- Keep each section to 2-4 bullet points maximum
- Do NOT rewrite the report — only critique it

FORMAT your response exactly like this:

## What the analyst got right
- ...

## Weak or vague conclusions
- ...

## What was ignored
- ...

## Overstated or understated
- ...

## What you should manually verify
- ...

## Overall verdict
One sentence: is this report trustworthy, partially trustworthy, or superficial?
"""


def run_critic(analyst_report: str, repo_url: str) -> dict:
    try:
        prompt = (
            f"{CRITIC_PROMPT}\n\n"
            f"Repo: {repo_url}\n\n"
            f"Analyst report to critique:\n\n{analyst_report}"
        )

        response = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "success": True,
            "critique": response.choices[0].message.content
        }

    except Exception as e:
        return {
            "success": False,
            "critique": "",
            "error": str(e)
        }