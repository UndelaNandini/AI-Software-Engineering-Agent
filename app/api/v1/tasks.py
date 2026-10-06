from pathlib import Path
from fastapi import APIRouter, HTTPException, status

from app.agents.debugger import debugger_agent
from app.models.schemas import (
    RepairRequest,
    RepairSessionResult,
    TestExecutionResult,
    VerifyRequest,
)
from app.tools.sandbox_runner import sandbox_runner

router = APIRouter()


@router.post(
    "/verify",
    response_model=TestExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Run Test Verification in Sandbox",
    description="Executes repository test suites (pytest) in an isolated subprocess with timeout protection.",
)
async def verify_tests(request: VerifyRequest) -> TestExecutionResult:
    target_path = Path(request.repo_path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target repository directory not found: {request.repo_path}",
        )

    try:
        result = sandbox_runner.run_pytest(
            repo_path=target_path,
            test_target=request.test_file,
            timeout=request.timeout_seconds,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test verification execution failed: {str(e)}",
        )


@router.post(
    "/repair",
    response_model=RepairSessionResult,
    status_code=status.HTTP_200_OK,
    summary="Run Self-Repair Verification Loop",
    description="Iteratively corrects failing tests by inspecting tracebacks and surgically modifying code (max 3 attempts).",
)
async def run_self_repair(request: RepairRequest) -> RepairSessionResult:
    target_path = Path(request.repo_path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target repository directory not found: {request.repo_path}",
        )

    try:
        result = debugger_agent.repair(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Self-repair execution failed: {str(e)}",
        )
