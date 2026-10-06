import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.ast_parser import ASTRepositoryAnalyzer
from app.models.schemas import (
    CodeChunk,
    RepoAnalysisResult,
    SemanticSearchResultItem,
    SymbolInfo,
)


def _tokenize_code(text: str) -> str:
    """Split camelCase, PascalCase, and snake_case to enrich semantic code matching."""
    # Split camelCase and PascalCase
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    # Replace non-alphanumeric with spaces
    tokens = re.sub(r"[^a-zA-Z0-9_]", " ", s1).split()
    expanded = []
    for t in tokens:
        expanded.append(t)
        if "_" in t:
            expanded.extend([part for part in t.split("_") if part])
    return " ".join(expanded)


class CodebaseIndexer:
    """Chunks repository code along AST boundaries and performs semantic similarity search."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.chunks: List[CodeChunk] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix: Optional[np.ndarray] = None

    def _extract_chunk_content(self, file_path: Path, line_start: int, line_end: int) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            # 1-indexed to 0-indexed
            start_idx = max(0, line_start - 1)
            end_idx = min(len(lines), line_end)
            return "".join(lines[start_idx:end_idx])
        except Exception:
            return ""

    def chunk_repository(self, analysis: RepoAnalysisResult) -> List[CodeChunk]:
        """Create semantic code chunks aligned with AST symbols."""
        self.chunks.clear()

        for file_info in analysis.files:
            file_abs_path = Path(file_info.file_path)
            if not file_abs_path.is_file():
                continue

            # 1. Chunk each extracted symbol (function, class, method)
            for sym in file_info.symbols:
                raw_code = self._extract_chunk_content(file_abs_path, sym.line_start, sym.line_end)
                if not raw_code.strip():
                    continue

                # Prepend semantic header to amplify retrieval signal
                doc_header = f"Docstring: {sym.docstring}\n" if sym.docstring else ""
                params_str = ", ".join(p.name for p in sym.parameters) if sym.parameters else ""
                signature_header = f"Signature: {sym.short_name}({params_str})\n"

                enriched_content = (
                    f"# File: {file_info.relative_path}\n"
                    f"# Symbol: {sym.name} ({sym.symbol_type.value})\n"
                    f"{doc_header}"
                    f"{signature_header}"
                    f"{raw_code}"
                )

                chunk_id = hashlib.sha256(f"{file_info.relative_path}::{sym.name}".encode()).hexdigest()[:16]
                chunk = CodeChunk(
                    chunk_id=chunk_id,
                    file_path=file_info.file_path,
                    relative_path=file_info.relative_path,
                    symbol_name=sym.name,
                    symbol_type=sym.symbol_type,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    content=enriched_content,
                )
                self.chunks.append(chunk)

            # 2. If file has no symbols or few lines, create file-level chunk
            if not file_info.symbols and file_info.line_count > 0:
                raw_code = self._extract_chunk_content(file_abs_path, 1, file_info.line_count)
                if raw_code.strip():
                    chunk_id = hashlib.sha256(f"{file_info.relative_path}::module".encode()).hexdigest()[:16]
                    chunk = CodeChunk(
                        chunk_id=chunk_id,
                        file_path=file_info.file_path,
                        relative_path=file_info.relative_path,
                        symbol_name=None,
                        symbol_type=None,
                        line_start=1,
                        line_end=file_info.line_count,
                        content=f"# File: {file_info.relative_path}\n{raw_code}",
                    )
                    self.chunks.append(chunk)

        # Build search index
        self._build_index()
        return self.chunks

    def _build_index(self):
        """Builds TF-IDF vector space model across tokenized code chunks."""
        if not self.chunks:
            self._vectorizer = None
            self._tfidf_matrix = None
            return

        corpus = [_tokenize_code(chunk.content) for chunk in self.chunks]
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            stop_words="english",
            max_features=10000,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus)

    def search(
        self, query: str, top_k: int = 5, min_score: float = 0.0
    ) -> List[SemanticSearchResultItem]:
        """Performs cosine similarity search against indexed code chunks."""
        if not self.chunks or self._vectorizer is None or self._tfidf_matrix is None:
            return []

        tokenized_query = _tokenize_code(query)
        if not tokenized_query.strip():
            return []

        query_vec = self._vectorizer.transform([tokenized_query])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Get top-k indices sorted descending
        top_indices = np.argsort(similarities)[::-1]

        results: List[SemanticSearchResultItem] = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < min_score:
                break
            if len(results) >= top_k:
                break

            chunk = self.chunks[idx]
            results.append(
                SemanticSearchResultItem(
                    chunk_id=chunk.chunk_id,
                    relative_path=chunk.relative_path,
                    symbol_name=chunk.symbol_name,
                    symbol_type=chunk.symbol_type,
                    line_start=chunk.line_start,
                    line_end=chunk.line_end,
                    content=chunk.content,
                    score=round(score, 4),
                )
            )

        return results
