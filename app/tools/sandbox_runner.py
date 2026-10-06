import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from app.models.schemas import TestExecutionResult, TestFailureDetail


class SandboxTestRunner:
    """Executes repository test suites in a controlled subprocess environment with timeout protection."""

    def __init__(self, default_timeout: int = 30):
        self.default_timeout = default_timeout

    def run_pytest(
        self,
        repo_path: Path,
        test_target: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> TestExecutionResult:
        """Run pytest inside the repo directory and parse structured results."""
        target_dir = Path(repo_path).resolve()
        if not target_dir.is_dir():
            raise FileNotFoundError(f"Target repository directory not found: {target_dir}")

        timeout_val = timeout or self.default_timeout

        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "-p", "no:cacheprovider"]
        if test_target:
            cmd.append(test_target)

        start_time = time.time()
        try:
            # Set PYTHONPATH and disable bytecode writing to prevent stale pyc caching
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONPATH"] = str(target_dir) + os.pathsep + env.get("PYTHONPATH", "")

            process = subprocess.run(
                cmd,
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=timeout_val,
                env=env,
            )

            duration = round(time.time() - start_time, 2)
            output = (process.stdout or "") + "\n" + (process.stderr or "")

            return self._parse_pytest_output(output, process.returncode, duration)

        except subprocess.TimeoutExpired as e:
            duration = round(time.time() - start_time, 2)
            timeout_output = (e.stdout or "") + "\n" + (e.stderr or "")
            return TestExecutionResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                failures=[
                    TestFailureDetail(
                        test_name="pytest_execution",
                        error_message=f"Execution timed out after {timeout_val} seconds.",
                        traceback="TimeoutExpired: The test suite took too long to complete.",
                    )
                ],
                raw_output=timeout_output + f"\n[ERROR] Command timed out after {timeout_val}s",
                duration_seconds=duration,
            )
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return TestExecutionResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                failures=[
                    TestFailureDetail(
                        test_name="runner_exception",
                        error_message=str(e),
                        traceback="",
                    )
                ],
                raw_output=f"Failed to launch test runner: {e}",
                duration_seconds=duration,
            )

    def _parse_pytest_output(
        self, output: str, return_code: int, duration: float
    ) -> TestExecutionResult:
        """Extract passed/failed counts, test names, and failure traces from pytest output."""
        passed_count = 0
        failed_count = 0

        # Match summary line: e.g. "== 2 passed in 0.12s ==" or "== 1 failed, 2 passed in 0.45s =="
        passed_match = re.search(r"(\d+)\s+passed", output)
        if passed_match:
            passed_count = int(passed_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed_count = int(failed_match.group(1))

        error_match = re.search(r"(\d+)\s+error", output)
        if error_match:
            failed_count += int(error_match.group(1))

        failures: List[TestFailureDetail] = []

        # Find individual failed tests: e.g. "FAILED test_file.py::test_name - AssertionError: ..."
        # or "FAILED test_file.py::test_name"
        failed_lines = re.findall(r"FAILED\s+([^\s:]+::[^\s\-]+)(?:\s+-\s+(.+))?", output)
        for match in failed_lines:
            test_name = match[0]
            err_msg = match[1] if len(match) > 1 and match[1] else "Test failed assertion or raised error"

            # Try to grab traceback snippet
            tb_snippet = ""
            tb_pattern = rf"_{2,}\s+{re.escape(test_name.split('::')[-1])}\s+_{2,}([\s\S]+?)(?=(?:_{2,}|FAILED|=+|$))"
            tb_match = re.search(tb_pattern, output)
            if tb_match:
                tb_snippet = tb_match.group(1).strip()

            failures.append(
                TestFailureDetail(
                    test_name=test_name,
                    error_message=err_msg,
                    traceback=tb_snippet,
                )
            )

        total_tests = passed_count + failed_count
        passed = (return_code == 0) and (failed_count == 0)

        return TestExecutionResult(
            passed=passed,
            total_tests=total_tests,
            passed_tests=passed_count,
            failed_tests=failed_count,
            failures=failures,
            raw_output=output,
            duration_seconds=duration,
        )


sandbox_runner = SandboxTestRunner()
