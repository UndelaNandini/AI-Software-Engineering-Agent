from pathlib import Path
import pytest
from app.core.git_manager import GitManager


def test_git_manager_lifecycle(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # 1. Initialize repo
    repo = GitManager.get_or_init_repo(repo_dir)
    assert (repo_dir / ".git").exists()

    # 2. Create branch
    branch_name = "agent/feature-123"
    active_branch = GitManager.create_feature_branch(repo_dir, branch_name)
    assert active_branch == branch_name
    assert GitManager.get_current_branch(repo_dir) == branch_name

    # 3. Modify a file and check diff
    code_file = repo_dir / "app.py"
    code_file.write_text("x = 42\n", encoding="utf-8")

    commit_sha = GitManager.commit_all(repo_dir, "Add app.py")
    assert commit_sha is not None
    assert len(commit_sha) == 40
