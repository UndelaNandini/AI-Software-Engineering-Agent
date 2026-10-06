import ast
from pathlib import Path
from typing import Optional, Tuple


def read_file_range(file_path: Path, start_line: int, end_line: int) -> str:
    """Read a specific line range (1-indexed, inclusive) from a file."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    return "".join(lines[start_idx:end_idx])


def create_file(file_path: Path, content: str) -> None:
    """Create a new file and ensure parent directories exist."""
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _find_symbol_span(tree: ast.AST, symbol_name: str) -> Optional[Tuple[int, int]]:
    """Find start and end line numbers for a function or class symbol in an AST."""
    target_short_name = symbol_name.split(".")[-1]

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == target_short_name:
                start = node.lineno
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                return (start, end)
    return None


def replace_symbol_code(file_path: Path, symbol_name: str, new_code: str) -> bool:
    """Surgically replace a function or class definition in a file using AST line spans.

    Validates that the replacement produces valid Python syntax before saving.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as e:
        raise ValueError(f"Target file currently has invalid Python syntax: {e}")

    span = _find_symbol_span(tree, symbol_name)
    if not span:
        raise ValueError(f"Symbol '{symbol_name}' not found in {path}")

    start_line, end_line = span
    lines = content.splitlines(keepends=True)

    # 1-indexed to 0-indexed: start_line - 1 to end_line
    before_lines = lines[: start_line - 1]
    after_lines = lines[end_line:]

    # Ensure new_code ends with newline
    formatted_new_code = new_code if new_code.endswith("\n") else new_code + "\n"

    new_content = "".join(before_lines) + formatted_new_code + "".join(after_lines)

    # Validate that modified content parses cleanly
    try:
        ast.parse(new_content, filename=str(path))
    except SyntaxError as e:
        raise ValueError(f"Replacement produced invalid Python syntax: {e}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True
