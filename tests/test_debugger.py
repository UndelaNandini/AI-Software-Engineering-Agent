from pathlib import Path
from app.agents.debugger import debugger_agent
from app.core.git_manager import GitManager
from app.models.schemas import RepairRequest


def test_debugger_self_repair_success(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    GitManager.get_or_init_repo(repo_dir)

    # 1. Broken implementation
    service_file = repo_dir / "calculator.py"
    service_file.write_text(
        """def calculate_total(a: int, b: int) -> int:
    return a - b
""",
        encoding="utf-8",
    )

    # 2. Test expecting a + b
    test_file = repo_dir / "test_calculator.py"
    test_file.write_text(
        """from calculator import calculate_total

def test_calculate_total():
    assert calculate_total(2, 3) == 5
""",
        encoding="utf-8",
    )

    # 3. Trigger repair loop with correct code fix
    req = RepairRequest(
        repo_path=str(repo_dir),
        issue_description="calculate_total should add numbers, not subtract them.",
        target_file="calculator.py",
        target_symbol="calculate_total",
        repaired_code="""def calculate_total(a: int, b: int) -> int:
    return a + b
""",
        max_attempts=3,
    )

    result = debugger_agent.repair(req)
    assert result.status == "RESOLVED"
    assert result.total_attempts == 1
    assert result.initial_failures == 1
    assert result.final_test_result.passed is True
    assert len(result.attempts_log) == 1


def test_debugger_circuit_breaker_on_repeated_failure(tmp_path: Path):
    repo_dir = tmp_path / "repo_failing"
    repo_dir.mkdir()
    GitManager.get_or_init_repo(repo_dir)

    service_file = repo_dir / "flaky.py"
    service_file.write_text(
        """def flaky_func():
    return 100
""",
        encoding="utf-8",
    )

    test_file = repo_dir / "test_flaky.py"
    test_file.write_text(
        """from flaky import flaky_func

def test_flaky():
    assert flaky_func() == 99999
""",
        encoding="utf-8",
    )

    # Trigger repair with wrong code
    req = RepairRequest(
        repo_path=str(repo_dir),
        issue_description="Fix the calculation",
        target_file="flaky.py",
        target_symbol="flaky_func",
        repaired_code="""def flaky_func():
    return 200
""",
        max_attempts=2,
    )

    result = debugger_agent.repair(req)
    # Circuit breaker triggered because test still failed after 2 attempts
    assert result.status == "MAX_ATTEMPTS_EXCEEDED"
    assert result.total_attempts == 2
    assert result.final_test_result.passed is False
