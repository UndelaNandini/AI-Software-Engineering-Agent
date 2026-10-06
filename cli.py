import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from app.agents.orchestrator import orchestrator
from app.agents.planner import issue_planner
from app.core.ast_parser import ASTRepositoryAnalyzer
from app.core.code_graph import CodeGraph
from app.models.schemas import IssuePlanRequest

console = Console(force_terminal=True, legacy_windows=False)


@click.group()
def cli():
    """AI Software Engineering Agent CLI - Autonomous codebase intelligence & repair."""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
def analyze(repo_path: str):
    """Deterministically analyze repository AST structure and symbols."""
    console.print(f"\n[bold cyan]Analyzing repository:[/] [dim]{repo_path}[/]\n")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(description="Parsing Abstract Syntax Trees...", total=None)
        analyzer = ASTRepositoryAnalyzer(repo_path=repo_path)
        analysis = analyzer.analyze()

    table = Table(title="Repository Intelligence Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Total Files", str(analysis.total_files))
    table.add_row("Total Lines of Code", str(analysis.total_lines))
    table.add_row("Classes Found", str(analysis.total_classes))
    table.add_row("Functions & Methods", str(analysis.total_functions))
    table.add_row("Total Symbols", str(analysis.total_symbols))
    table.add_row("Call Relationships", str(len(analysis.call_graph)))

    console.print(table)

    tree = Tree(f"[bold yellow]Directory: {Path(repo_path).name}[/]")
    for f in analysis.files[:10]:
        branch = tree.add(f"[cyan]{f.relative_path}[/] ([dim]{f.line_count} lines[/])")
        for sym in f.symbols[:5]:
            type_label = "[C]" if sym.symbol_type.value == "class" else "[F]"
            branch.add(f"{type_label} [bold]{sym.short_name}[/] [dim]({sym.symbol_type.value}, L{sym.line_start}-L{sym.line_end})[/]")

    console.print(tree)
    console.print(f"\n[bold green]Analysis complete![/]\n")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.argument("symbol_name")
def impact(repo_path: str, symbol_name: str):
    """Compute upstream ripple impact radius for a target function or class."""
    console.print(f"\n[bold cyan]Computing impact radius for symbol:[/] [bold yellow]{symbol_name}[/]\n")

    analyzer = ASTRepositoryAnalyzer(repo_path=repo_path)
    analysis = analyzer.analyze()
    graph = CodeGraph().build_from_analysis(analysis)

    impact_data = graph.get_impact_radius(symbol_name)
    if not impact_data["found"]:
        console.print(f"[bold red]Symbol '{symbol_name}' was not found in the repository graph.[/]")
        return

    table = Table(title=f"Ripple Impact for `{symbol_name}`", header_style="bold magenta")
    table.add_column("Impacted Symbol", style="cyan")
    table.add_column("Call Depth", style="yellow", justify="center")
    table.add_column("File Location", style="dim")

    for item in impact_data["impacted_symbols"]:
        table.add_row(item["symbol"], str(item["depth"]), item.get("file", ""))

    console.print(table)
    test_str = ", ".join(impact_data["impacted_tests"]) if impact_data["impacted_tests"] else "None detected"
    console.print(f"\n[bold green]Affected Test Suites:[/] {test_str}\n")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--title", "-t", required=True, help="Issue headline or title")
@click.option("--desc", "-d", default="", help="Detailed issue requirements")
def plan(repo_path: str, title: str, desc: str):
    """Formulate an interactive implementation plan for an issue."""
    console.print(Panel(f"[bold cyan]Issue:[/] {title}\n[dim]{desc}[/]", title="Planning Agent", border_style="cyan"))

    req = IssuePlanRequest(repo_path=repo_path, issue_title=title, issue_description=desc or title)
    p = issue_planner.generate_plan(req)

    console.print(f"\n[bold green]Plan Generated (ID: {p.plan_id}):[/]")
    console.print(f"[bold yellow]Summary:[/] {p.summary}\n")

    steps_table = Table(title="Proposed Implementation Steps", header_style="bold blue")
    steps_table.add_column("#", justify="center", style="dim")
    steps_table.add_column("Action", style="yellow")
    steps_table.add_column("Target File", style="cyan")
    steps_table.add_column("Instruction", style="white")

    for step in p.steps:
        steps_table.add_row(str(step.step_number), step.action.value, step.target_file, step.instruction)

    console.print(steps_table)
    console.print(f"\n[bold magenta]Risk Assessment:[/] {p.risk_assessment}\n")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--title", "-t", required=True, help="Issue headline")
@click.option("--desc", "-d", default="", help="Issue description")
@click.option("--fix", "-f", default=None, help="Optional code replacement")
def run(repo_path: str, title: str, desc: str, fix: Optional[str]):
    """Execute end-to-end autonomous agent cycle on an issue."""
    console.print(Panel(f"[bold white on blue] AI SOFTWARE ENGINEERING AGENT RUNNER [/]\n\n[bold cyan]Target Repo:[/] {repo_path}\n[bold yellow]Issue:[/] {title}", border_style="blue"))

    async def _run():
        result = await orchestrator.execute_task(
            repo_path=repo_path,
            issue_title=title,
            issue_description=desc or title,
            auto_approve_plan=True,
            explicit_code_fix=fix,
        )

        status_color = "green" if result.status in ("SUCCESS", "REPAIRED") else "red"
        console.print(f"\n[bold {status_color}]Run completed with status: {result.status}[/]\n")

        if result.git_diff:
            console.print(Panel(Syntax(result.git_diff, "diff", theme="monokai", line_numbers=True), title="Generated Git Diff", border_style="green"))

        if result.review_report:
            console.print(Panel(
                f"[bold cyan]Security Audit:[/] {result.review_report.security_verdict}\n"
                f"[bold cyan]Performance:[/] {result.review_report.performance_verdict}\n"
                f"[bold cyan]Quality:[/] {result.review_report.quality_verdict}\n\n"
                f"{result.review_report.summary}",
                title="Senior Code Reviewer Verdict",
                border_style="magenta",
            ))

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
