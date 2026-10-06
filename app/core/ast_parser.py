import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.schemas import (
    CallRelationship,
    FileInfo,
    ImportInfo,
    ParameterInfo,
    RepoAnalysisResult,
    SymbolInfo,
    SymbolType,
)


class CodeVisitor(ast.NodeVisitor):
    """AST Visitor that traverses an individual Python file and extracts symbols, imports, and calls."""

    def __init__(self, file_path: str, relative_path: str, module_qualname: str):
        self.file_path = file_path
        self.relative_path = relative_path
        self.module_qualname = module_qualname

        self.symbols: List[SymbolInfo] = []
        self.imports: List[ImportInfo] = []
        self.call_relationships: List[CallRelationship] = []

        self._current_class: Optional[str] = None
        self._current_class_qualname: Optional[str] = None

    def _unparse_safe(self, node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except Exception:
            return None

    def _extract_call_name(self, node: ast.AST) -> str:
        """Extract a readable string for a function call target."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._extract_call_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        try:
            return ast.unparse(node)
        except Exception:
            return "<unknown_call>"

    def _extract_parameters(self, args_node: ast.arguments) -> List[ParameterInfo]:
        parameters: List[ParameterInfo] = []

        # Map positional defaults
        defaults = args_node.defaults
        num_args = len(args_node.args)
        num_defaults = len(defaults)
        default_offset = num_args - num_defaults

        for idx, arg in enumerate(args_node.args):
            default_val = None
            if idx >= default_offset:
                default_val = self._unparse_safe(defaults[idx - default_offset])

            param = ParameterInfo(
                name=arg.arg,
                type_annotation=self._unparse_safe(arg.annotation),
                default_value=default_val,
            )
            parameters.append(param)

        # Vararg (*args)
        if args_node.vararg:
            parameters.append(
                ParameterInfo(
                    name=f"*{args_node.vararg.arg}",
                    type_annotation=self._unparse_safe(args_node.vararg.annotation),
                )
            )

        # Keyword-only arguments
        for idx, kwarg in enumerate(args_node.kwonlyargs):
            kw_default = None
            if idx < len(args_node.kw_defaults) and args_node.kw_defaults[idx]:
                kw_default = self._unparse_safe(args_node.kw_defaults[idx])
            parameters.append(
                ParameterInfo(
                    name=kwarg.arg,
                    type_annotation=self._unparse_safe(kwarg.annotation),
                    default_value=kw_default,
                )
            )

        # Kwarg (**kwargs)
        if args_node.kwarg:
            parameters.append(
                ParameterInfo(
                    name=f"**{args_node.kwarg.arg}",
                    type_annotation=self._unparse_safe(args_node.kwarg.annotation),
                )
            )

        return parameters

    def visit_Import(self, node: ast.Import):
        names = [alias.name for alias in node.names]
        alias = node.names[0].asname if node.names and node.names[0].asname else None
        self.imports.append(
            ImportInfo(
                module=None,
                names=names,
                alias=alias,
                is_from=False,
                line_number=node.lineno,
            )
        )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        if node.level > 0:
            module = "." * node.level + module
        names = [alias.name for alias in node.names]
        self.imports.append(
            ImportInfo(
                module=module,
                names=names,
                alias=None,
                is_from=True,
                line_number=node.lineno,
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        class_qualname = (
            f"{self.module_qualname}.{node.name}"
            if self.module_qualname
            else node.name
        )
        decorators = [self._unparse_safe(d) for d in node.decorator_list if self._unparse_safe(d)]

        symbol = SymbolInfo(
            name=class_qualname,
            short_name=node.name,
            symbol_type=SymbolType.CLASS,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            decorators=decorators,
        )
        self.symbols.append(symbol)

        # Push class context for methods
        prev_class = self._current_class
        prev_qualname = self._current_class_qualname
        self._current_class = node.name
        self._current_class_qualname = class_qualname

        self.generic_visit(node)

        # Restore class context
        self._current_class = prev_class
        self._current_class_qualname = prev_qualname

    def _process_function(self, node: ast.AST, is_async: bool = False):
        func_name = getattr(node, "name", "")
        if self._current_class:
            symbol_type = SymbolType.METHOD
            func_qualname = f"{self._current_class_qualname}.{func_name}"
            parent_symbol = self._current_class
        else:
            symbol_type = SymbolType.FUNCTION
            func_qualname = (
                f"{self.module_qualname}.{func_name}"
                if self.module_qualname
                else func_name
            )
            parent_symbol = None

        decorators = [self._unparse_safe(d) for d in getattr(node, "decorator_list", []) if self._unparse_safe(d)]
        parameters = self._extract_parameters(node.args)
        return_type = self._unparse_safe(getattr(node, "returns", None))

        # Inspect function body for function calls
        calls_found: List[str] = []
        for body_child in ast.walk(node):
            if isinstance(body_child, ast.Call):
                call_target = self._extract_call_name(body_child.func)
                calls_found.append(call_target)
                self.call_relationships.append(
                    CallRelationship(
                        caller=func_qualname,
                        callee=call_target,
                        file_path=self.file_path,
                        line_number=body_child.lineno,
                    )
                )

        symbol = SymbolInfo(
            name=func_qualname,
            short_name=func_name,
            symbol_type=symbol_type,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno) or node.lineno,
            docstring=ast.get_docstring(node),
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            calls=calls_found,
            parent_symbol=parent_symbol,
        )
        self.symbols.append(symbol)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node, is_async=False)
        # Avoid double visiting child nodes manually since we walked them for calls
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.visit(item)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node, is_async=True)
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.visit(item)


class ASTRepositoryAnalyzer:
    """Recursively parses a Python repository and extracts code intelligence."""

    def __init__(self, repo_path: str, ignore_patterns: Optional[List[str]] = None):
        self.repo_path = Path(repo_path).resolve()
        self.ignore_patterns = ignore_patterns or [
            ".git",
            "venv",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            "dist",
            "build",
            ".egg-info",
        ]

    def _should_ignore(self, path: Path) -> bool:
        parts = path.parts
        for pattern in self.ignore_patterns:
            if pattern in parts:
                return True
        return False

    def _file_to_module_qualname(self, file_path: Path) -> str:
        """Convert a relative python file path into a module dot-notation qualname."""
        try:
            rel = file_path.relative_to(self.repo_path)
            parts = list(rel.with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts.pop()
            return ".".join(parts)
        except Exception:
            return file_path.stem

    def parse_file(self, file_path: Path) -> Optional[Tuple[FileInfo, List[CallRelationship]]]:
        if not file_path.is_file() or file_path.suffix != ".py":
            return None

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return None

        line_count = len(content.splitlines())
        relative_path = str(file_path.relative_to(self.repo_path)).replace("\\", "/")
        module_qualname = self._file_to_module_qualname(file_path)

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            # Code might have invalid syntax; return basic file info with 0 symbols
            file_info = FileInfo(
                file_path=str(file_path).replace("\\", "/"),
                relative_path=relative_path,
                line_count=line_count,
                symbols=[],
                imports=[],
            )
            return file_info, []

        visitor = CodeVisitor(
            file_path=str(file_path).replace("\\", "/"),
            relative_path=relative_path,
            module_qualname=module_qualname,
        )
        visitor.visit(tree)

        file_info = FileInfo(
            file_path=str(file_path).replace("\\", "/"),
            relative_path=relative_path,
            line_count=line_count,
            symbols=visitor.symbols,
            imports=visitor.imports,
        )

        return file_info, visitor.call_relationships

    def analyze(self) -> RepoAnalysisResult:
        """Traverse the repository directory, parse all Python files, and aggregate intelligence."""
        if not self.repo_path.exists() or not self.repo_path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist or is not a directory: {self.repo_path}")

        files_info: List[FileInfo] = []
        all_call_relations: List[CallRelationship] = []

        total_lines = 0
        total_symbols = 0
        total_classes = 0
        total_functions = 0

        for root, dirs, files in os.walk(self.repo_path):
            current_dir = Path(root)
            if self._should_ignore(current_dir):
                dirs.clear()
                continue

            # Filter out ignored directories in-place to prevent walking into them
            dirs[:] = [d for d in dirs if not self._should_ignore(current_dir / d)]

            for file_name in files:
                if not file_name.endswith(".py"):
                    continue

                file_path = current_dir / file_name
                if self._should_ignore(file_path):
                    continue

                parsed = self.parse_file(file_path)
                if parsed:
                    file_info, call_rels = parsed
                    files_info.append(file_info)
                    all_call_relations.extend(call_rels)

                    total_lines += file_info.line_count
                    for sym in file_info.symbols:
                        total_symbols += 1
                        if sym.symbol_type == SymbolType.CLASS:
                            total_classes += 1
                        elif sym.symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD):
                            total_functions += 1

        summary = (
            f"Analyzed {len(files_info)} Python files ({total_lines} lines). "
            f"Found {total_classes} classes, {total_functions} functions/methods, "
            f"and {len(all_call_relations)} function call relationships."
        )

        return RepoAnalysisResult(
            repo_path=str(self.repo_path).replace("\\", "/"),
            total_files=len(files_info),
            total_lines=total_lines,
            total_symbols=total_symbols,
            total_classes=total_classes,
            total_functions=total_functions,
            files=files_info,
            call_graph=all_call_relations,
            summary=summary,
        )
