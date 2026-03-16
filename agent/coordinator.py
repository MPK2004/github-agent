from typing import Any

from agent.issue_finder import IssueFinder
from agent.difficulty_evaluator import DifficultyEvaluator


class Coordinator:
    def __init__(self) -> None:
        self.name = "ai_contribution_mentor"
        self.issue_finder = IssueFinder()
        self.difficulty_evaluator = DifficultyEvaluator()

    async def handle_find_issue(self, user_profile: dict) -> str:
        stack = (user_profile or {}).get("preferred_stack") or ""
        skill = (user_profile or {}).get("skill_level") or "intermediate"
        issues = self.issue_finder.search_issues(stack, limit=15)
        if not issues:
            return "No issues found right now. Next steps will improve query logic and filtering."
        enriched: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for it in issues:
            try:
                eval_result = self.difficulty_evaluator.evaluate_issue(it, "", skill)
            except Exception:
                eval_result = {"difficulty": "intermediate", "reason": "Failed to contact difficulty evaluator; using default."}
            enriched.append((it, eval_result))
        target = skill.lower()
        ordered: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for diff in ("beginner", "intermediate", "advanced"):
            if diff == target:
                ordered.extend([pair for pair in enriched if pair[1].get("difficulty") == diff])
        if not ordered:
            ordered = enriched
        chosen = ordered[:3]
        lines: list[str] = []
        lines.append(f"Found {len(issues)} candidate issues for stack={stack}, target_level={skill}.")
        lines.append("")
        for idx, (it, meta) in enumerate(chosen, start=1):
            repo_url = it.get("repository_url", "")
            repo_name = repo_url.split("/repos/")[-1] if "/repos/" in repo_url else repo_url
            title = it.get("title", "")
            link = it.get("html_url", "")
            comments = it.get("comments", 0)
            updated = it.get("updated_at", "")
            diff = meta.get("difficulty", "intermediate")
            reason = meta.get("reason", "")
            lines.append(f"{idx}) {repo_name} — {title}")
            lines.append(f"   Link: {link}")
            lines.append(f"   Updated: {updated} | Comments: {comments}")
            lines.append(f"   Difficulty: {diff}")
            lines.append(f"   Why this fits you: {reason}")
            lines.append("")
        return "\n".join(lines).strip()

    async def handle_analyze_issue(self, issue_url: str, user_profile: dict | None) -> str:
        return "Issue analysis is not implemented yet. Next steps will add full multi-agent analysis for the provided GitHub issue."

