import json
from app.mcp_server import analyze_repository, compute_impact, plan_issue, review_diff

def test_mcp_tool_analyze_repo():
    res_str = analyze_repository(".")
    data = json.loads(res_str)
    assert "total_files" in data
    assert "total_symbols" in data
    assert data["total_files"] > 0

def test_mcp_tool_plan_issue():
    res_str = plan_issue(".", "Add user query parameter", "Support limit query")
    data = json.loads(res_str)
    assert "plan_id" in data
    assert "steps" in data
    assert len(data["steps"]) > 0

def test_mcp_tool_review_diff():
    diff = "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-x = 1\n+x = eval('2')"
    res_str = review_diff(diff)
    data = json.loads(res_str)
    assert data["security_verdict"] == "FAIL"
