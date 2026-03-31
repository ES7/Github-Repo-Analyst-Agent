# GitHub Repo Analyst Agent

An autonomous AI agent that analyzes any public GitHub repository and generates a structured technical report — architecture, tech stack, health signals, red flags, and improvement suggestions.

Built using a **ReAct agent loop from scratch** — no LangChain, no LangGraph, no frameworks. Just Python, Gemini Flash, and PyGithub.

---

## Demo

Paste any public GitHub URL → watch the agent think step by step → get a full markdown report you can download.

![demo](demo.png)

---

## How it works

This is not a pipeline. A pipeline calls tools in a fixed order. This agent uses the **ReAct pattern** (Reason → Act → Observe) — at each step, the LLM decides which tool to call next based on everything it has observed so far.

```
User inputs repo URL
        ↓
  [ Reason ] — LLM decides what to do next
        ↓
  [ Act ]    — calls one of 4 tools
        ↓
  [ Observe ] — result fed back to LLM
        ↓
  repeat until LLM says DONE
        ↓
  Structured report generated
```

The agent has 4 tools it can call:
- `fetch_repo_metadata` — stars, forks, language, topics, license, last activity
- `fetch_file_tree` — root folder structure, detects README / Dockerfile / tests / CI
- `fetch_file_content` — reads any specific file (README, requirements.txt, main.py)
- `fetch_recent_commits` — last 10 commit messages, dates, authors

---

## Project structure

```
github-repo-analyst-agent/
├── app.py              # Streamlit frontend
├── core.py             # ReAct agent loop (the brain)
├── prompts.py          # All LLM prompts in one place
├── tools_registry.py   # Maps tool names → functions
├── github_tools.py     # 4 GitHub API tool functions
├── save_report.py      # Saves reports as .md files
├── config.py           # Reads API keys from .env
├── .env.example        # Copy this to .env and fill keys
├── .gitignore
└── requirements.txt
```

---

## Tech stack

| Layer | Tool |
|---|---|
| LLM | Gemini 1.5 Flash (free tier) |
| GitHub API | PyGithub |
| Frontend | Streamlit |
| Agent pattern | ReAct (built from scratch) |
| Config | python-dotenv |

**Cost: $0** — runs entirely on free tier APIs.

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/ebadsayed/github-repo-analyst-agent
cd github-repo-analyst-agent
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set up API keys**
```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `GITHUB_TOKEN` → [github.com/settings/tokens](https://github.com/settings/tokens) — New token (classic), no scopes needed for public repos
- `GEMINI_API_KEY` → [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — free tier, no billing needed

**4. Run**
```bash
streamlit run app.py
```

---

## Sample report output

For any repo the agent generates:

- **TL;DR** — plain English summary
- **Architecture overview** — what the file structure reveals
- **Tech stack** — languages, frameworks, key dependencies
- **Health signals** — activity, CI/CD, community, maintenance
- **Red flags** — honest critique and gaps
- **Who should use this** — ideal user and use cases

Reports are saved locally to `reports/` as `.md` files and can be downloaded directly from the UI.

---

## What I learned building this

- The difference between a pipeline and a true agent (the LLM decides, not the code)
- How the ReAct loop works under the hood — what every framework hides from you
- How to structure a Python AI project professionally with `.env`, separated concerns, and clean imports
- That agentic AI is less scary than it sounds — the core loop is ~50 lines of Python

---

## What's next

- [ ] Streaming output (token by token like ChatGPT)
- [ ] Memory — track repos analyzed over time, show what changed
- [ ] Critic agent — second agent that reviews and challenges the first report
- [ ] Compare two repos side by side

---

## Author

**Ebad Sayed** — Final year, IIT (ISM) Dhanbad  
Co-founder, [VokeAI](https://github.com/ebadsayed) — AI startup, government grant recipient

Connect: [LinkedIn](https://linkedin.com/in/ebadsayed) · [GitHub](https://github.com/ebadsayed)

---

*Built with Gemini Flash + PyGithub · Runs on free tier · No frameworks*
