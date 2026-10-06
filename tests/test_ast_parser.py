import tempfile
from pathlib import Path
import pytest

from app.core.ast_parser import ASTRepositoryAnalyzer
from app.models.schemas import SymbolType


SAMPLE_CODE = '''"""Sample module docstring."""
import os
from typing import List, Optional

@decorator_a
class UserService:
    """Service handling user accounts."""

    def __init__(self, db_url: str = "sqlite:///:memory:"):
        self.db_url = db_url

    def get_user(self, user_id: int) -> Optional[dict]:
        """Fetch user by id."""
        record = self._query_db(user_id)
        return record

    def _query_db(self, uid: int) -> dict:
        return {"id": uid, "name": "Alice"}


async def calculate_metrics(items: List[int], multiplier: float = 1.5) -> float:
    """Calculate aggregate metric score."""
    total = sum(items)
    return total * multiplier
'''


def test_ast_parser_single_file(tmp_path: Path):
    test_file = tmp_path / "sample.py"
    test_file.write_text(SAMPLE_CODE, encoding="utf-8")

    analyzer = ASTRepositoryAnalyzer(repo_path=str(tmp_path))
    result = analyzer.analyze()

    assert result.total_files == 1
    assert result.total_classes == 1
    # UserService.__init__, UserService.get_user, UserService._query_db, calculate_metrics = 4 functions/methods
    assert result.total_functions == 4
    assert result.total_symbols == 5

    file_info = result.files[0]
    assert file_info.relative_path == "sample.py"
    assert len(file_info.imports) == 2

    # Check class symbol
    class_sym = next(s for s in file_info.symbols if s.symbol_type == SymbolType.CLASS)
    assert class_sym.short_name == "UserService"
    assert "Service handling user accounts." in (class_sym.docstring or "")
    assert class_sym.decorators == ["decorator_a"]

    # Check method symbol
    get_user_sym = next(s for s in file_info.symbols if s.short_name == "get_user")
    assert get_user_sym.symbol_type == SymbolType.METHOD
    assert get_user_sym.parent_symbol == "UserService"
    assert get_user_sym.return_type == "Optional[dict]"
    assert any(param.name == "user_id" for param in get_user_sym.parameters)

    # Check calls inside get_user
    assert "self._query_db" in get_user_sym.calls

    # Check async function
    metrics_sym = next(s for s in file_info.symbols if s.short_name == "calculate_metrics")
    assert metrics_sym.symbol_type == SymbolType.FUNCTION
    assert metrics_sym.return_type == "float"
    assert "sum" in metrics_sym.calls


def test_ast_parser_call_graph(tmp_path: Path):
    test_file = tmp_path / "caller_callee.py"
    test_file.write_text(
        """
def helper():
    return 42

def main_flow():
    a = helper()
    b = helper()
    return a + b
""",
        encoding="utf-8",
    )

    analyzer = ASTRepositoryAnalyzer(repo_path=str(tmp_path))
    result = analyzer.analyze()

    # Verify call relationships
    callers = [rel for rel in result.call_graph if rel.callee == "helper"]
    assert len(callers) == 2
    assert all("main_flow" in c.caller for c in callers)


def test_ast_parser_ignores_directories(tmp_path: Path):
    # Create valid python file
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    # Create ignored folder
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "hidden.py").write_text("y = 2\n", encoding="utf-8")

    analyzer = ASTRepositoryAnalyzer(repo_path=str(tmp_path))
    result = analyzer.analyze()

    assert result.total_files == 1
    assert result.files[0].relative_path == "app.py"
