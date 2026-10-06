# AI Software Engineering Agent (SWE-Agent)

> An autonomous, deterministic, and sandboxed AI software engineering agent powered by Python, FastAPI, AST-based Repository Intelligence Graphs, and a closed-loop self-repair verification engine.

---

## 1. Executive Summary & Vision

Software engineering is far more than generating isolated snippets of code. In real production environments, over 80% of an engineer's time is spent exploring unfamiliar repositories, tracing symbol dependencies, interpreting architecture patterns, verifying changes against existing test suites, and debugging regressions.

The **AI Software Engineering Agent** solves this end-to-end lifecycle. Given a GitHub issue or feature request, the system:
1. Ingests and deterministically parses the repository using Abstract Syntax Trees (AST).
2. Builds a **Repository Intelligence Graph** linking functions, classes, callers, and callees.
3. Formulates a structured, human-approvable **Implementation Plan**.
4. Modifies the codebase using AST-aware and diff-based editing tools.
5. Executes the test suite in an **isolated sandbox environment**.
6. Enters a **self-repair loop** (max 3 retries) on test or lint failure.
7. Performs an automated **Senior Code Review** checking for security vulnerabilities, performance regressions, and style.
8. Produces a verified, human-ready Git Pull Request or unified patch.

---

## 2. Project Scope

A clearly defined scope is critical to avoid the common trap of building an unfocused "agent chat loop" that burns tokens and fails in real-world repositories.

### In-Scope (Core Deliverables)

| Component | In-Scope Features |
| :--- | :--- |
| **Language Target** | **Python repositories** (initially), leveraging Python's native `ast` module and `pytest` testing ecosystem. Extensible via tree-sitter in later phases. |
| **Static Code Intelligence** | AST parsing for functions, classes, decorators, docstrings, imports, and calls. Call-graph generation and impact analysis ("If I edit function X, what breaks?"). |
| **Hybrid Retrieval** | Semantic search (vector embeddings via `pgvector`) combined with deterministic symbol lookups and call-graph traversal. |
| **Planning & Verification** | Structured issue decomposition into a validated Pydantic `ImplementationPlan` with human-in-the-loop approval before code modification. |
| **Sandboxed Execution** | Safe execution of test commands (`pytest`, `ruff`, `mypy`) inside isolated Docker containers or secure subprocess sandboxes. |
| **Autonomous Self-Repair** | Automatic ingestion of tracebacks and error messages with an iterative repair loop capped at 3 attempts. |
| **Backend & APIs** | Production-ready FastAPI service exposing REST endpoints and real-time WebSockets for live agent execution telemetry. |
| **Benchmarking & Evaluation** | Standardized evaluation harness inspired by SWE-bench (pass rate, repair efficiency, token usage, cost per task). |

### Out-of-Scope (Deferred to Future Versions)

- **Autonomous Production Merging**: The agent *never* merges PRs directly into main branches without human review.
- **Arbitrary Polyglot Support in v1**: Non-Python languages (e.g., C++, Rust, TypeScript) are deferred until tree-sitter integration in v1.2+.
- **Zero-Sandboxed Host Execution**: Untrusted code will never be run directly on the host machine.
- **Indefinite Autonomous Loops**: Infinite agent loops are strictly forbidden via token/step circuit breakers.

---

## 3. High-Level Architecture

