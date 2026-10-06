from pathlib import Path
from app.tools.sandbox_runner import sandbox_runner

PASSING_TEST_MODULE = """
def test_addition():
    assert 1 + 1 == 2

def test_string():
    assert "hello".upper() == "HELLO"
"""

FAILING_TEST_MODULE = """
def test_broken_math():
    assert 1 + 1 == 999
"""


def test_sandbox_runner_passing(tmp_path: Path):
    test_file = tmp_path / "test_ok.py"
    test_file.write_text(PASSING_TEST_MODULE, encoding="utf-8")

    result = sandbox_runner.run_pytest(tmp_path)
    assert result.passed is True
    assert result.passed_tests == 2
    assert result.failed_tests == 0
    assert len(result.failures) == 0


def test_sandbox_runner_failing(tmp_path: Path):
    test_file = tmp_path / "test_fail.py"
    test_file.write_text(FAILING_TEST_MODULE, encoding="utf-8")

    result = sandbox_runner.run_pytest(tmp_path)
    assert result.passed is False
    assert result.failed_tests == 1
    assert len(result.failures) == 1
    failure = result.failures[0]
    assert "test_broken_math" in failure.test_name
    assert "assert (1 + 1) == 999" in failure.error_message or "assert" in failure.error_message
    assert "FAILED" in result.raw_output

