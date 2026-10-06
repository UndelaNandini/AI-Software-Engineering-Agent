from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_analyze_endpoint_valid_repo(tmp_path: Path):
    # Create sample python file in temp folder
    sample = tmp_path / "calc.py"
    sample.write_text(
        """
def add(a: int, b: int) -> int:
    '''Add two integers.'''
    return a + b
""",
        encoding="utf-8",
    )

    payload = {"repo_path": str(tmp_path)}
    response = client.post("/api/v1/repos/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["total_files"] == 1
    assert data["total_functions"] == 1
    assert len(data["files"]) == 1

    file_item = data["files"][0]
    assert file_item["relative_path"] == "calc.py"
    symbol = file_item["symbols"][0]
    assert symbol["short_name"] == "add"
    assert symbol["return_type"] == "int"


def test_analyze_endpoint_nonexistent_path():
    payload = {"repo_path": "/path/does/not/exist/ever"}
    response = client.post("/api/v1/repos/analyze", json=payload)
    assert response.status_code == 404
    assert "Target path does not exist" in response.json()["detail"]


def test_analyze_endpoint_file_instead_of_dir(tmp_path: Path):
    sample = tmp_path / "single_file.py"
    sample.write_text("x = 10", encoding="utf-8")

    payload = {"repo_path": str(sample)}
    response = client.post("/api/v1/repos/analyze", json=payload)
    assert response.status_code == 400
    assert "Target path is not a directory" in response.json()["detail"]
