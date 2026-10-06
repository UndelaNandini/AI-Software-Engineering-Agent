from pathlib import Path
from fastapi.testclient import TestClient

from app.core.ast_parser import ASTRepositoryAnalyzer
from app.core.indexer import CodebaseIndexer
from app.main import app

client = TestClient(app)

SAMPLE_AUTH_CODE = """
def authenticate_user(token: str) -> bool:
    '''Validate JWT bearer token and verify user identity credentials.'''
    if not token:
        return False
    return True

def calculate_shipping_cost(weight_kg: float, distance_km: float) -> float:
    '''Calculate freight shipping charges and delivery fees based on package weight.'''
    rate = 2.5
    return weight_kg * distance_km * rate
"""


def test_codebase_indexer_chunking_and_search(tmp_path: Path):
    app_file = tmp_path / "services.py"
    app_file.write_text(SAMPLE_AUTH_CODE, encoding="utf-8")

    analyzer = ASTRepositoryAnalyzer(repo_path=str(tmp_path))
    analysis = analyzer.analyze()

    indexer = CodebaseIndexer(repo_path=str(tmp_path))
    chunks = indexer.chunk_repository(analysis)

    # Should have 2 symbol chunks
    assert len(chunks) == 2

    # Query 1: JWT authentication
    auth_results = indexer.search(query="JWT user identity authentication token", top_k=2)
    assert len(auth_results) > 0
    top_auth = auth_results[0]
    assert "authenticate_user" in (top_auth.symbol_name or "")
    assert top_auth.score > 0.0

    # Query 2: Freight shipping
    shipping_results = indexer.search(query="freight delivery package shipping fee", top_k=2)
    assert len(shipping_results) > 0
    top_shipping = shipping_results[0]
    assert "calculate_shipping_cost" in (top_shipping.symbol_name or "")
    assert top_shipping.score > 0.0


def test_api_semantic_search_endpoint(tmp_path: Path):
    app_file = tmp_path / "payment.py"
    app_file.write_text(
        """
def process_stripe_refund(transaction_id: str, amount: float):
    '''Issue customer refund through Stripe payment gateway API.'''
    return {"status": "refunded", "tx": transaction_id}
""",
        encoding="utf-8",
    )

    payload = {
        "repo_path": str(tmp_path),
        "query": "Stripe payment refund to customer",
        "top_k": 3,
    }
    response = client.post("/api/v1/repos/search/semantic", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["total_results"] >= 1
    top_result = data["results"][0]
    assert "process_stripe_refund" in top_result["symbol_name"]
    assert top_result["score"] > 0.0
