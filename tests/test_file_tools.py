from pathlib import Path
import pytest

from app.tools.file_tools import (
    create_file,
    read_file_range,
    replace_symbol_code,
)

ORIGINAL_MODULE = """import os

def calculate_discount(price: float) -> float:
    return price * 0.1

def calculate_tax(price: float) -> float:
    return price * 0.05
"""


def test_create_and_read_range(tmp_path: Path):
    target_file = tmp_path / "sub" / "module.py"
    create_file(target_file, ORIGINAL_MODULE)

    assert target_file.is_file()
    # Read lines 3 to 4 (calculate_discount)
    content = read_file_range(target_file, 3, 4)
    assert "def calculate_discount" in content
    assert "calculate_tax" not in content


def test_replace_symbol_code_success(tmp_path: Path):
    target_file = tmp_path / "pricing.py"
    create_file(target_file, ORIGINAL_MODULE)

    NEW_TAX_FUNC = """def calculate_tax(price: float) -> float:
    # Updated tax computation
    base_tax = price * 0.08
    return base_tax
"""

    success = replace_symbol_code(target_file, "calculate_tax", NEW_TAX_FUNC)
    assert success is True

    updated_text = target_file.read_text(encoding="utf-8")
    assert "import os" in updated_text
    assert "def calculate_discount" in updated_text
    assert "base_tax = price * 0.08" in updated_text


def test_replace_symbol_code_syntax_error_rollback(tmp_path: Path):
    target_file = tmp_path / "pricing.py"
    create_file(target_file, ORIGINAL_MODULE)

    BROKEN_CODE = "def calculate_tax(price: float) -> float:\n    this is invalid python syntax %%%"

    with pytest.raises(ValueError) as excinfo:
        replace_symbol_code(target_file, "calculate_tax", BROKEN_CODE)

    assert "invalid Python syntax" in str(excinfo.value)
    # Ensure original content is preserved and uncorrupted!
    assert target_file.read_text(encoding="utf-8") == ORIGINAL_MODULE
