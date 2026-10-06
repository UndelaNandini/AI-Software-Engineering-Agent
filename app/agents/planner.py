import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from app.config import get_settings
from app.core.ast_parser import ASTRepositoryAnalyzer
from app.core.code_graph import CodeGraph
from app.core.indexer import CodebaseIndexer
from app.models.schemas import (
    ImplementationPlan,
    IssuePlanRequest,
    PlanStatus,
    PlanStep,
    PlanStepAction,
    PlanUpdateRequest,
)


class IssuePlanner:
    """Agent responsible for investigating repository context and formulating implementation plans."""

    def __init__(self):
        self._plans: Dict[str, ImplementationPlan] = {}
        self.settings = get_settings()

    def generate_plan(self, request: IssuePlanRequest) -> ImplementationPlan:
        """Assembles hybrid AST and semantic retrieval context, then produces a structured ImplementationPlan."""
        target_path = Path(request.repo_path).resolve()
        if not target_path.exists() or not target_path.is_dir():
            raise FileNotFoundError(f"Repository directory not found: {request.repo_path}")

        # 1. AST Static Parsing
        analyzer = ASTRepositoryAnalyzer(repo_path=str(target_path))
        analysis = analyzer.analyze()

        # 2. Semantic Code Retrieval
        indexer = CodebaseIndexer(repo_path=str(target_path))
        indexer.chunk_repository(analysis)
        search_query = f"{request.issue_title} {request.issue_description}"
        top_chunks = indexer.search(query=search_query, top_k=3)

        # 3. Call Graph Impact Analysis
        graph = CodeGraph().build_from_analysis(analysis)

        affected_files: List[str] = []
        target_symbols: List[str] = []
        impacted_tests: List[str] = []

        for chunk in top_chunks:
            if chunk.relative_path not in affected_files:
                affected_files.append(chunk.relative_path)
            if chunk.symbol_name and chunk.symbol_name not in target_symbols:
                target_symbols.append(chunk.symbol_name)
                # Compute upstream impact
                impact = graph.get_impact_radius(chunk.symbol_name, max_depth=2)
                for t in impact.get("impacted_tests", []):
                    rel_t = str(Path(t).relative_to(target_path)).replace("\\", "/") if Path(t).is_absolute() else t
                    if rel_t not in impacted_tests:
                        impacted_tests.append(rel_t)

        # If no specific tests were directly impacted, check for existing test files
        if not impacted_tests:
            for f in analysis.files:
                if "test" in f.relative_path.lower():
                    impacted_tests.append(f.relative_path)

        # 4. Formulate Steps
        steps: List[PlanStep] = []
        step_num = 1

        # File creation or primary modification steps
        if target_symbols:
            for sym in target_symbols:
                file_for_sym = next(
                    (c.relative_path for c in top_chunks if c.symbol_name == sym),
                    affected_files[0] if affected_files else "app/main.py",
                )
                steps.append(
                    PlanStep(
                        step_number=step_num,
                        action=PlanStepAction.MODIFY_SYMBOL,
                        target_file=file_for_sym,
                        target_symbol=sym,
                        instruction=f"Update '{sym}' to implement requirements for '{request.issue_title}'.",
                    )
                )
                step_num += 1
        elif affected_files:
            steps.append(
                PlanStep(
                    step_number=step_num,
                    action=PlanStepAction.MODIFY_SYMBOL,
                    target_file=affected_files[0],
                    target_symbol=None,
                    instruction=f"Implement changes required for '{request.issue_title}' in {affected_files[0]}.",
                )
            )
            step_num += 1
        else:
            # Fallback when repo is empty or new file is needed
            steps.append(
                PlanStep(
                    step_number=step_num,
                    action=PlanStepAction.CREATE_FILE,
                    target_file="app/features.py",
                    target_symbol=None,
                    instruction=f"Create implementation for: {request.issue_title}",
                )
            )
            step_num += 1

        # Test step
        test_file_target = impacted_tests[0] if impacted_tests else "tests/test_feature.py"
        steps.append(
            PlanStep(
                step_number=step_num,
                action=PlanStepAction.UPDATE_TESTS,
                target_file=test_file_target,
                target_symbol=None,
                instruction=f"Add unit test assertions verifying: {request.issue_title}",
            )
        )
        step_num += 1

        # Verification step
        steps.append(
            PlanStep(
                step_number=step_num,
                action=PlanStepAction.RUN_VERIFICATION,
                target_file=test_file_target,
                target_symbol=None,
                instruction="Execute pytest test suite in isolated sandbox and ensure all tests pass.",
            )
        )

        plan_id = str(uuid.uuid4())
        summary = (
            f"Implementation plan for '{request.issue_title}'. "
            f"Targeting {len(target_symbols)} symbols across {len(affected_files)} files, "
            f"with {len(impacted_tests)} test suites to verify."
        )

        risk_assessment = (
            f"Low to moderate risk. {len(affected_files)} files directly modified. "
            f"Upstream impact identified in {len(impacted_tests)} test files."
        )

        plan = ImplementationPlan(
            plan_id=plan_id,
            repo_path=str(target_path).replace("\\", "/"),
            issue_title=request.issue_title,
            issue_description=request.issue_description,
            summary=summary,
            affected_files=affected_files,
            target_symbols=target_symbols,
            impacted_tests=impacted_tests,
            steps=steps,
            risk_assessment=risk_assessment,
            status=PlanStatus.PENDING_APPROVAL,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        self._plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[ImplementationPlan]:
        return self._plans.get(plan_id)

    def list_plans(self) -> List[ImplementationPlan]:
        return list(self._plans.values())

    def update_plan(self, plan_id: str, update: PlanUpdateRequest) -> Optional[ImplementationPlan]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        if update.status is not None:
            plan.status = update.status
        if update.modified_steps is not None:
            plan.steps = update.modified_steps

        return plan


# Global singleton instance for in-memory session management
issue_planner = IssuePlanner()
