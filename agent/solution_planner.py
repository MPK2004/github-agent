import os
from typing import Any

from groq import Groq


class SolutionPlanner:
    def __init__(self, api_key: str | None = None, model: str = "llama3-70b-8192") -> None:
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.client = Groq(api_key=key)
        self.model = model

    def plan(self, issue: dict[str, Any], analysis: dict[str, Any], user_profile: dict | None) -> dict[str, Any]:
        title = issue.get("title", "")
        url = issue.get("html_url", "")
        repo = ""
        repo_url = issue.get("repository_url") or ""
        if "/repos/" in repo_url:
            repo = repo_url.split("/repos/")[-1]
        stack = ""
        level = ""
        if user_profile:
            stack = str(user_profile.get("preferred_stack") or "")
            level = str(user_profile.get("skill_level") or "")
        system_prompt = (
            "You are a senior engineer mentoring an open source contributor.\n"
            "Create a practical implementation plan.\n"
            "Return ONLY valid JSON with keys:\n"
            "plan_steps (array of strings),\n"
            "test_plan (array of strings),\n"
            "risk_notes (array of strings).\n"
        )
        user_parts = []
        user_parts.append(f"Repository: {repo}")
        user_parts.append(f"Issue URL: {url}")
        user_parts.append(f"Issue title: {title}")
        user_parts.append("")
        user_parts.append("Analysis (structured):")
        user_parts.append(self._safe_json(analysis))
        user_parts.append("")
        if stack or level:
            user_parts.append(f"Developer profile: preferred_stack={stack}, skill_level={level}")
        user_prompt = "\n".join(user_parts)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        content = ""
        if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
            content = resp.choices[0].message.content.strip()
        parsed = self._parse_json_like(content)
        return self._normalize(parsed)

    def _normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        steps = parsed.get("plan_steps", [])
        if not isinstance(steps, list):
            steps = []
        steps = [str(x).strip() for x in steps if str(x).strip()]
        tests = parsed.get("test_plan", [])
        if not isinstance(tests, list):
            tests = []
        tests = [str(x).strip() for x in tests if str(x).strip()]
        risks = parsed.get("risk_notes", [])
        if not isinstance(risks, list):
            risks = []
        risks = [str(x).strip() for x in risks if str(x).strip()]
        return {"plan_steps": steps, "test_plan": tests, "risk_notes": risks}

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

