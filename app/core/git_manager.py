from pathlib import Path
from typing import Optional
import git


class GitManager:
    """Manages Git branch isolation, diff generation, and commits."""

    @staticmethod
    def get_or_init_repo(repo_path: Path) -> git.Repo:
        path = Path(repo_path).resolve()
        try:
            return git.Repo(path)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            repo = git.Repo.init(path)
            # Create an initial commit if repository is completely empty
            readme = path / "README.md"
            if not readme.exists():
                readme.write_text("# Project Repository\n", encoding="utf-8")
            repo.index.add(["README.md"])
            repo.index.commit("Initial repository commit")
            return repo

    @staticmethod
    def create_feature_branch(repo_path: Path, branch_name: str) -> str:
        """Create and checkout an isolated feature branch for the agent task."""
        repo = GitManager.get_or_init_repo(repo_path)
        try:
            # Check if branch exists
            if branch_name in [b.name for b in repo.branches]:
                repo.git.checkout(branch_name)
            else:
                repo.git.checkout("-b", branch_name)
            return branch_name
        except Exception as e:
            raise RuntimeError(f"Failed to create Git branch '{branch_name}': {e}")

    @staticmethod
    def get_diff(repo_path: Path) -> str:
        """Returns the unified diff of unstaged and staged changes."""
        repo = GitManager.get_or_init_repo(repo_path)
        try:
            return repo.git.diff()
        except Exception:
            return ""

    @staticmethod
    def commit_all(repo_path: Path, message: str) -> Optional[str]:
        """Stages all modified files and creates a commit."""
        repo = GitManager.get_or_init_repo(repo_path)
        try:
            repo.git.add(A=True)
            if repo.is_dirty() or repo.untracked_files:
                commit = repo.index.commit(message)
                return commit.hexsha
            return None
        except Exception as e:
            raise RuntimeError(f"Git commit failed: {e}")

    @staticmethod
    def get_current_branch(repo_path: Path) -> str:
        repo = GitManager.get_or_init_repo(repo_path)
        try:
            return repo.active_branch.name
        except Exception:
            return "detached"

    @staticmethod
    def push_branch(repo_path: Path, branch_name: str, remote_name: str = "origin") -> bool:
        """Pushes branch to remote."""
        repo = GitManager.get_or_init_repo(repo_path)
        try:
            repo.git.push(remote_name, branch_name, set_upstream=True)
            return True
        except Exception as e:
            raise RuntimeError(f"Git push failed: {e}")

