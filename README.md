# 🤖 AI Software Engineering Agent (SWE-Agent)

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-29%20Passed-brightgreen.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An autonomous, deterministic, and self-verifying AI Software Engineering Agent backend. Given an issue, the system parses the repository via **Abstract Syntax Trees (AST)**, constructs a **Repository Intelligence Graph**, formulates a human-approvable **Implementation Plan**, performs surgical code edits, verifies changes in a **sandboxed test environment**, self-repairs failures through an iterative reflection loop, and conducts an automated **Senior Code Review**.

---

## 🌟 Core Architecture

```
GitHub Issue / Feature Request
            │
            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Application Gateway               │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            ▼                                ▼
┌───────────────────────┐        ┌───────────────────────┐
│ AST Parser & Analysis │        │ Codebase Indexer      │
│ (Python `ast` module) │        │ (TF-IDF & Cosine RAG) │
└───────────┬───────────┘        └───────────┬───────────┘
            │                                │
            └───────────────┬────────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │ Repository Intelligence   │
              │ Graph (NetworkX DiGraph)  │
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │ Issue Planning Agent      │
              │ (Human-in-the-Loop Gate)  │
              └─────────────┬─────────────┘
                            │ [APPROVED]
                            ▼
              ┌───────────────────────────┐
              │ Surgical File & Git Tools │
              │ (AST Line-Span Replacer)  │
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │ Sandbox Test Runner       │
              │ (Isolated pytest process) │
              └─────────────┬─────────────┘
                            │
                 ┌──────────┴──────────┐
                 │                     │
              [PASS]                [FAIL]
                 │                     │
                 │                     ▼
                 │            ┌─────────────────┐
                 │            │ Debugger Agent  │
                 │            │ (Traceback loop)│
                 │            │ (Max 3 retries) │
                 │            └────────┬────────┘
                 │                     │ (Fix code)
                 │                     ▼
                 │            [Re-run Sandbox]
                 │                     │
                 └──────────┬──────────┘
                            ▼
              ┌───────────────────────────┐
              │ Senior Code Reviewer      │
              │ (Security & Performance)  │
              └─────────────┬─────────────┘
                            │
                            ▼
                Verified Pull Request
```

---

## 🚀 Key Differentiators

1. **Deterministic AST Static Analysis**: Zero-dependency AST visitor that extracts modules, classes, functions, exact line spans, decorators, type annotations, and docstrings without LLM hallucinations.
2. **Repository Intelligence Graph**: NetworkX directed graph tracking caller/callee hierarchies. Performs **Ripple Impact Analysis**: *"If I change function X, which upstream callers and unit tests are affected?"*
3. **AST-Enriched Codebase RAG**: Chunks code along exact function/class boundaries with enriched signature headers, powered by subword TF-IDF vectorization and cosine similarity.
4. **Human-in-the-Loop Planning Gate**: Automatically breaks down issues into structured Pydantic `ImplementationPlan` steps (`CREATE_FILE`, `MODIFY_SYMBOL`, `UPDATE_TESTS`, `RUN_VERIFICATION`) with human approval before code is touched.
5. **Surgical AST Code Editing**: Edits target functions by line span and validates Python syntax before writing to disk, automatically rolling back on syntax errors.
6. **Closed-Loop Self-Repair**: Executes test suites inside a protected sandbox with execution timeouts (30s) and reflects on failing tracebacks (capped at 3 iterations by a circuit breaker).
7. **Automated Senior Code Review**: Inspects unified git diffs for security vulnerabilities (`eval()`, hardcoded credentials), performance anti-patterns (N+1 queries), and outputs formatted PR descriptions.

---

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **API Framework**: FastAPI + Uvicorn
- **Data Validation**: Pydantic v2
- **Static Analysis**: Python `ast` + `inspect`
- **Graph Computing**: NetworkX
- **ML / Vector Search**: Scikit-Learn (`TfidfVectorizer`, Cosine Similarity) + NumPy
- **Version Control**: GitPython
- **Testing & Sandbox**: Pytest + Subprocess Sandbox

---

## 📁 Project Structure

```
AI-Software-Engineering-Agent/
├── app/
│   ├── main.py                    # FastAPI entrypoint, middleware & routing
│   ├── config.py                  # Pydantic Settings & environment variables
│   ├── api/
│   │   └── v1/
│   │       ├── repos.py           # AST analysis, graph impact & semantic search
│   │       ├── issues.py          # Issue planning & human approval gate
│   │       ├── tasks.py           # Sandbox verification & self-repair loop
│   │       └── review.py          # Code review audit & PR description generator
│   ├── core/
│   │   ├── ast_parser.py          # AST visitor & symbol/call extractor
│   │   ├── code_graph.py          # NetworkX repository dependency graph
│   │   ├── indexer.py             # Semantic AST code chunker & vector search
│   │   └── git_manager.py         # Git branch isolation, diffs & commits
│   ├── agents/
│   │   ├── planner.py             # Issue -> ImplementationPlan agent
│   │   ├── debugger.py            # Traceback reflection & self-repair agent
│   │   └── reviewer.py            # Senior code review & security auditor
│   ├── tools/
│   │   ├── file_tools.py          # Surgical AST replacement & file IO
│   │   └── sandbox_runner.py      # Subprocess pytest runner with timeouts
│   └── models/
│       └── schemas.py             # Pydantic data schemas
├── tests/                         # 29 Comprehensive unit & integration tests
├── PROJECT.md                     # Deep architectural specification
├── pyproject.toml                 # Package dependencies and configuration
└── .env.example                   # Environment configuration template
```

---

## ⚡ Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/UndelaNandini/AI-Software-Engineering-Agent.git
cd AI-Software-Engineering-Agent
```

### 2. Install Dependencies
```bash
python -m pip install -e .
python -m pip install pytest numpy scikit-learn
```

### 3. Start the FastAPI Server
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** to view the interactive Swagger API documentation.

### 4. Run the Test Suite
```bash
python -m pytest -v
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/repos/analyze` | Deterministically parse Python AST and return symbol tree |
| `POST` | `/api/v1/repos/impact` | Compute upstream ripple impact for a target symbol |
| `POST` | `/api/v1/repos/symbols/search` | Exact & substring symbol search across repository |
| `POST` | `/api/v1/repos/search/semantic` | Semantic natural language code search via ML vectorizer |
| `POST` | `/api/v1/issues/plan` | Generate a structured implementation plan from an issue |
| `GET` | `/api/v1/issues/plans/{id}` | Retrieve generated implementation plan |
| `PATCH`| `/api/v1/issues/plans/{id}` | **Human Gate**: Approve, reject, or modify plan steps |
| `POST` | `/api/v1/tasks/verify` | Execute test suite in isolated sandbox with timeout limits |
| `POST` | `/api/v1/tasks/repair` | Run iterative self-repair loop on failing code (max 3 tries) |
| `POST` | `/api/v1/review/diff` | Audit git diff for security and performance anti-patterns |
| `POST` | `/api/v1/review/pr` | Generate verified GitHub Pull Request Markdown description |

---

## 📄 License
This project is licensed under the MIT License.
