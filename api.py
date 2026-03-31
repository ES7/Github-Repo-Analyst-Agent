import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
import uuid
from datetime import datetime

from core import run_agent
from critic_agent import run_critic
from compare_agent import run_compare
from save_report import save_report, save_comparison_report
from memory import format_memory_for_ui, save_memory

# ─────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="GitHub Repo Analyst Agent API",
    description="Multi-agent GitHub repository analyzer.",
    version="1.0.0",
)

# Allow all origins for local dev — tighten this in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store — tracks background jobs
# { job_id: { "status": "running"|"done"|"failed", "result": {...} } }
jobs: dict = {}


# ─────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    repo_url: str
    include_critique: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/tiangolo/fastapi",
                "include_critique": True
            }
        }


class CompareRequest(BaseModel):
    repo_url_a: str
    repo_url_b: str

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url_a": "https://github.com/pallets/flask",
                "repo_url_b": "https://github.com/tiangolo/fastapi"
            }
        }


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class AnalyzeResponse(BaseModel):
    success: bool
    repo_url: str
    report: str
    critique: Optional[str] = None
    steps_count: int
    report_saved_to: str
    generated_at: str


class CompareResponse(BaseModel):
    success: bool
    repo_url_a: str
    repo_url_b: str
    comparison: str
    report_a: str
    report_b: str
    report_saved_to: str
    generated_at: str


# ─────────────────────────────────────────────
# Background job runners
# ─────────────────────────────────────────────

def _run_analyze_job(job_id: str, repo_url: str, include_critique: bool):
    """Runs in background. Updates jobs dict when done."""
    try:
        jobs[job_id]["status"] = "running"

        # Run analyst agent
        result = run_agent(repo_url)
        if not result["success"]:
            jobs[job_id] = {
                "status": "failed",
                "error": result.get("error", "Agent failed")
            }
            return

        report = result["report"]
        critique = ""

        # Run critic if requested
        if include_critique:
            critic_result = run_critic(report, repo_url)
            if critic_result["success"]:
                critique = critic_result["critique"]

        # Save memory
        save_memory(repo_url, report)

        # Save report to disk
        saved_path = save_report(repo_url, report, critique)

        jobs[job_id] = {
            "status": "done",
            "result": {
                "success": True,
                "repo_url": repo_url,
                "report": report,
                "critique": critique,
                "steps_count": len(result["steps"]),
                "report_saved_to": saved_path,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        }

    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}


def _run_compare_job(job_id: str, repo_url_a: str, repo_url_b: str):
    """Runs comparison in background."""
    try:
        jobs[job_id]["status"] = "running"

        result_a = run_agent(repo_url_a)
        result_b = run_agent(repo_url_b)

        if not result_a["success"]:
            jobs[job_id] = {"status": "failed", "error": f"Repo A failed: {result_a.get('error')}"}
            return
        if not result_b["success"]:
            jobs[job_id] = {"status": "failed", "error": f"Repo B failed: {result_b.get('error')}"}
            return

        report_a = result_a["report"]
        report_b = result_b["report"]

        compare_result = run_compare(report_a, repo_url_a, report_b, repo_url_b)

        save_memory(repo_url_a, report_a)
        save_memory(repo_url_b, report_b)

        saved_path = save_comparison_report(
            repo_url_a, report_a,
            repo_url_b, report_b,
            compare_result.get("comparison", "")
        )

        jobs[job_id] = {
            "status": "done",
            "result": {
                "success": True,
                "repo_url_a": repo_url_a,
                "repo_url_b": repo_url_b,
                "comparison": compare_result.get("comparison", ""),
                "report_a": report_a,
                "report_b": report_b,
                "report_saved_to": saved_path,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        }

    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Check if the API is running."""
    return {
        "status": "ok",
        "message": "GitHub Repo Analyst Agent API is running",
        "version": "1.0.0"
    }


@app.post("/analyze", response_model=JobResponse)
def analyze_repo(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Start an async analysis job for a single GitHub repo.
    Returns a job_id — poll /jobs/{job_id} for results.
    """
    repo_url = request.repo_url
    if not repo_url.startswith("https://"):
        repo_url = f"https://github.com/{repo_url}"

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued"}

    background_tasks.add_task(
        _run_analyze_job, job_id, repo_url, request.include_critique
    )

    return JobResponse(
        job_id=job_id,
        status="queued",
        message=f"Analysis started. Poll /jobs/{job_id} for results."
    )


@app.post("/compare", response_model=JobResponse)
def compare_repos(request: CompareRequest, background_tasks: BackgroundTasks):
    """
    Start an async comparison job for two GitHub repos.
    Returns a job_id — poll /jobs/{job_id} for results.
    """
    repo_url_a = request.repo_url_a
    repo_url_b = request.repo_url_b

    if not repo_url_a.startswith("https://"):
        repo_url_a = f"https://github.com/{repo_url_a}"
    if not repo_url_b.startswith("https://"):
        repo_url_b = f"https://github.com/{repo_url_b}"

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued"}

    background_tasks.add_task(
        _run_compare_job, job_id, repo_url_a, repo_url_b
    )

    return JobResponse(
        job_id=job_id,
        status="queued",
        message=f"Comparison started. Poll /jobs/{job_id} for results."
    )


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """
    Poll this endpoint to check job status and get results.
    Status: queued → running → done | failed
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    job = jobs[job_id]

    if job["status"] == "done":
        return {"status": "done", "result": job["result"]}
    elif job["status"] == "failed":
        return {"status": "failed", "error": job.get("error", "Unknown error")}
    else:
        return {"status": job["status"]}


@app.get("/memory/{owner}/{repo}")
def get_memory(owner: str, repo: str):
    """
    Get past analysis memory for a repo.
    Example: GET /memory/tiangolo/fastapi
    """
    repo_url = f"https://github.com/{owner}/{repo}"
    past = format_memory_for_ui(repo_url)

    if not past:
        raise HTTPException(
            status_code=404,
            detail=f"No memory found for {repo_url}. Analyze it first."
        )

    return {
        "repo_url": repo_url,
        "memory": past
    }


@app.get("/jobs")
def list_jobs():
    """List all jobs and their current status."""
    return {
        job_id: {"status": data.get("status")}
        for job_id, data in jobs.items()
    }