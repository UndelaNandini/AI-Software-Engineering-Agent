import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.debugger import debugger_agent
from app.agents.planner import issue_planner
from app.agents.reviewer import CodeReviewReport, code_reviewer
from app.core.ast_parser import ASTRepositoryAnalyzer
from app.core.code_graph import CodeGraph
from app.core.event_stream import EventType, event_stream
from app.core.git_manager import GitManager
from app.core.indexer import CodebaseIndexer
from app.core.llm_client import llm_client
from app.models.schemas import (
    ImplementationPlan,
    IssuePlanRequest,
    PlanStatus,
    RepairRequest,
    RepairSessionResult,
    TestExecutionResult,
)
from app.tools.file_tools import replace_symbol_code
from app.tools.sandbox_runner import sandbox_runner


class OrchestratorRunResult(BaseModel):
    task_id: str
    status: str = Field(description="SUCCESS, REPAIRED, FAILED, or APPROVAL_REQUIRED")
    plan: ImplementationPlan
    initial_test_result: Optional[TestExecutionResult] = None
    final_test_result: Optional[TestExecutionResult] = None
    repair_session: Optional[RepairSessionResult] = None
    review_report: Optional[CodeReviewReport] = None
    git_diff: str = ""
    summary: str = ""


class AgentOrchestrator:
    """Master workflow coordinator executing the end-to-end software engineering lifecycle."""

    async def execute_task(
        self,
        repo_path: str,
        issue_title: str,
        issue_description: str,
        auto_approve_plan: bool = True,
        max_repair_attempts: int = 3,
        explicit_code_fix: Optional[str] = None,
    ) -> OrchestratorRunResult:
        task_id = event_stream.create_task()
        target_dir = Path(repo_path).resolve()

        # 1. System start
        await event_stream.emit(
            task_id,
            EventType.SYSTEM,
            f"Starting autonomous software engineering agent for task: '{issue_title}'",
            {"repo_path": str(target_dir)},
        )

        # 2. Repository Analysis & RAG
        await event_stream.emit(
            task_id,
            EventType.THINKING,
            "Parsing repository Abstract Syntax Trees and building code intelligence graph...",
        )
        analyzer = ASTRepositoryAnalyzer(repo_path=str(target_dir))
        analysis = analyzer.analyze()
        indexer = CodebaseIndexer(repo_path=str(target_dir))
        indexer.chunk_repository(analysis)
        graph = CodeGraph().build_from_analysis(analysis)

        await event_stream.emit(
            task_id,
            EventType.TOOL_RESULT,
            f"Repository indexed: {analysis.total_files} files, {analysis.total_symbols} symbols, {len(analysis.call_graph)} call edges.",
            {"total_files": analysis.total_files, "total_symbols": analysis.total_symbols},
        )

        # 3. Formulate Plan
        await event_stream.emit(
            task_id,
            EventType.THINKING,
            "Synthesizing issue requirements with retrieved context into an Implementation Plan...",
        )
        plan_req = IssuePlanRequest(
            repo_path=str(target_dir),
            issue_title=issue_title,
            issue_description=issue_description,
        )
        plan = issue_planner.generate_plan(plan_req)

        await event_stream.emit(
            task_id,
            EventType.TOOL_RESULT,
            f"Plan generated (ID: {plan.plan_id}): {len(plan.steps)} steps formulated across {len(plan.affected_files)} files.",
            {"plan_id": plan.plan_id, "steps": [s.model_dump() for s in plan.steps]},
        )

        if auto_approve_plan:
            plan.status = PlanStatus.APPROVED
            await event_stream.emit(
                task_id,
                EventType.SYSTEM,
                "Plan automatically approved for execution.",
            )

        # 4. Code Modification
        target_sym = plan.target_symbols[0] if plan.target_symbols else None
        target_file = plan.affected_files[0] if plan.affected_files else None

        if target_file and target_sym and explicit_code_fix:
            await event_stream.emit(
                task_id,
                EventType.TOOL_CALL,
                f"Surgically updating symbol '{target_sym}' in '{target_file}'...",
            )
            replace_symbol_code(target_dir / target_file, target_sym, explicit_code_fix)
            await event_stream.emit(
                task_id,
                EventType.TOOL_RESULT,
                f"Successfully updated symbol '{target_sym}' with AST validation.",
            )

        # 5. Verification Run
        await event_stream.emit(
            task_id,
            EventType.THINKING,
            "Executing pytest verification in isolated sandbox...",
        )
        initial_test_result = sandbox_runner.run_pytest(target_dir)

        await event_stream.emit(
            task_id,
            EventType.TEST_OUTPUT,
            f"Initial verification: {initial_test_result.passed_tests} passed, {initial_test_result.failed_tests} failed.",
            initial_test_result.model_dump(),
        )

        repair_session = None
        final_test_result = initial_test_result

        # 6. Self-Repair Loop if tests failed
        if not initial_test_result.passed and target_file and target_sym:
            await event_stream.emit(
                task_id,
                EventType.REPAIR_ATTEMPT,
                f"Initial tests failed ({initial_test_result.failed_tests} failures). Entering self-repair loop...",
            )

            repair_req = RepairRequest(
                repo_path=str(target_dir),
                issue_description=issue_description,
                target_file=target_file,
                target_symbol=target_sym,
                repaired_code=explicit_code_fix,
                max_attempts=max_repair_attempts,
            )
            repair_session = debugger_agent.repair(repair_req)
            final_test_result = repair_session.final_test_result

            await event_stream.emit(
                task_id,
                EventType.REPAIR_ATTEMPT,
                f"Self-repair session finished with status: '{repair_session.status}' after {repair_session.total_attempts} attempts.",
                repair_session.model_dump(),
            )

        # 7. Code Review Audit
        git_diff = GitManager.get_diff(target_dir)
        await event_stream.emit(
            task_id,
            EventType.THINKING,
            "Performing automated Senior Code Review and security audit on diff...",
        )
        review_report = code_reviewer.review_diff(git_diff)

        await event_stream.emit(
            task_id,
            EventType.REVIEW,
            f"Code Review: Security={review_report.security_verdict}, Quality={review_report.quality_verdict}.",
            review_report.model_dump(),
        )

        overall_status = "SUCCESS" if final_test_result.passed else "FAILED"
        if repair_session and repair_session.status == "RESOLVED":
            overall_status = "REPAIRED"

        summary = (
            f"Task '{issue_title}' completed with status: {overall_status}. "
            f"Tests: {final_test_result.passed_tests} passed, {final_test_result.failed_tests} failed. "
            f"Security Audit: {review_report.security_verdict}."
        )

        await event_stream.emit(
            task_id,
            EventType.COMPLETE,
            summary,
            {"status": overall_status},
        )

        return OrchestratorRunResult(
            task_id=task_id,
            status=overall_status,
            plan=plan,
            initial_test_result=initial_test_result,
            final_test_result=final_test_result,
            repair_session=repair_session,
            review_report=review_report,
            git_diff=git_diff,
            summary=summary,
        )


orchestrator = AgentOrchestrator()
