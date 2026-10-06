from pathlib import Path
from fastapi.testclient import TestClient

from app.core.ast_parser import ASTRepositoryAnalyzer
from app.core.code_graph import CodeGraph
from app.main import app

client = TestClient(app)

SAMPLE_APP_CODE = """
# router.py
def get_user_route(user_id: int):
    return fetch_user_data(user_id)

def fetch_user_data(user_id: int):
    return query_database(user_id)

def query_database(user_id: int):
    return {"id": user_id, "name": "Test User"}
"""

SAMPLE_TEST_CODE = """
# test_router.py
def test_get_user_route():
    result = get_user_route(1)
    assert result["id"] == 1
"""


def test_code_graph_and_impact(tmp_path: Path):
    app_file = tmp_path / "router.py"
    app_file.write_text(SAMPLE_APP_CODE, encoding="utf-8")

    test_file = tmp_path / "test_router.py"
    test_file.write_text(SAMPLE_TEST_CODE, encoding="utf-8")

    analyzer = ASTRepositoryAnalyzer(repo_path=str(tmp_path))
    analysis = analyzer.analyze()

    graph = CodeGraph().build_from_analysis(analysis)
    stats = graph.get_graph_stats()
    assert stats["total_nodes"] > 0

    # Impact radius of lowest level function 'query_database'
    impact = graph.get_impact_radius("query_database", max_depth=4)
    assert impact["found"] is True
    impacted_symbol_names = [item["symbol"] for item in impact["impacted_symbols"]]

    # Both fetch_user_data and get_user_route should be flagged as impacted upstream!
    assert any("fetch_user_data" in s for s in impacted_symbol_names)
    assert any("get_user_route" in s for s in impacted_symbol_names)


def test_api_impact_endpoint(tmp_path: Path):
    app_file = tmp_path / "service.py"
    app_file.write_text(
        """
def core_calc():
    return 100

def caller_api():
    return core_calc()
""",
        encoding="utf-8",
    )

    payload = {"repo_path": str(tmp_path), "symbol_name": "core_calc"}
    response = client.post("/api/v1/repos/impact", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["total_impacted_symbols"] >= 1


def test_api_symbol_search(tmp_path: Path):
    app_file = tmp_path / "models.py"
    app_file.write_text(
        """
class AccountModel:
    pass

def verify_account():
    pass
""",
        encoding="utf-8",
    )

    payload = {"repo_path": str(tmp_path), "query": "account"}
    response = client.post("/api/v1/repos/symbols/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_matches"] == 2
