import json
import logging
from typing import Any, Dict, List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Multi-provider LLM interface powered by LiteLLM with offline fallback."""

    def __init__(self):
        self.settings = get_settings()

    def is_configured(self) -> bool:
        """Check if any LLM API key is present in environment."""
        return bool(
            self.settings.OPENAI_API_KEY
            or self.settings.GEMINI_API_KEY
            or self.settings.ANTHROPIC_API_KEY
        )

    def _resolve_model(self) -> str:
        if self.settings.GEMINI_API_KEY:
            return "gemini/gemini-2.0-flash"
        if self.settings.OPENAI_API_KEY:
            return self.settings.DEFAULT_MODEL
        if self.settings.ANTHROPIC_API_KEY:
            return "claude-3-5-sonnet-20241022"
        return "gpt-4o"

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        response_format: Optional[Dict] = None,
    ) -> Optional[str]:
        """Send completion request to configured LLM provider."""
        if not self.is_configured():
            logger.info("No LLM API keys configured; using deterministic engine.")
            return None

        try:
            import litellm

            model = self._resolve_model()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = litellm.completion(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"LLM call failed ({e}); falling back to deterministic engine.")
            return None

    def plan_issue(self, issue_title: str, issue_description: str, code_context: str) -> Optional[Dict]:
        """Ask LLM to produce a structured plan for the given issue and code context."""
        system_prompt = (
            "You are a Principal Software Engineer. Analyze the issue and code context. "
            "Output JSON with keys: 'summary' (str), 'steps' (list of objects with 'step_number', "
            "'action' (CREATE_FILE|MODIFY_SYMBOL|UPDATE_TESTS|RUN_VERIFICATION), 'target_file', "
            "'target_symbol', 'instruction'), and 'risk_assessment' (str)."
        )
        user_prompt = (
            f"ISSUE TITLE: {issue_title}\n\n"
            f"ISSUE DESCRIPTION: {issue_description}\n\n"
            f"CODE CONTEXT:\n{code_context}\n"
        )
        content = self.complete(system_prompt, user_prompt, response_format={"type": "json_object"})
        if content:
            try:
                return json.loads(content)
            except Exception:
                return None
        return None

    def repair_code(self, function_name: str, current_code: str, error_traceback: str) -> Optional[str]:
        """Ask LLM to repair code based on traceback."""
        system_prompt = (
            "You are an expert Python debugger. Fix the provided Python function based on the error traceback. "
            "Return ONLY the replacement Python code for the function. Do not wrap in markdown quotes if possible."
        )
        user_prompt = (
            f"FUNCTION NAME: {function_name}\n\n"
            f"CURRENT CODE:\n{current_code}\n\n"
            f"ERROR TRACEBACK:\n{error_traceback}\n"
        )
        content = self.complete(system_prompt, user_prompt)
        if content:
            # Strip markdown fences if present
            cleaned = content.strip()
            if cleaned.startswith("```python"):
                cleaned = cleaned[9:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return cleaned.strip() + "\n"
        return None


llm_client = LLMClient()
