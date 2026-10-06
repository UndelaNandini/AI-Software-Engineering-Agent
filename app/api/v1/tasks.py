import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from app.agents.debugger import debugger_agent
from app.agents.orchestrator import OrchestratorRunResult, orchestrator
from app.core.event_stream import AgentEvent, EventType, event_stream
from app.models.schemas import (
    RepairRequest,
    RepairSessionResult,
    TestExecutionResult,
    VerifyRequest,
)
from app.tools.sandbox_runner import sandbox_runner

router = APIRouter()


class OrchestratorRunRequest(BaseModel):
    repo_path: str = Field(description="Target repository directory path")
    issue_title: str = Field(description="Issue title or task headline")
    issue_description: str = Field(description="Issue details and requirements")
    auto_approve_plan: bool = Field(default=True, description="Automatically approve generated plan")
    max_repair_attempts: int = Field(default=3, description="Maximum automated self-repair attempts")
    explicit_code_fix: Optional[str] = Field(default=None, description="Optional explicit code fix to apply")


@router.post(
    "/run",
    response_model=OrchestratorRunResult,
    status_code=status.HTTP_200_OK,
    summary="Run Autonomous End-to-End Task",
    description="Orchestrates repository ingestion, plan creation, surgical edits, sandbox verification, self-repair, and code review.",
)
async def run_orchestrated_task(request: OrchestratorRunRequest) -> OrchestratorRunResult:
    target_path = Path(request.repo_path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target repository directory not found: {request.repo_path}",
        )

    try:
        result = await orchestrator.execute_task(
            repo_path=str(target_path),
            issue_title=request.issue_title,
            issue_description=request.issue_description,
            auto_approve_plan=request.auto_approve_plan,
            max_repair_attempts=request.max_repair_attempts,
            explicit_code_fix=request.explicit_code_fix,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task orchestration failed: {str(e)}",
        )


@router.websocket("/{task_id}/stream")
async def websocket_event_stream(websocket: WebSocket, task_id: str):
    """Real-time WebSocket connection streaming agent execution events."""
    await websocket.accept()
    queue = event_stream.subscribe(task_id)

    # First send all historical events for this task
    for past_event in event_stream.get_task_log(task_id):
        await websocket.send_json(past_event.model_dump())

    try:
        while True:
            event: AgentEvent = await queue.get()
            await websocket.send_json(event.model_dump())
            if event.event_type in (EventType.COMPLETE, EventType.ERROR):
                break
    except WebSocketDisconnect:
        pass
    finally:
        event_stream.unsubscribe(task_id, queue)


@router.get(
    "/{task_id}/events",
    response_model=List[AgentEvent],
    status_code=status.HTTP_200_OK,
    summary="Get Task Event Logs",
    description="Retrieve all real-time events logged during the execution of a task.",
)
async def get_task_events(task_id: str) -> List[AgentEvent]:
    return event_stream.get_task_log(task_id)


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
