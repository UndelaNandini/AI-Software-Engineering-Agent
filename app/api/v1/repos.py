import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status

from app.core.ast_parser import ASTRepositoryAnalyzer
from app.core.code_graph import CodeGraph
from app.core.indexer import CodebaseIndexer
from app.models.schemas import (
    ImpactAnalysisRequest,
    ImpactAnalysisResult,
    RepoAnalysisRequest,
    RepoAnalysisResult,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SymbolSearchRequest,
    SymbolSearchResult,
)

router = APIRouter()



@router.post(
    "/analyze",
    response_model=RepoAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze Repository AST",
    description="Deterministically parses all Python files in a target repository, extracting symbols, imports, and function call relationships.",
)
async def analyze_repository(request: RepoAnalysisRequest) -> RepoAnalysisResult:
    target_path = Path(request.repo_path).resolve()

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target path does not exist: {request.repo_path}",
        )

    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target path is not a directory: {request.repo_path}",
        )

    try:
        analyzer = ASTRepositoryAnalyzer(
            repo_path=str(target_path),
            ignore_patterns=request.ignore_patterns,
        )
        result = analyzer.analyze()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository analysis failed: {str(e)}",
        )


@router.post(
    "/impact",
    response_model=ImpactAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Symbol Impact Analysis",
    description="Computes the upstream ripple impact of changing a symbol (finding all calling functions and affected test suites).",
)
async def analyze_symbol_impact(request: ImpactAnalysisRequest) -> ImpactAnalysisResult:
    target_path = Path(request.repo_path).resolve()

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository directory: {request.repo_path}",
        )

    analyzer = ASTRepositoryAnalyzer(repo_path=str(target_path))
    analysis = analyzer.analyze()

    graph = CodeGraph().build_from_analysis(analysis)
    impact_data = graph.get_impact_radius(request.symbol_name, max_depth=request.max_depth)

    return ImpactAnalysisResult(**impact_data)


@router.post(
    "/symbols/search",
    response_model=SymbolSearchResult,
    status_code=status.HTTP_200_OK,
    summary="Search Repository Symbols",
    description="Search for functions, classes, or methods across the repository by name.",
)
async def search_symbols(request: SymbolSearchRequest) -> SymbolSearchResult:
    target_path = Path(request.repo_path).resolve()

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository directory: {request.repo_path}",
        )

    analyzer = ASTRepositoryAnalyzer(repo_path=str(target_path))
    analysis = analyzer.analyze()

    query_lower = request.query.lower()
    matches = []

    for file_info in analysis.files:
        for sym in file_info.symbols:
            if request.symbol_type and sym.symbol_type != request.symbol_type:
                continue
            if query_lower in sym.short_name.lower() or query_lower in sym.name.lower():
                matches.append(sym)

    return SymbolSearchResult(
        query=request.query,
        total_matches=len(matches),
        matches=matches,
    )


@router.post(
    "/search/semantic",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Code Search (ML RAG)",
    description="Search code chunks by natural language concept using AST-chunked TF-IDF vector embeddings and cosine similarity.",
)
async def semantic_search(request: SemanticSearchRequest) -> SemanticSearchResponse:
    target_path = Path(request.repo_path).resolve()

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository directory: {request.repo_path}",
        )

    analyzer = ASTRepositoryAnalyzer(repo_path=str(target_path))
    analysis = analyzer.analyze()

    indexer = CodebaseIndexer(repo_path=str(target_path))
    indexer.chunk_repository(analysis)

    results = indexer.search(
        query=request.query,
        top_k=request.top_k,
        min_score=request.min_score,
    )

    return SemanticSearchResponse(
        query=request.query,
        total_results=len(results),
        results=results,
    )


