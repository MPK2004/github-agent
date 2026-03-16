import os
from typing import Any

from groq import Groq


class DifficultyEvaluator:
    def __init__(self, api_key: str | None = None, model: str = "llama3-70b-8192") -> None:
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.client = Groq(api_key=key)
        self.model = model

    def evaluate_issue(self, issue: dict[str, Any], repo_readme: str, target_skill: str) -> dict[str, Any]:
        title = issue.get("title", "")
        body = issue.get("body", "")
        repo = ""
        repo_url = issue.get("repository_url") or ""
        if "/repos/" in repo_url:
            repo = repo_url.split("/repos/")[-1]
        system_prompt = (
            "You are an experienced software engineer helping developers contribute to open source.\n"
            "Analyze the following GitHub issue and estimate its difficulty.\n\n"
            "Consider:\n"
            "- required programming knowledge\n"
            "- repository complexity\n"
            "- implementation effort\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            '{\"difficulty\": \"beginner | intermediate | advanced\", \"reason\": \"short explanation\"}'
        )
        user_parts = []
        user_parts.append(f"Repository: {repo}")
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
        user_parts.append(f"Target contributor skill level: {target_skill}")
        user_prompt = "\n".join(user_parts)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=256,
        )
        content = ""
        if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
            content = resp.choices[0].message.content.strip()
        parsed = self._parse_json_like(content)
        difficulty = str(parsed.get("difficulty", "")).strip().lower()
        if difficulty not in ("beginner", "intermediate", "advanced"):
            difficulty = "intermediate"
        reason = str(parsed.get("reason", "")).strip()
        return {"difficulty": difficulty, "reason": reason or "Difficulty estimated based on issue and repository context."}

    def _parse_json_like(self, text: str) -> dict[str, Any]:
        import json

        s = text.strip()
        try:
            if not s.startswith("{"):
                start = s.find("{")
                end = s.rfind("}")
                if start != -1 and end != -1 and end > start:
                    s = s[start : end + 1]
            return json.loads(s)
        except Exception:
            return {}

