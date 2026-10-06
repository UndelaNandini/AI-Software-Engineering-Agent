from pathlib import Path
from fastapi.testclient import TestClient

from app.agents.planner import issue_planner
from app.main import app
from app.models.schemas import IssuePlanRequest, PlanStatus, PlanUpdateRequest

client = TestClient(app)

SAMPLE_PROJECT_CODE = """
# user_service.py
class UserService:
    def get_all_users(self):
        '''Retrieve all user records from database.'''
        return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
"""

SAMPLE_TEST_CODE = """
# test_user_service.py
def test_get_all_users():
    service = UserService()
    assert len(service.get_all_users()) == 2
"""


def test_planner_generate_plan(tmp_path: Path):
    service_file = tmp_path / "user_service.py"
    service_file.write_text(SAMPLE_PROJECT_CODE, encoding="utf-8")

    test_file = tmp_path / "test_user_service.py"
    test_file.write_text(SAMPLE_TEST_CODE, encoding="utf-8")

    req = IssuePlanRequest(
        repo_path=str(tmp_path),
        issue_title="Add pagination to get_all_users",
        issue_description="Allow page and page_size query limits on get_all_users method.",
    )

    plan = issue_planner.generate_plan(req)
    assert plan.plan_id is not None
    assert plan.status == PlanStatus.PENDING_APPROVAL
    assert any("user_service.py" in f for f in plan.affected_files)
    assert any("get_all_users" in s for s in plan.target_symbols)
    assert len(plan.steps) >= 3


def test_api_issues_plan_workflow(tmp_path: Path):
    service_file = tmp_path / "user_service.py"
    service_file.write_text(SAMPLE_PROJECT_CODE, encoding="utf-8")

    payload = {
        "repo_path": str(tmp_path),
        "issue_title=" : "Add pagination support",
        "issue_title": "Add pagination support",
        "issue_description": "We need pagination limits on user records.",
    }

    # 1. Create plan
    resp = client.post("/api/v1/issues/plan", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    plan_id = data["plan_id"]
    assert data["status"] == "PENDING_APPROVAL"

    # 2. Get plan by ID
    get_resp = client.get(f"/api/v1/issues/plans/{plan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["plan_id"] == plan_id

    # 3. Approve plan (Human-in-the-loop gate)
    patch_payload = {"status": "APPROVED"}
    patch_resp = client.patch(f"/api/v1/issues/plans/{plan_id}", json=patch_payload)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "APPROVED"

    # 4. List plans
    list_resp = client.get("/api/v1/issues/plans")
    assert list_resp.status_code == 200
    plans = list_resp.json()
    assert any(p["plan_id"] == plan_id for p in plans)
