"""
test_api.py
-----------
Quick test script for the FastAPI backend.
Run the API first:  uvicorn api:app --reload
Then run this:      python test_api.py
"""

import time
import requests

BASE_URL = "http://localhost:8000"
TEST_REPO = "https://github.com/ES7/Github-Repo-Analyst-Agent"


def test_health():
    print("\n--- GET /health ---")
    r = requests.get(f"{BASE_URL}/health")
    print(r.json())


def test_analyze():
    print("\n--- POST /analyze ---")
    r = requests.post(f"{BASE_URL}/analyze", json={
        "repo_url": TEST_REPO,
        "include_critique": True
    })
    data = r.json()
    print(f"Job ID: {data['job_id']}")
    print(f"Status: {data['status']}")

    job_id = data["job_id"]

    # Poll until done
    print("\nPolling for result...")
    while True:
        r = requests.get(f"{BASE_URL}/jobs/{job_id}")
        status = r.json().get("status")
        print(f"  Status: {status}")

        if status == "done":
            result = r.json()["result"]
            print(f"\nReport preview:\n{result['report'][:300]}...")
            print(f"\nSaved to: {result['report_saved_to']}")
            break
        elif status == "failed":
            print(f"Failed: {r.json().get('error')}")
            break

        time.sleep(5)


def test_memory():
    print("\n--- GET /memory ---")
    owner_repo = TEST_REPO.replace("https://github.com/", "")
    owner, repo = owner_repo.split("/")
    r = requests.get(f"{BASE_URL}/memory/{owner}/{repo}")
    print(r.json())


def test_compare():
    print("\n--- POST /compare ---")
    r = requests.post(f"{BASE_URL}/compare", json={
        "repo_url_a": "https://github.com/pallets/flask",
        "repo_url_b": "https://github.com/tiangolo/fastapi",
    })
    data = r.json()
    print(f"Job ID: {data['job_id']}")

    job_id = data["job_id"]

    print("\nPolling for result...")
    while True:
        r = requests.get(f"{BASE_URL}/jobs/{job_id}")
        status = r.json().get("status")
        print(f"  Status: {status}")

        if status == "done":
            result = r.json()["result"]
            print(f"\nComparison preview:\n{result['comparison'][:300]}...")
            break
        elif status == "failed":
            print(f"Failed: {r.json().get('error')}")
            break

        time.sleep(5)


if __name__ == "__main__":
    test_health()
    test_analyze()
    test_memory()
    # test_compare()  # uncomment to test comparison — takes longer