```
                                  ┌───────────────────────┐
                                  │   Developer / Web UI  │
                                  │   or GitHub Webhook   │
                                  └───────────┬───────────┘
                                              │ REST / WebSocket
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI Gateway Layer                                   │
│                                                                                         │
│   [/api/v1/repos]           [/api/v1/issues]          [/api/v1/tasks]     [/api/v1/review]│
│   - Clone & Ingest          - Plan Generation         - Execution Loop    - Diff & Review │
└───────┬───────────────────────────────┬─────────────────────────┬───────────────────┬───┘
        │                               │                         │                   │
        ▼                               ▼                         ▼                   ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────┐  ┌───────────┐
│ AST & Graph Engine   │    │ Planning Engine      │    │ Coding & Tool    │  │ Review    │
│                      │    │                      │    │ Engine           │  │ Engine    │
│ - Python AST visitor │    │ - Context Assembler  │    │ - AST Symbol     │  │ - Diff    │
│ - Symbol Table       │    │ - Pydantic Plan      │    │   Replacer       │  │   Analysis│
│ - NetworkX Graph     │    │ - Human Gate         │    │ - Git Worktree   │  │ - Security│
└───────┬──────────────┘    └───────────┬──────────┘    └─────────┬────────┘  │   Checks  │
        │                               │                         │           └─────┬─────┘
        │                               ▼                         │                 │
        │                    ┌─────────────────────┐              │                 │
        │                    │ Hybrid Vector RAG   │              │                 │
        │                    │ (PostgreSQL/pgvector│              │                 │
        │                    └─────────────────────┘              │                 │
        │                                                         ▼                 │
        │                                              ┌────────────────────┐       │
        │                                              │ Sandboxed Runner   │       │
        │                                              │ (Docker / Pytest)  │       │
        │                                              └──────────┬─────────┘       │
        │                                                         │                 │
        │                                                  Pass / Fail Trace        │
        │                                                         │                 │
        │                                                         ▼                 │
        │                                              ┌────────────────────┐       │
        │                                              │ Debug / Repair     │       │
        │                                              │ Loop (Max 3 tries) ◄───────┘
        │                                              └────────────────────┘
        ▼                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               Persistence & State Layer                                 │
│                   PostgreSQL (Relational + pgvector) | Redis (Job Queue)               │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Progressive Implementation Milestones

### Milestone 1: Repository AST & Static Intelligence (`v0.1`)
- **Objective**: Deterministic codebase parsing without relying on LLMs.
- **Capabilities**:
  - Traverse Python repositories and parse all `.py` files using `ast`.
  - Extract symbols: modules, classes, methods, functions, docstrings, decorators, and line ranges.
  - Parse imports (`ast.Import`, `ast.ImportFrom`) to trace file-level dependencies.
  - Detect function invocations (`ast.Call`) to map inter-function call relationships.
- **FastAPI Endpoints**:
  - `POST /api/v1/repos/analyze`: Accepts a local path or repository URI and returns a comprehensive symbol tree.

### Milestone 2: Repository Intelligence Graph & Search (`v0.2` - `v0.3`)
- **Objective**: Precision code retrieval blending static graphs with semantic vectors.
- **Capabilities**:
  - Construct a directed graph (`NetworkX`) of callers and callees.
  - Impact Analysis: Given a function, compute all dependent files and tests that might be affected.
  - Semantic Chunking: Chunk code cleanly at function/class boundaries with surrounding context.
  - Store and search chunks with PostgreSQL `pgvector`.
- **FastAPI Endpoints**:
  - `GET /api/v1/repos/{repo_id}/symbols`: Query symbols by name or scope.
  - `GET /api/v1/repos/{repo_id}/impact`: Retrieve impact graph for a specific symbol.
  - `POST /api/v1/repos/{repo_id}/search`: Hybrid search across symbols and vector embeddings.

### Milestone 3: Planning Agent with Human-in-the-Loop (`v0.4` - `v0.5`)
- **Objective**: Translate issues into concrete, validated engineering plans before modifying code.
- **Capabilities**:
  - Ingest GitHub issue descriptions and relevant repository context.
  - LLM generates a structured `ImplementationPlan` (Pydantic schema).
  - List of affected files, proposed modifications, and target test cases.
  - Interactive approval or modification of the plan by a human developer.
- **FastAPI Endpoints**:
  - `POST /api/v1/issues/plan`: Generate an implementation plan.
  - `PATCH /api/v1/issues/plans/{plan_id}`: Approve or modify steps.

### Milestone 4: Coding Agent & Isolated Git Tools (`v0.6`)
- **Objective**: Programmatic modification of code with surgical accuracy.
- **Capabilities**:
  - Autonomous tool execution: `read_file`, `read_symbol`, `edit_symbol`, `create_file`, `git_diff`.
  - Branch isolation: Automatically checkout feature branch `swe-agent/issue-{id}`.
  - AST-aware symbol replacement to eliminate hallucinated indentation or partial edits.
- **FastAPI Endpoints**:
  - `POST /api/v1/tasks/execute`: Trigger coding agent on an approved plan.

### Milestone 5: Sandboxed Test Runner & Self-Repair Loop (`v0.7` - `v0.8`)
- **Objective**: Verification and automated bug correction.
- **Capabilities**:
  - Docker sandbox executes `pytest --json-report`.
  - Failure analyzer extracts traceback, failure assertion, and error location.
  - Debugging Agent reflects on the failure and generates surgical fixes.
  - Hard limit of 3 repair attempts with circuit-breaker on token expenditure.
- **FastAPI Endpoints**:
  - `WS /api/v1/tasks/{task_id}/stream`: Stream real-time agent thoughts, edits, and test runs.
  - `GET /api/v1/tasks/{task_id}/status`: Poll current execution state.

### Milestone 6: Senior Code Reviewer & PR Automation (`v0.9` - `v1.0`)
- **Objective**: Production gatekeeping and pull request generation.
- **Capabilities**:
  - Independent reviewer agent evaluates the final `git diff`.
  - Checks for security vulnerabilities, N+1 query patterns, and regressions.
  - Generates a verified Pull Request via GitHub API with execution metrics.
- **FastAPI Endpoints**:
  - `GET /api/v1/tasks/{task_id}/diff`: Inspect generated patch.
  - `POST /api/v1/tasks/{task_id}/create-pr`: Push branch and open Pull Request.

---

## 5. Technology Stack

| Category | Technology | Rationale |
| :--- | :--- | :--- |
| **Core Language** | Python 3.11+ | Native AST manipulation, extensive LLM ecosystem, robust typing. |
| **API Framework** | FastAPI + Uvicorn | Async performance, auto-generated OpenAPI documentation, native WebSocket support. |
| **Data Validation** | Pydantic v2 | High-speed data parsing, strict typing for LLM structured outputs. |
| **Static Code Parsing** | Python `ast` + `inspect` | Zero-dependency, deterministic syntactic analysis of Python codebases. |
| **Graph Computing** | `NetworkX` | High-performance graph traversal for caller/callee impact analysis. |
| **Database & Vector Search** | PostgreSQL + `pgvector` | Unified relational and vector database; eliminates multi-database bloat. |
| **Execution Sandboxing** | Docker SDK for Python | Secure, isolated execution of arbitrary code and test suites. |
| **Git Operations** | `GitPython` / Native Git CLI | Reliable branch, diff, worktree, and patch management. |
| **LLM Orchestration** | LiteLLM / LangChain / Native | Model-agnostic switching between OpenAI, Anthropic, and Gemini models. |

---

## 6. Project Directory Structure

```
ai-swe-agent/
├── PROJECT.md                     # Project specification and scope (this file)
├── pyproject.toml                 # Package dependencies and configuration
├── .env.example                   # Environment variable template
├── app/
│   ├── main.py                    # FastAPI application initialization & routes
│   ├── config.py                  # Pydantic Settings (API keys, DB config, limits)
│   ├── api/
│   │   ├── v1/
│   │   │   ├── repos.py           # Repo ingestion, symbol queries, impact graph
│   │   │   ├── issues.py          # Issue planning & approval endpoints
│   │   │   ├── tasks.py           # Agent execution and WebSocket streaming
│   │   │   └── review.py          # Diffs, reviews, and PR generation
│   │   └── deps.py                # Database and service dependency injection
│   ├── core/
│   │   ├── ast_parser.py          # Python AST visitor and symbol extractor
│   │   ├── code_graph.py          # NetworkX repository intelligence graph
│   │   ├── git_manager.py         # Git clone, branch, patch, and diff utilities
│   │   └── indexer.py             # Code chunker and vector embedding pipeline
│   ├── agents/
│   │   ├── orchestrator.py        # Master state machine workflow controller
│   │   ├── planner.py             # Issue -> Pydantic implementation plan
│   │   ├── coder.py               # Tool-calling coding agent
│   │   ├── tester.py              # Test runner and traceback parser
│   │   ├── debugger.py            # Traceback analyzer & self-repair loop
│   │   └── reviewer.py            # Code quality and security review agent
│   ├── tools/
│   │   ├── file_tools.py          # Surgical read/edit/write operations
│   │   ├── search_tools.py        # Symbol lookup and hybrid search
│   │   └── sandbox_runner.py      # Docker / subprocess isolated test executor
│   ├── models/
│   │   ├── database.py            # SQLAlchemy / SQLModel models
│   │   └── schemas.py             # Pydantic request/response & agent schemas
│   └── workers/
│       └── task_queue.py          # Background task dispatching
├── docker/
│   ├── Dockerfile.api             # FastAPI application container
│   └── Dockerfile.sandbox         # Hardened sandbox for executing repo test suites
└── tests/
    ├── test_ast_parser.py         # AST symbol & call extraction unit tests
    ├── test_code_graph.py         # Graph traversal and impact analysis tests
    ├── test_file_tools.py         # Tool verification tests
    └── test_planner.py            # Plan generation tests
```

---

## 7. Metrics & Evaluation Framework

To validate that the agent performs like a senior software engineer, all runs are tracked against quantitative metrics:

1. **Task Resolution Rate**: Percentage of issues resolved with all tests passing.
2. **Self-Repair Efficiency**: Percentage of initially failing tests that were corrected within 3 repair attempts.
3. **Diff Precision**: Ratio of relevant code changed versus extraneous modified lines.
4. **Token & Cost Efficiency**: Average tokens consumed and API cost per resolved issue.
5. **Review Detection Rate**: Percentage of deliberate vulnerabilities (e.g., SQLi, N+1 queries) caught by the Code Reviewer agent.

---

## 8. Definition of Done for Milestone 1

Milestone 1 is complete when:
1. `app/core/ast_parser.py` parses arbitrary Python projects and extracts:
   - All modules, classes, methods, and functions.
   - Exact line numbers (start and end).
   - Docstrings and function signatures.
   - Module imports and inter-symbol function calls.
2. The FastAPI endpoint `POST /api/v1/repos/analyze` accepts a target directory and returns the full JSON symbol tree and call graph.
3. Unit tests in `tests/test_ast_parser.py` pass with 100% test coverage on sample codebases.
