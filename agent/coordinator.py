from agent.issue_finder import IssueFinder


class Coordinator:
    def __init__(self) -> None:
        self.name = "ai_contribution_mentor"
        self.issue_finder = IssueFinder()

    async def handle_find_issue(self, user_profile: dict) -> str:
        stack = (user_profile or {}).get("preferred_stack") or ""
        skill = (user_profile or {}).get("skill_level") or ""
        issues = self.issue_finder.search_issues(stack, limit=15)
        if not issues:
            return "No issues found right now. Next steps will improve query logic and filtering."
        lines = []
        lines.append(f"Found {len(issues)} candidate issues for stack={stack}, target_level={skill}.")
        lines.append("")
        for idx, it in enumerate(issues[:3], start=1):
            repo_url = it.get("repository_url", "")
            repo_name = repo_url.split("/repos/")[-1] if "/repos/" in repo_url else repo_url
            title = it.get("title", "")
            link = it.get("html_url", "")
            comments = it.get("comments", 0)
            updated = it.get("updated_at", "")
            lines.append(f"{idx}) {repo_name} — {title}")
            lines.append(f"   Link: {link}")
            lines.append(f"   Updated: {updated} | Comments: {comments}")
            lines.append("   Difficulty: pending (Groq evaluator not wired yet)")
            lines.append("   Fit: pending (will be added after difficulty evaluation)")
            lines.append("")
        return "\n".join(lines).strip()

    async def handle_analyze_issue(self, issue_url: str, user_profile: dict | None) -> str:
        return "Issue analysis is not implemented yet. Next steps will add full multi-agent analysis for the provided GitHub issue."

