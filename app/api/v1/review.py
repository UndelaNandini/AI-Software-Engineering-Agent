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
