from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SymbolType(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class ParameterInfo(BaseModel):
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None


class SymbolInfo(BaseModel):
    name: str = Field(description="Fully qualified symbol name, e.g. 'app.users.UserService.get_users'")
    short_name: str = Field(description="Base name, e.g. 'get_users'")
    symbol_type: SymbolType
    file_path: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    parameters: List[ParameterInfo] = Field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    calls: List[str] = Field(default_factory=list, description="Names of functions called within this body")
    parent_symbol: Optional[str] = Field(default=None, description="Enclosing class name if method")


class ImportInfo(BaseModel):
    module: Optional[str] = None
    names: List[str] = Field(default_factory=list)
    alias: Optional[str] = None
    is_from: bool = False
    line_number: int


class FileInfo(BaseModel):
    file_path: str
    relative_path: str
    line_count: int
    symbols: List[SymbolInfo] = Field(default_factory=list)
    imports: List[ImportInfo] = Field(default_factory=list)


class CallRelationship(BaseModel):
    caller: str = Field(description="Caller symbol name")
    callee: str = Field(description="Callee function/method name or expression")
    file_path: str
    line_number: int


class RepoAnalysisRequest(BaseModel):
    repo_path: str = Field(description="Absolute or relative path to the local repository directory")
    ignore_patterns: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "venv",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            "dist",
            "build",
            ".egg-info",
        ],
        description="Directories and patterns to ignore during traversal",
    )


class RepoAnalysisResult(BaseModel):
    repo_path: str
    total_files: int
    total_lines: int
    total_symbols: int
    total_classes: int
    total_functions: int
    files: List[FileInfo]
    call_graph: List[CallRelationship]
    summary: str


class ImpactedSymbolItem(BaseModel):
    symbol: str
    depth: int
    file: Optional[str] = None


class ImpactAnalysisRequest(BaseModel):
    repo_path: str = Field(description="Path to repository")
    symbol_name: str = Field(description="Symbol name to analyze impact for")
    max_depth: int = Field(default=3, description="Maximum call depth to traverse")


class ImpactAnalysisResult(BaseModel):
    target: str
    found: bool
    impacted_symbols: List[ImpactedSymbolItem] = Field(default_factory=list)
    impacted_files: List[str] = Field(default_factory=list)
    impacted_tests: List[str] = Field(default_factory=list)
    total_impacted_symbols: int = 0


class SymbolSearchRequest(BaseModel):
    repo_path: str = Field(description="Path to repository")
    query: str = Field(description="Search term (matches name or short_name)")
    symbol_type: Optional[SymbolType] = None


class SymbolSearchResult(BaseModel):
    query: str
    total_matches: int
    matches: List[SymbolInfo]


class CodeChunk(BaseModel):
    chunk_id: str
    file_path: str
    relative_path: str
    symbol_name: Optional[str] = None
    symbol_type: Optional[SymbolType] = None
    line_start: int
    line_end: int
    content: str
    embedding: Optional[List[float]] = None


class SemanticSearchRequest(BaseModel):
    repo_path: str = Field(description="Path to repository")
    query: str = Field(description="Natural language query describing desired code/functionality")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SemanticSearchResultItem(BaseModel):
    chunk_id: str
    relative_path: str
    symbol_name: Optional[str] = None
    symbol_type: Optional[SymbolType] = None
    line_start: int
    line_end: int
    content: str
    score: float = Field(description="Cosine similarity score (0.0 to 1.0)")


class SemanticSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SemanticSearchResultItem]


class PlanStepAction(str, Enum):
    CREATE_FILE = "CREATE_FILE"
    MODIFY_SYMBOL = "MODIFY_SYMBOL"
    UPDATE_TESTS = "UPDATE_TESTS"
    RUN_VERIFICATION = "RUN_VERIFICATION"


class PlanStep(BaseModel):
    step_number: int
    action: PlanStepAction
    target_file: str
    target_symbol: Optional[str] = None
    instruction: str
    status: str = Field(default="PENDING", description="PENDING, IN_PROGRESS, COMPLETED, FAILED")


class PlanStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class IssuePlanRequest(BaseModel):
    repo_path: str = Field(description="Local path to repository")
    issue_title: str = Field(description="GitHub issue title or concise task name")
    issue_description: str = Field(description="Full issue description and requirements")
    issue_url: Optional[str] = None


class ImplementationPlan(BaseModel):
    plan_id: str
    repo_path: str
    issue_title: str
    issue_description: str
    summary: str
    affected_files: List[str] = Field(default_factory=list)
    target_symbols: List[str] = Field(default_factory=list)
    impacted_tests: List[str] = Field(default_factory=list)
    steps: List[PlanStep] = Field(default_factory=list)
    risk_assessment: str
    status: PlanStatus = PlanStatus.PENDING_APPROVAL
    created_at: str


class PlanUpdateRequest(BaseModel):
    status: Optional[PlanStatus] = None
    modified_steps: Optional[List[PlanStep]] = None
    notes: Optional[str] = None


class TestFailureDetail(BaseModel):
    test_name: str
    error_message: str
    traceback: str


class TestExecutionResult(BaseModel):
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    failures: List[TestFailureDetail] = Field(default_factory=list)
    raw_output: str
    duration_seconds: float


class RepairAttemptLog(BaseModel):
    attempt_number: int
    action_taken: str
    target_file: str
    target_symbol: Optional[str] = None
    test_result: TestExecutionResult


class RepairSessionResult(BaseModel):
    session_id: str
    status: str = Field(description="RESOLVED, MAX_ATTEMPTS_EXCEEDED, or ERROR")
    total_attempts: int
    initial_failures: int
    final_test_result: TestExecutionResult
    attempts_log: List[RepairAttemptLog] = Field(default_factory=list)
    git_diff: Optional[str] = None


class VerifyRequest(BaseModel):
    repo_path: str = Field(description="Path to repository")
    test_file: Optional[str] = Field(default=None, description="Optional specific test file or path")
    timeout_seconds: int = Field(default=30, description="Test execution timeout in seconds")


class RepairRequest(BaseModel):
    repo_path: str = Field(description="Path to repository")
    issue_description: str = Field(description="Description of requirement or bug to solve")
    target_file: str = Field(description="Relative path to file needing repair")
    target_symbol: str = Field(description="Symbol name needing repair")
    repaired_code: Optional[str] = Field(default=None, description="Optional explicit replacement code")
    max_attempts: int = Field(default=3, description="Maximum automated repair attempts")




