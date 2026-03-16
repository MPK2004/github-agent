import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from groq import Groq

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.coordinator import Coordinator


@dataclass
class RunResult:
    agent_text: str
    baseline_text: str
    judge: dict[str, Any]
    agent_tokens: int
    baseline_tokens: int
    judge_tokens: int
    score: int


def _clamp_int(x: float, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(x))))


def compute_agent_score(accuracy: float, relevance: float, clarity: float, token_usage: int) -> int:
    a = max(0.0, min(1.0, float(accuracy)))
    r = max(0.0, min(1.0, float(relevance)))
    c = max(0.0, min(1.0, float(clarity)))
    t = max(1, int(token_usage))
    quality = (a + r + c) / 3.0
    quality_score = quality * 9000.0
    efficiency_penalty = t / 10.0
    final = quality_score - efficiency_penalty
    return _clamp_int(final, 1, 10000)


def groq_chat(client: Groq, model: str, system: str, user: str, max_tokens: int) -> tuple[str, int]:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )
    content = ""
    if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
        content = resp.choices[0].message.content.strip()
    tokens = 0
    if getattr(resp, "usage", None) is not None and getattr(resp.usage, "total_tokens", None) is not None:
        tokens = int(resp.usage.total_tokens or 0)
    return content, tokens


def parse_json_like(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    try:
        if not s.startswith("{"):
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                s = s[start : end + 1]
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def baseline_output(client: Groq, model: str, issue_url: str, issue_title: str, issue_body: str, readme: str) -> tuple[str, int]:
    system = (
        "You are a senior engineer mentoring an open source contributor.\n"
        "Given a GitHub issue and repository README, produce a structured response with:\n"
        "- problem summary\n"
        "- suggested approach\n"
        "- files likely involved\n"
        "- recommended learning resources\n"
        "- solution plan\n"
        "- PR template (title, description, commit message)\n\n"
        "Return plain text with clear section headings. Do not output JSON."
    )
    user_parts = []
    user_parts.append(f"Issue URL: {issue_url}")
    user_parts.append(f"Issue title: {issue_title}")
    user_parts.append("")
    user_parts.append("Issue body:")
    user_parts.append(issue_body)
    user_parts.append("")
    user_parts.append("Repository README (truncated if very long):")
    user_parts.append(readme[:6000] if len(readme) > 6000 else readme)
    user = "\n".join(user_parts)
    return groq_chat(client, model, system, user, max_tokens=1400)


def judge_outputs(client: Groq, model: str, issue_url: str, agent_text: str, baseline_text: str) -> tuple[dict[str, Any], int]:
    system = (
        "You are an evaluator for an AI mentor bot.\n"
        "Score the AGENT output relative to the BASELINE output for the same GitHub issue.\n"
        "Return ONLY valid JSON with keys:\n"
        "accuracy (number 0..1), relevance (number 0..1), clarity (number 0..1), notes (string).\n"
    )
    user = (
        f"Issue: {issue_url}\n\n"
        "AGENT OUTPUT:\n"
        f"{agent_text}\n\n"
        "BASELINE OUTPUT:\n"
        f"{baseline_text}\n"
    )
    text, tokens = groq_chat(client, model, system, user, max_tokens=350)
    parsed = parse_json_like(text)
    acc = parsed.get("accuracy", 0.5)
    rel = parsed.get("relevance", 0.5)
    cla = parsed.get("clarity", 0.5)
    notes = str(parsed.get("notes", "")).strip()
    try:
        accf = float(acc)
    except Exception:
        accf = 0.5
    try:
        relf = float(rel)
    except Exception:
        relf = 0.5
    try:
        claf = float(cla)
    except Exception:
        claf = 0.5
    return {"accuracy": accf, "relevance": relf, "clarity": claf, "notes": notes}, tokens


async def run_once(issue_url: str, model: str) -> RunResult:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    client = Groq(api_key=key)
    coord = Coordinator()

    from agent.issue_finder import IssueFinder, parse_github_issue_url

    finder = IssueFinder()
    owner, repo, number = parse_github_issue_url(issue_url)
    issue = finder.fetch_issue(owner, repo, number)
    readme = finder.fetch_repo_readme(owner, repo)

    agent_text, agent_tokens = await coord.handle_analyze_issue_with_usage(issue_url, None)

    baseline_text, baseline_tokens = baseline_output(
        client,
        model,
        issue_url=issue_url,
        issue_title=str(issue.get("title", "")),
        issue_body=str(issue.get("body", "")),
        readme=readme,
    )
    judge, judge_tokens = judge_outputs(client, model, issue_url, agent_text, baseline_text)
    total_tokens = agent_tokens + baseline_tokens + judge_tokens
    score = compute_agent_score(judge["accuracy"], judge["relevance"], judge["clarity"], total_tokens)
    return RunResult(
        agent_text=agent_text,
        baseline_text=baseline_text,
        judge=judge,
        agent_tokens=agent_tokens,
        baseline_tokens=baseline_tokens,
        judge_tokens=judge_tokens,
        score=score,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-url", required=True)
    parser.add_argument("--model", default=os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    result = __import__("asyncio").run(run_once(args.issue_url, args.model))
    payload = {
        "issue_url": args.issue_url,
        "score": result.score,
        "judge": result.judge,
        "token_usage": {
            "agent_tokens": result.agent_tokens,
            "baseline_tokens": result.baseline_tokens,
            "judge_tokens": result.judge_tokens,
            "total_tokens": result.agent_tokens + result.baseline_tokens + result.judge_tokens,
        },
        "agent_output": result.agent_text,
        "baseline_output": result.baseline_text,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

