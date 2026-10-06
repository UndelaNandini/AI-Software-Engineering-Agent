from pathlib import Path
from fastapi.testclient import TestClient

from app.core.git_manager import GitManager
from app.main import app

client = TestClient(app)


def test_api_verify_endpoint(tmp_path: Path):
    test_file = tmp_path / "test_api_sample.py"
    test_file.write_text("def test_ok(): assert 5 * 5 == 25\n", encoding="utf-8")

    payload = {"repo_path": str(tmp_path)}
    resp = client.post("/api/v1/tasks/verify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["passed_tests"] == 1


def test_api_repair_endpoint(tmp_path: Path):
    repo_dir = tmp_path / "repair_repo"
    repo_dir.mkdir()
    GitManager.get_or_init_repo(repo_dir)

    code_file = repo_dir / "mod.py"
    code_file.write_text("def run(): return 'bad'\n", encoding="utf-8")

    test_file = repo_dir / "test_mod.py"
    test_file.write_text("from mod import run\ndef test_run(): assert run() == 'good'\n", encoding="utf-8")

    payload = {
        "repo_path": str(repo_dir),
        "issue_description": "Fix run() return value",
        "target_file": "mod.py",
        "target_symbol": "run",
        "repaired_code": "def run():\n    return 'good'\n",
        "max_attempts": 3,
    }
    resp = client.post("/api/v1/tasks/repair", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RESOLVED"
    assert data["final_test_result"]["passed"] is True
