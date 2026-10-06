from pathlib import Path
from fastapi.testclient import TestClient

from app.agents.reviewer import code_reviewer
from app.core.git_manager import GitManager
from app.main import app

client = TestClient(app)

SAFE_DIFF = """
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,3 @@
 def add(a: int, b: int) -> int:
+    '''Add two integers.'''
     return a + b
"""

INSECURE_DIFF = """
--- a/server.py
+++ b/server.py
@@ -5,2 +5,3 @@
 def run_dynamic(cmd):
+    api_key = "sk_live_1234567890abcdef"
+    return eval(cmd)
"""


def test_code_reviewer_safe_diff():
    report = code_reviewer.review_diff(SAFE_DIFF)
    assert report.security_verdict == "PASS"
    assert report.approved is True
    assert len(report.findings) == 0


def test_code_reviewer_insecure_diff():
    report = code_reviewer.review_diff(INSECURE_DIFF)
    assert report.security_verdict == "FAIL"
    assert report.approved is False
    assert len(report.findings) >= 2  # Hardcoded key + eval()
    categories = [f.category for f in report.findings]
    assert "SECURITY" in categories


def test_api_review_diff_endpoint(tmp_path: Path):
    repo_dir = tmp_path / "review_repo"
    repo_dir.mkdir()
    GitManager.get_or_init_repo(repo_dir)

    payload = {
        "repo_path": str(repo_dir),
        "diff_text": INSECURE_DIFF,
    }
    resp = client.post("/api/v1/review/diff", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["security_verdict"] == "FAIL"
    assert data["approved"] is False


def test_api_pr_description_endpoint(tmp_path: Path):
    repo_dir = tmp_path / "pr_repo"
    repo_dir.mkdir()
    GitManager.get_or_init_repo(repo_dir)

    payload = {
        "repo_path": str(repo_dir),
        "issue_title": "Add input sanitization",
        "issue_description": "We need to sanitize user search queries to prevent XSS.",
        "tests_passed": True,
    }
    resp = client.post("/api/v1/review/pr", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "## 🚀 PR: Add input sanitization" in data["markdown_body"]
    assert "✅ Verified & Passing" in data["markdown_body"]


def test_api_publish_pr_no_token():
    payload = {
        "owner": "test-owner",
        "repo": "test-repo",
        "head_branch": "agent/fix-1",
        "base_branch": "main",
        "title": "Fix: Automated Bug Repair",
    }
    resp = client.post("/api/v1/review/publish-pr", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "GitHub token not configured" in data["message"]

