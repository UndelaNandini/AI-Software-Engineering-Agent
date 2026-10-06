import asyncio
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

from app.agents.orchestrator import orchestrator
from app.agents.planner import issue_planner
from app.agents.reviewer import code_reviewer
from app.core.ast_parser import ASTRepositoryAnalyzer
from app.core.code_graph import CodeGraph
from app.core.indexer import CodebaseIndexer
from app.models.schemas import IssuePlanRequest
from app.tools.file_tools import read_file_range, replace_symbol_code
from app.tools.sandbox_runner import sandbox_runner

# Initialize MCP Server
mcp = MCPServer("AI-Software-Engineering-Agent")


@mcp.tool()
def analyze_repository(repo_path: str = ".") -> str:
    """Analyze Python codebase Abstract Syntax Tree and return symbol tree and statistics."""
    analyzer = ASTRepositoryAnalyzer(repo_path=repo_path)
    analysis = analyzer.analyze()
    return json.dumps({
        "total_files": analysis.total_files,
        "total_lines": analysis.total_lines,
        "total_classes": analysis.total_classes,
        "total_functions": analysis.total_functions,
        "total_symbols": analysis.total_symbols,
        "call_edges": len(analysis.call_graph),
    }, indent=2)


@mcp.tool()
def compute_impact(repo_path: str, symbol_name: str) -> str:
    """Compute upstream ripple impact radius and affected test suites for a function or class."""
    analyzer = ASTRepositoryAnalyzer(repo_path=repo_path)
    analysis = analyzer.analyze()
    graph = CodeGraph().build_from_analysis(analysis)
    impact = graph.get_impact_radius(symbol_name)
    return json.dumps(impact, indent=2)


@mcp.tool()
def semantic_code_search(repo_path: str, query: str, top_k: int = 5) -> str:
    """Semantic subword vector search across codebase AST chunks."""
    analyzer = ASTRepositoryAnalyzer(repo_path=repo_path)
    analysis = analyzer.analyze()
    indexer = CodebaseIndexer(repo_path=repo_path)
    indexer.chunk_repository(analysis)
    results = indexer.search(query, top_k=top_k)
    return json.dumps([r.model_dump() for r in results], indent=2)


@mcp.tool()
def plan_issue(repo_path: str, issue_title: str, issue_description: str) -> str:
    """Formulate a step-by-step Pydantic implementation plan for an issue."""
    req = IssuePlanRequest(
        repo_path=repo_path,
        issue_title=issue_title,
        issue_description=issue_description or issue_title,
    )
    plan = issue_planner.generate_plan(req)
    return json.dumps(plan.model_dump(), indent=2)


@mcp.tool()
def replace_symbol(file_path: str, symbol_name: str, new_code: str) -> str:
    """Surgically replace a Python function or class using AST validation with rollback."""
    success = replace_symbol_code(file_path, symbol_name, new_code)
    return f"Symbol '{symbol_name}' replacement {'succeeded' if success else 'failed'}."


@mcp.tool()
def run_tests(repo_path: str, test_file: str = "") -> str:
    """Execute pytest verification in isolated sandbox with timeout limits."""
    result = sandbox_runner.run_pytest(Path(repo_path), test_target=test_file or None)
    return json.dumps(result.model_dump(), indent=2)


@mcp.tool()
def review_diff(diff_content: str) -> str:
    """Perform Senior Code Review and security audit on unified git diff."""
    report = code_reviewer.review_diff(diff_content)
    return json.dumps(report.model_dump(), indent=2)


@mcp.tool()
async def run_autonomous_agent(repo_path: str, issue_title: str, issue_description: str) -> str:
    """Run full autonomous software engineering agent from issue to verified diff & review."""
    result = await orchestrator.execute_task(
        repo_path=repo_path,
        issue_title=issue_title,
        issue_description=issue_description,
        auto_approve_plan=True,
    )
    return json.dumps({
        "task_id": result.task_id,
        "status": result.status,
        "summary": result.summary,
        "security_verdict": result.review_report.security_verdict if result.review_report else "PASS",
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
