import os
from typing import Dict, Optional
import httpx
from pydantic import BaseModel, Field

from app.config import get_settings


class GitHubPRCreationResult(BaseModel):
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_title: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: Optional[str] = None
    message: str


class GitHubPRPublisher:
    """Creates remote branches, pushes changes, and publishes live Pull Requests via GitHub REST API."""

    def __init__(self, github_token: Optional[str] = None):
        self.settings = get_settings()
        self.token = github_token or os.environ.get("GITHUB_TOKEN")

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False,
    ) -> GitHubPRCreationResult:
        """Call GitHub REST API v3 to create a Pull Request."""
        if not self.token:
            return GitHubPRCreationResult(
                success=False,
                message="GitHub token not configured. Set GITHUB_TOKEN environment variable or pass token.",
            )

        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(api_url, headers=headers, json=payload)

                if response.status_code == 201:
                    data = response.json()
                    return GitHubPRCreationResult(
                        success=True,
                        pr_number=data.get("number"),
                        pr_url=data.get("html_url"),
                        pr_title=data.get("title"),
                        head_branch=head_branch,
                        base_branch=base_branch,
                        message=f"Pull Request #{data.get('number')} successfully created!",
                    )
                else:
                    error_data = response.json()
                    err_msg = error_data.get("message", response.text)
                    return GitHubPRCreationResult(
                        success=False,
                        head_branch=head_branch,
                        base_branch=base_branch,
                        message=f"GitHub API Error ({response.status_code}): {err_msg}",
                    )

            except Exception as e:
                return GitHubPRCreationResult(
                    success=False,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    message=f"Network error communicating with GitHub API: {str(e)}",
                )


github_pr_publisher = GitHubPRPublisher()
