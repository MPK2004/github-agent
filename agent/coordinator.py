from typing import Any

from agent.issue_finder import IssueFinder
from agent.difficulty_evaluator import DifficultyEvaluator
from agent.issue_analyzer import IssueAnalyzer
from agent.solution_planner import SolutionPlanner
from agent.pr_generator import PRGenerator


class Coordinator:
    def __init__(self) -> None:
        self.name = "ai_contribution_mentor"
        self.issue_finder = IssueFinder()
        self.difficulty_evaluator = DifficultyEvaluator()
        self.issue_analyzer = IssueAnalyzer()
        self.solution_planner = SolutionPlanner()
        self.pr_generator = PRGenerator()

    async def handle_find_issue(self, user_profile: dict) -> tuple[str, list[dict[str, Any]]]:
        stack = (user_profile or {}).get("preferred_stack") or ""
        skill = (user_profile or {}).get("skill_level") or "intermediate"
        issues = self.issue_finder.search_issues(stack, limit=15)
        if not issues:
            return "No issues found right now. Next steps will improve query logic and filtering.", []
        enriched: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for it in issues:
            try:
                eval_result = self.difficulty_evaluator.evaluate_issue(it, "", skill)
            except Exception as e:
                fallback_diff = skill.lower()
                if fallback_diff not in ("beginner", "intermediate", "advanced"):
                    fallback_diff = "intermediate"
                eval_result = {
                    "difficulty": fallback_diff,
                    "reason": f"Difficulty evaluator unavailable ({type(e).__name__}). Showing best-effort results.",
                    "_token_usage": 0,
                }
            enriched.append((it, eval_result))
        target = skill.lower()
        order_map = {
            "beginner": ["beginner", "intermediate", "advanced"],
            "intermediate": ["intermediate", "beginner", "advanced"],
            "advanced": ["advanced", "intermediate", "beginner"],
        }
        ordered: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for diff in order_map.get(target, ["intermediate", "beginner", "advanced"]):
            ordered.extend([pair for pair in enriched if pair[1].get("difficulty") == diff])
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
        return "\n".join(lines).strip(), [it for it, _ in chosen]

    async def handle_analyze_issue(self, issue_url: str, user_profile: dict | None) -> str:
        text, _tokens = await self.handle_analyze_issue_with_usage(issue_url, user_profile)
        return text

    async def handle_analyze_issue_with_usage(self, issue_url: str, user_profile: dict | None) -> tuple[str, int]:
        from agent.issue_finder import parse_github_issue_url

        owner, repo, number = parse_github_issue_url(issue_url)
        issue = self.issue_finder.fetch_issue(owner, repo, int(number))
        readme = self.issue_finder.fetch_repo_readme(owner, repo)
        analysis = self.issue_analyzer.analyze(issue, readme, user_profile)
        plan = self.solution_planner.plan(issue, analysis, user_profile)
        pr = self.pr_generator.generate(issue, analysis, plan)
        token_usage = int(analysis.get("_token_usage", 0) or 0) + int(plan.get("_token_usage", 0) or 0) + int(pr.get("_token_usage", 0) or 0)

        lines: list[str] = []
        lines.append("Result (structured):")
        lines.append("")
        lines.append("Problem summary:")
        lines.append(analysis.get("problem_summary", ""))
        lines.append("")
        merged_plan: list[str] = []
        plan_steps = plan.get("plan_steps", []) or []
        suggested = analysis.get("suggested_approach", []) or []
        if plan_steps:
            merged_plan.extend(plan_steps)
        elif suggested:
            merged_plan.extend(suggested)
        lines.append("Files likely involved:")
        for f in analysis.get("files_likely_involved", []) or []:
            lines.append(f"- {f}")
        lines.append("")
        lines.append("Recommended learning resources:")
        for r in analysis.get("recommended_learning_resources", []) or []:
            lines.append(f"- {r}")
        lines.append("")
        lines.append("Solution plan:")
        for i, step in enumerate(merged_plan, start=1):
            lines.append(f"- {i}. {step}")
        lines.append("")
        lines.append("Test plan:")
        for t in plan.get("test_plan", []) or []:
            lines.append(f"- {t}")
        lines.append("")
        lines.append("Risk notes:")
        for rn in plan.get("risk_notes", []) or []:
            lines.append(f"- {rn}")
        lines.append("")
        lines.append("PR template:")
        lines.append(f"PR title: {pr.get('pr_title','')}")
        lines.append("")
        lines.append("PR description:")
        lines.append(pr.get("pr_description", ""))
        lines.append("")
        lines.append(f"Commit message: {pr.get('commit_message','')}")
        return "\n".join([x for x in lines if x is not None]).strip(), token_usage

