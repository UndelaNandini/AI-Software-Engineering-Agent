from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.reviewer import CodeReviewReport, code_reviewer
from app.core.git_manager import GitManager

router = APIRouter()


class ReviewDiffRequest(BaseModel):
    repo_path: str = Field(description="Path to repository")
    diff_text: Optional[str] = Field(default=None, description="Optional explicit diff text")


class PRDescriptionRequest(BaseModel):
    repo_path: str = Field(description="Path to repository")
    issue_title: str
    issue_description: str
    tests_passed: bool = True


class PRDescriptionResponse(BaseModel):
    markdown_body: str


@router.post(
    "/diff",
    response_model=CodeReviewReport,
    status_code=status.HTTP_200_OK,
    summary="Review Code Diff",
    description="Analyzes unified git diff for security vulnerabilities, performance anti-patterns, and code quality.",
)
async def review_diff(request: ReviewDiffRequest) -> CodeReviewReport:
    target_path = Path(request.repo_path).resolve()
    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {request.repo_path}",
        )

    diff_content = request.diff_text
    if diff_content is None:
        diff_content = GitManager.get_diff(target_path)

    return code_reviewer.review_diff(diff_content)


@router.post(
    "/pr",
    response_model=PRDescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Pull Request Description",
    description="Generates GitHub-ready Markdown PR description with test results and review checklist.",
)
async def generate_pr_description(request: PRDescriptionRequest) -> PRDescriptionResponse:
    target_path = Path(request.repo_path).resolve()
    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository not found: {request.repo_path}",
        )

    diff_content = GitManager.get_diff(target_path)
    body = code_reviewer.generate_pr_description(
        issue_title=request.issue_title,
        issue_description=request.issue_description,
        diff_text=diff_content,
        tests_passed=request.tests_passed,
    )
    return PRDescriptionResponse(markdown_body=body)


class PublishPRRequest(BaseModel):
    owner: str = Field(description="GitHub repository owner/organization, e.g. 'UndelaNandini'")
    repo: str = Field(description="GitHub repository name, e.g. 'AI-Software-Engineering-Agent'")
    head_branch: str = Field(description="Branch containing the verified changes, e.g. 'agent/feature-123'")
    base_branch: str = Field(default="main", description="Target base branch")
    title: str = Field(description="PR title")
    body: Optional[str] = Field(default=None, description="Optional custom PR description")
    github_token: Optional[str] = Field(default=None, description="Optional GitHub Personal Access Token")
    draft: bool = Field(default=False, description="Open as draft PR")


from app.core.github_publisher import GitHubPRCreationResult, GitHubPRPublisher

@router.post(
    "/publish-pr",
    response_model=GitHubPRCreationResult,
    status_code=status.HTTP_200_OK,
    summary="Publish Live GitHub Pull Request",
    description="Opens a real Pull Request directly on GitHub using the GitHub REST API v3.",
)
async def publish_pull_request(request: PublishPRRequest) -> GitHubPRCreationResult:
    publisher = GitHubPRPublisher(github_token=request.github_token)
    
    pr_body = request.body or (
        f"## 🚀 Automated Pull Request: {request.title}\n\n"
        f"Verified changes generated autonomously by the **AI Software Engineering Agent**.\n"
    )

    result = await publisher.create_pull_request(
        owner=request.owner,
        repo=request.repo,
        title=request.title,
        body=pr_body,
        head_branch=request.head_branch,
        base_branch=request.base_branch,
        draft=request.draft,
    )
    return result

