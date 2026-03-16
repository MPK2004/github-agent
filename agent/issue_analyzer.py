import os
from typing import Any

from groq import Groq


class IssueAnalyzer:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.client = Groq(api_key=key)
        self.model = model or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"

    def analyze(self, issue: dict[str, Any], repo_readme: str, user_profile: dict | None) -> dict[str, Any]:
        title = issue.get("title", "")
        body = issue.get("body", "")
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
            "You are a senior engineer helping a developer contribute to an open source project.\n"
            "Analyze the issue below.\n\n"
            "Provide:\n"
            "1. problem summary\n"
            "2. suggested approach\n"
            "3. files likely involved\n"
            "4. recommended learning resources\n\n"
            "Return a single JSON object with keys:\n"
            "problem_summary (string),\n"
            "suggested_approach (array of steps as strings),\n"
            "files_likely_involved (array of strings),\n"
            "recommended_learning_resources (array of strings).\n"
            "Return ONLY valid JSON."
        )
        user_parts = []
        user_parts.append(f"Repository: {repo}")
        user_parts.append(f"Issue URL: {url}")
        user_parts.append(f"Issue title: {title}")
        user_parts.append("")
        user_parts.append("Issue body:")
        user_parts.append(body)
        user_parts.append("")
        user_parts.append("Repository README (truncated if very long):")
        if len(repo_readme) > 6000:
            user_parts.append(repo_readme[:6000])
        else:
            user_parts.append(repo_readme)
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
            max_tokens=900,
        )
        content = ""
        if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
            content = resp.choices[0].message.content.strip()
        tokens = 0
        if getattr(resp, "usage", None) is not None and getattr(resp.usage, "total_tokens", None) is not None:
            tokens = int(resp.usage.total_tokens or 0)
        parsed = self._parse_json_like(content)
        out = self._normalize(parsed)
        out["_token_usage"] = tokens
        return out

    def _normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        ps = str(parsed.get("problem_summary", "")).strip()
        if not ps:
            ps = "Unable to extract a structured problem summary."
        sa = parsed.get("suggested_approach", [])
        if not isinstance(sa, list):
            sa = []
        sa = [str(x).strip() for x in sa if str(x).strip()]
        files = parsed.get("files_likely_involved", [])
        if not isinstance(files, list):
            files = []
        files = [str(x).strip() for x in files if str(x).strip()]
        res = parsed.get("recommended_learning_resources", [])
        if not isinstance(res, list):
            res = []
        res = [str(x).strip() for x in res if str(x).strip()]
        return {
            "problem_summary": ps,
            "suggested_approach": sa,
            "files_likely_involved": files,
            "recommended_learning_resources": res,
        }

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

