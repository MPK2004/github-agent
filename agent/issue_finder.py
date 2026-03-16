import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class IssueFinder:
    def __init__(self, github_token: str | None = None) -> None:
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-contribution-agent",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _stack_to_query(self, preferred_stack: str) -> str:
        stack = (preferred_stack or "").strip().lower()
        if stack == "python":
            return "language:python"
        if stack in ("javascript", "js"):
            return "language:javascript"
        if stack == "rust":
            return "language:rust"
        if stack in ("ai/ml", "ai", "ml"):
            return "(language:python OR language:jupyter-notebook)"
        return ""

    def search_issues(self, preferred_stack: str, limit: int = 15) -> list[dict[str, Any]]:
        if limit < 1:
            return []
        q_parts = []
        stack_q = self._stack_to_query(preferred_stack)
        if stack_q:
            q_parts.append(stack_q)
        q_parts.append("state:open")
        q_parts.append("is:issue")

        query = "+".join(q_parts)
        url = "https://api.github.com/search/issues"
        params = {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(max(limit, 1), 100),
            "page": 1,
        }
        resp = self.session.get(url, headers=self._headers(), params=params, timeout=30)
        if resp.status_code == 401:
            raise RuntimeError("GitHub authentication failed (401). Check GITHUB_TOKEN.")
        if resp.status_code == 403:
            raise RuntimeError("GitHub API forbidden (403). Possible rate limit or insufficient token scopes.")
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub search failed ({resp.status_code}): {resp.text[:500]}")
        data = resp.json()
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return self._filter_issues(items)[:limit]

    def _filter_issues(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=365 * 2)
        filtered: list[dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            comments = it.get("comments", 0)
            if isinstance(comments, int) and comments > 50:
                continue
            updated_at = it.get("updated_at") or it.get("created_at")
            if isinstance(updated_at, str):
                try:
                    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    if dt < cutoff:
                        continue
                except Exception:
                    pass
            repo_url = it.get("repository_url")
            html_url = it.get("html_url")
            title = it.get("title")
            number = it.get("number")
            if not (repo_url and html_url and title and number is not None):
                continue
            filtered.append(it)
        return filtered

    def fetch_issue(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        resp = self.session.get(url, headers=self._headers(), timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub issue fetch failed ({resp.status_code}): {resp.text[:500]}")
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError("GitHub issue fetch returned unexpected response.")
        return data

    def fetch_repo_readme(self, owner: str, repo: str) -> str:
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        headers = self._headers()
        headers["Accept"] = "application/vnd.github.raw+json"
        resp = self.session.get(url, headers=headers, timeout=30)
        if resp.status_code == 404:
            return ""
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub README fetch failed ({resp.status_code}): {resp.text[:500]}")
        return resp.text or ""


def parse_github_issue_url(url: str) -> tuple[str, str, int]:
    u = (url or "").strip()
    if not u.startswith("https://github.com/"):
        raise ValueError("Invalid GitHub issue URL. Expected https://github.com/<owner>/<repo>/issues/<number>")
    parts = u.split("/")
    try:
        owner = parts[3]
        repo = parts[4]
        if parts[5] != "issues":
            raise ValueError
        number = int(parts[6])
    except Exception:
        raise ValueError("Invalid GitHub issue URL. Expected https://github.com/<owner>/<repo>/issues/<number>")
    return owner, repo, number

