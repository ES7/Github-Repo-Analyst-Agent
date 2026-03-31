---
title: GitHub Repo Analyst Agent
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
license: mit
---

# GitHub Repo Analyst Agent

An autonomous multi-agent system that analyzes any public GitHub repository and generates a structured technical report.

## What it does

Paste any public GitHub URL → Agent 1 analyzes the repo → Agent 2 critiques the analysis → Download the full report.

## Agents

- **Agent 1 — Analyst**: ReAct loop, calls 4 GitHub API tools autonomously
- **Agent 2 — Critic**: Reviews Agent 1's report, finds weak conclusions
- **Agent 3 — Comparison**: Compares two repos head-to-head (Compare mode)

## Built with

- OpenAI GPT-4o-mini
- PyGithub
- ChromaDB + sentence-transformers (RAG)
- Streamlit
- Built from scratch — no LangChain

## Author

Ebad Sayed — IIT (ISM) Dhanbad | Co-founder, VokeAI