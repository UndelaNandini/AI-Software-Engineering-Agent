import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from app.models.schemas import TestExecutionResult, TestFailureDetail

logger = logging.getLogger(__name__)


class SandboxTestRunner:
    """Executes repository test suites with hardened Docker isolation or subprocess fallback."""

    def __init__(self, default_timeout: int = 30, use_docker_if_available: bool = True):
        self.default_timeout = default_timeout
        self.use_docker_if_available = use_docker_if_available

    def is_docker_available(self) -> bool:
        """Check if Docker daemon is active and responsive."""
        if not self.use_docker_if_available:
            return False
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    def run_pytest(
        self,
        repo_path: Path,
        test_target: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> TestExecutionResult:
        """Executes test suite inside a hardened Docker container, falling back to secure subprocess."""
        target_dir = Path(repo_path).resolve()
        if not target_dir.is_dir():
            raise FileNotFoundError(f"Target repository directory not found: {target_dir}")

        timeout_val = timeout or self.default_timeout

        # 1. Attempt hardened Docker execution if Docker daemon is running
        if self.is_docker_available():
            try:
                return self._run_in_docker(target_dir, test_target, timeout_val)
            except Exception as e:
                logger.warning(f"Docker sandbox execution encountered error ({e}); using subprocess fallback.")

        # 2. Subprocess sandbox execution with timeout and environment isolation
        return self._run_in_subprocess(target_dir, test_target, timeout_val)

    def _run_in_docker(
        self, target_dir: Path, test_target: Optional[str], timeout_val: int
    ) -> TestExecutionResult:
        """Executes pytest inside an isolated container with memory, CPU, and network limits."""
        import docker

        client = docker.from_env()
        image_tag = "swe-agent-sandbox:latest"

        # Check or build sandbox image if needed
        try:
            client.images.get(image_tag)
        except docker.errors.ImageNotFound:
            dockerfile_path = Path(__file__).resolve().parent.parent.parent / "docker"
            if (dockerfile_path / "Dockerfile.sandbox").is_file():
                client.images.build(
                    path=str(dockerfile_path),
                    dockerfile="Dockerfile.sandbox",
                    tag=image_tag,
                )
            else:
                image_tag = "python:3.11-slim"

        cmd = "pytest -v --tb=short -p no:cacheprovider"
        if test_target:
            cmd += f" {test_target}"

        start_time = time.time()
        container = client.containers.run(
            image=image_tag,
            command=f"bash -c 'pip install pytest -q && {cmd}'",
            volumes={str(target_dir): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            network_mode="none",             # Complete network isolation (no outbound connections)
            mem_limit="512m",                 # 512MB RAM ceiling
            nano_cpus=1_000_000_000,          # 1.0 CPU limit
            detach=True,
        )

        try:
            status = container.wait(timeout=timeout_val)
            duration = round(time.time() - start_time, 2)
            exit_code = status.get("StatusCode", 1)
            output = container.logs().decode("utf-8", errors="replace")
            return self._parse_pytest_output(output, exit_code, duration)
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass

    def _run_in_subprocess(
        self, target_dir: Path, test_target: Optional[str], timeout_val: int
    ) -> TestExecutionResult:
        """Subprocess sandbox execution with environment and timeout constraints."""
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "-p", "no:cacheprovider"]
        if test_target:
            cmd.append(test_target)

        start_time = time.time()
        try:
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
        failed_lines = re.findall(r"FAILED\s+([^\s:]+::[^\s\-]+)(?:\s+-\s+(.+))?", output)
        for match in failed_lines:
            test_name = match[0]
            err_msg = match[1] if len(match) > 1 and match[1] else "Test failed assertion or raised error"

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
