from typing import Dict, List, Optional
import re
from pydantic import BaseModel, Field

from app.core.git_manager import GitManager


class ReviewFinding(BaseModel):
    category: str = Field(description="SECURITY, PERFORMANCE, or CODE_QUALITY")
    severity: str = Field(description="INFO, WARNING, or CRITICAL")
    message: str
    line_snippet: Optional[str] = None


class CodeReviewReport(BaseModel):
    security_verdict: str = Field(description="PASS, WARNING, or FAIL")
    performance_verdict: str = Field(description="PASS, WARNING, or FAIL")
    quality_verdict: str = Field(description="GOOD, ACCEPTABLE, or NEEDS_IMPROVEMENT")
    findings: List[ReviewFinding] = Field(default_factory=list)
    summary: str
    approved: bool


class CodeReviewer:
    """Automated Senior Code Reviewer that evaluates git diffs and code patches."""

    def review_diff(self, diff_text: str) -> CodeReviewReport:
        findings: List[ReviewFinding] = []

        if not diff_text.strip():
            return CodeReviewReport(
                security_verdict="PASS",
                performance_verdict="PASS",
                quality_verdict="GOOD",
                findings=[],
                summary="No changes detected in git diff.",
                approved=True,
            )

        # 1. Security Checks
        security_verdict = "PASS"
        dangerous_patterns = [
            (r"eval\(", "Use of eval() detected, which can lead to arbitrary code execution.", "CRITICAL"),
            (r"exec\(", "Use of exec() detected, which can lead to arbitrary code execution.", "CRITICAL"),
            (r"(api_key|secret|password|auth_token)\s*=\s*['\"][^'\"]{8,}['\"]", "Possible hardcoded secret or API credential detected.", "CRITICAL"),
        ]

        for pattern, msg, severity in dangerous_patterns:
            matches = re.finditer(pattern, diff_text, re.IGNORECASE)
            for m in matches:
                findings.append(
                    ReviewFinding(
                        category="SECURITY",
                        severity=severity,
                        message=msg,
                        line_snippet=m.group(0),
                    )
                )
                security_verdict = "FAIL" if severity == "CRITICAL" else "WARNING"

        # 2. Performance Checks
        performance_verdict = "PASS"
        perf_patterns = [
            (r"for\s+.*:\s*\n.*\.(query|execute|fetch|find)\(", "Potential N+1 database query inside a loop.", "WARNING"),
        ]
        for pattern, msg, severity in perf_patterns:
            matches = re.finditer(pattern, diff_text)
            for m in matches:
                findings.append(
                    ReviewFinding(
                        category="PERFORMANCE",
                        severity=severity,
                        message=msg,
                        line_snippet=m.group(0),
                    )
                )
                performance_verdict = "WARNING"

        # 3. Code Quality Checks
        quality_verdict = "GOOD"
        if len(findings) > 2:
            quality_verdict = "NEEDS_IMPROVEMENT"
        elif len(findings) > 0:
            quality_verdict = "ACCEPTABLE"

        approved = (security_verdict != "FAIL")

        summary = (
            f"Review completed with {len(findings)} findings. "
            f"Security: {security_verdict}, Performance: {performance_verdict}, Quality: {quality_verdict}."
        )

        return CodeReviewReport(
            security_verdict=security_verdict,
            performance_verdict=performance_verdict,
            quality_verdict=quality_verdict,
            findings=findings,
            summary=summary,
            approved=approved,
        )

    def generate_pr_description(
        self,
        issue_title: str,
        issue_description: str,
        diff_text: str,
        tests_passed: bool = True,
    ) -> str:
        """Generates a GitHub-flavored Markdown PR description."""
        review = self.review_diff(diff_text)
        status_badge = "✅ Verified & Passing" if tests_passed else "❌ Tests Failing"

        return f"""## 🚀 PR: {issue_title}

### 📋 Overview & Motivation
{issue_description}

### 🧪 Verification & Test Status
- **Test Status**: {status_badge}
- **Security Audit**: `{review.security_verdict}`
- **Performance Audit**: `{review.performance_verdict}`
- **Code Quality**: `{review.quality_verdict}`

### 🔍 Automated Code Review Summary
{review.summary}

### 📝 Key Changes in this Diff
```diff
{diff_text[:1500] if diff_text else "No diff available."}
```

---
*Generated autonomously by [AI Software Engineering Agent](https://github.com/UndelaNandini/AI-Software-Engineering-Agent).*
"""


code_reviewer = CodeReviewer()
