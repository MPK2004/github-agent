import os
from typing import Any

from groq import Groq


class PRGenerator:
    def __init__(self, api_key: str | None = None, model: str = "llama3-70b-8192") -> None:
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.client = Groq(api_key=key)
        self.model = model

    def generate(self, issue: dict[str, Any], analysis: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        title = issue.get("title", "")
        url = issue.get("html_url", "")
        repo = ""
        repo_url = issue.get("repository_url") or ""
        if "/repos/" in repo_url:
            repo = repo_url.split("/repos/")[-1]
        system_prompt = (
            "You generate a GitHub pull request template.\n"
            "Return ONLY valid JSON with keys:\n"
            "pr_title (string),\n"
            "pr_description (string),\n"
            "commit_message (string).\n"
        )
        user_parts = []
        user_parts.append(f"Repository: {repo}")
        user_parts.append(f"Issue URL: {url}")
        user_parts.append(f"Issue title: {title}")
        user_parts.append("")
        user_parts.append("Analysis (structured):")
        user_parts.append(self._safe_json(analysis))
        user_parts.append("")
        user_parts.append("Plan (structured):")
        user_parts.append(self._safe_json(plan))
        user_prompt = "\n".join(user_parts)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        content = ""
        if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
            content = resp.choices[0].message.content.strip()
        parsed = self._parse_json_like(content)
        return self._normalize(parsed, title)

    def _normalize(self, parsed: dict[str, Any], fallback_title: str) -> dict[str, Any]:
        pr_title = str(parsed.get("pr_title", "")).strip() or f"Fix: {fallback_title}".strip()
        pr_description = str(parsed.get("pr_description", "")).strip() or "Summary:\n- \n\nTest plan:\n- "
        commit_message = str(parsed.get("commit_message", "")).strip() or pr_title
        return {"pr_title": pr_title, "pr_description": pr_description, "commit_message": commit_message}

    def _parse_json_like(self, text: str) -> dict[str, Any]:
        import json

        s = (text or "").strip()
        try:
            if not s.startswith("{"):
                start = s.find("{")
                end = s.rfind("}")
                if start != -1 and end != -1 and end > start:
                    s = s[start : end + 1]
            return json.loads(s)
        except Exception:
            return {}

    def _safe_json(self, obj: Any) -> str:
        import json

        try:
            return json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            return str(obj)

