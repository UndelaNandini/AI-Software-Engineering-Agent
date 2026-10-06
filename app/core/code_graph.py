from typing import Any, Dict, List, Optional, Set
import networkx as nx

from app.models.schemas import RepoAnalysisResult, SymbolInfo, SymbolType


class CodeGraph:
    """Directed graph representing repository architecture, symbol dependencies, and call hierarchies."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._symbol_lookup: Dict[str, SymbolInfo] = {}

    def build_from_analysis(self, analysis: RepoAnalysisResult) -> "CodeGraph":
        """Populates nodes and edges from AST analysis results."""
        self.graph.clear()
        self._symbol_lookup.clear()

        # 1. Add file nodes and symbol nodes
        for file_info in analysis.files:
            file_node_id = f"file::{file_info.relative_path}"
            self.graph.add_node(
                file_node_id,
                node_type="file",
                relative_path=file_info.relative_path,
                line_count=file_info.line_count,
            )

            for sym in file_info.symbols:
                sym_node_id = f"symbol::{sym.name}"
                self._symbol_lookup[sym.name] = sym
                self._symbol_lookup[sym.short_name] = sym  # Also index short name for flexible matching

                self.graph.add_node(
                    sym_node_id,
                    node_type="symbol",
                    name=sym.name,
                    short_name=sym.short_name,
                    symbol_type=sym.symbol_type.value,
                    file_path=sym.file_path,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    docstring=sym.docstring,
                )

                # Edge: File contains symbol
                self.graph.add_edge(file_node_id, sym_node_id, relation="CONTAINS")

                # Edge: Class contains method
                if sym.parent_symbol:
                    # Look for parent class node
                    parent_node_id = f"symbol::{sym.parent_symbol}"
                    # Check if qualified class exists in graph
                    for candidate_id in self.graph.nodes:
                        if candidate_id.startswith("symbol::") and candidate_id.endswith(f".{sym.parent_symbol}"):
                            parent_node_id = candidate_id
                            break
                    self.graph.add_edge(parent_node_id, sym_node_id, relation="CONTAINS")

        # 2. Add function call edges
        for rel in analysis.call_graph:
            caller_node_id = f"symbol::{rel.caller}"
            # Callee may be short name or fully qualified or attribute call like 'self.repo.find'
            callee_target = rel.callee.split(".")[-1]
            callee_node_id = f"symbol::{rel.callee}"

            # If exact callee node not in graph, look for matching short name
            if callee_node_id not in self.graph:
                matched_id = None
                for node_id, data in self.graph.nodes(data=True):
                    if data.get("node_type") == "symbol" and data.get("short_name") == callee_target:
                        matched_id = node_id
                        break
                if matched_id:
                    callee_node_id = matched_id

            # Add CALLS edge
            self.graph.add_edge(
                caller_node_id,
                callee_node_id,
                relation="CALLS",
                file_path=rel.file_path,
                line_number=rel.line_number,
            )

        return self

    def find_callers(self, target_symbol_name: str) -> List[Dict[str, Any]]:
        """Return all functions/methods that directly call the target symbol."""
        callers: List[Dict[str, Any]] = []
        target_node = self._resolve_node_id(target_symbol_name)
        if not target_node or target_node not in self.graph:
            return callers

        # Predecessors with 'CALLS' relationship
        for pred in self.graph.predecessors(target_node):
            edge_data = self.graph.get_edge_data(pred, target_node)
            if edge_data and edge_data.get("relation") == "CALLS":
                node_data = self.graph.nodes[pred]
                callers.append(
                    {
                        "symbol": node_data.get("name", pred),
                        "file_path": node_data.get("file_path"),
                        "line_number": edge_data.get("line_number"),
                    }
                )
        return callers

    def find_callees(self, source_symbol_name: str) -> List[Dict[str, Any]]:
        """Return all functions/methods called by the source symbol."""
        callees: List[Dict[str, Any]] = []
        source_node = self._resolve_node_id(source_symbol_name)
        if not source_node or source_node not in self.graph:
            return callees

        for succ in self.graph.successors(source_node):
            edge_data = self.graph.get_edge_data(source_node, succ)
            if edge_data and edge_data.get("relation") == "CALLS":
                node_data = self.graph.nodes[succ]
                callees.append(
                    {
                        "symbol": node_data.get("name", succ),
                        "file_path": node_data.get("file_path"),
                        "line_number": edge_data.get("line_number"),
                    }
                )
        return callees

    def get_impact_radius(self, symbol_name: str, max_depth: int = 3) -> Dict[str, Any]:
        """Compute the ripple impact of modifying a symbol (all upstream callers and tests)."""
        target_node = self._resolve_node_id(symbol_name)
        if not target_node or target_node not in self.graph:
            return {
                "target": symbol_name,
                "found": False,
                "impacted_symbols": [],
                "impacted_files": [],
                "impacted_tests": [],
            }

        # Transitive callers via reverse BFS/ancestors
        reversed_graph = self.graph.reverse()
        visited: Set[str] = set()
        queue = [(target_node, 0)]

        impacted_symbols: List[Dict[str, Any]] = []
        impacted_files: Set[str] = set()
        impacted_tests: Set[str] = set()

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            if current != target_node:
                data = self.graph.nodes.get(current, {})
                if data.get("node_type") == "symbol":
                    name = data.get("name", current.replace("symbol::", ""))
                    impacted_symbols.append({"symbol": name, "depth": depth, "file": data.get("file_path")})
                    if data.get("file_path"):
                        impacted_files.add(data.get("file_path"))
                        if "test" in str(data.get("file_path")).lower():
                            impacted_tests.add(data.get("file_path"))

            # Next ancestors in reversed graph
            for succ in reversed_graph.successors(current):
                edge_data = reversed_graph.get_edge_data(current, succ)
                if edge_data and edge_data.get("relation") == "CALLS":
                    if succ not in visited:
                        queue.append((succ, depth + 1))

        return {
            "target": symbol_name,
            "found": True,
            "impacted_symbols": impacted_symbols,
            "impacted_files": sorted(list(impacted_files)),
            "impacted_tests": sorted(list(impacted_tests)),
            "total_impacted_symbols": len(impacted_symbols),
        }

    def _resolve_node_id(self, symbol_name: str) -> Optional[str]:
        exact_id = f"symbol::{symbol_name}"
        if exact_id in self.graph:
            return exact_id

        # Search by suffix or short name
        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == "symbol":
                if data.get("short_name") == symbol_name or data.get("name", "").endswith(f".{symbol_name}"):
                    return node_id
        return None

    def get_graph_stats(self) -> Dict[str, int]:
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
        }
