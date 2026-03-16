AI Open Source Contribution Mentor Agent (Telegram)
===================================================

Telegram bot that helps developers discover, understand, and solve GitHub issues for open source contributions.

## Project Overview

This bot is a mentor-style assistant:

- Finds issues aligned to a developer’s preferred stack and skill level
- Explains the problem in plain language
- Proposes a concrete implementation plan
- Generates a PR title/description/commit message
- Recommends learning resources when needed

## Architecture

Directory layout:

- `telegram/`: Telegram transport (polling) and user interaction
- `agent/`: Multi-agent pipeline and Groq prompts
- `storage/`: Lightweight persistence (`users.json`)
- `evaluation/`: Benchmarking and scoring

Key technical choices:

- Python 3.10+
- Polling mode (no webhook dependency)
- Authenticated GitHub API calls (rate-limit resilient)
- Groq LLM calls for difficulty, analysis, planning, and PR template generation

## Agent Pipeline

### `/find_issue`

- Fetch 15 candidates from GitHub Search API for the user’s stack
- Filter out:
  - issues updated/created more than 2 years ago
  - issues with more than 50 comments
- Use Groq to estimate difficulty and a short fit explanation
- Strictly select matching difficulty first, then backfill from nearest levels if needed
- Return top 3

### `/analyze_issue <github_issue_url>`

Workflow:

- Fetch issue title/body
- Fetch repository README
- Analyze (problem summary, approach, likely files, learning resources)
- Plan (implementation steps, test plan, risks)
- Generate PR template (title, description, commit message)

Telegram responses include a short reasoning trace before the final structured output.

## Installation

Tested on Linux. Recommended baseline:

- CPU: 1 vCPU
- RAM: 1 GB
- Python: 3.10+

Setup:

```bash
cd ai-contribution-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Create `.env` based on `.env.example`:

- `TELEGRAM_BOT_TOKEN`: Telegram Bot API token
- `GROQ_API_KEY`: Groq API key
- `GITHUB_TOKEN`: GitHub Personal Access Token (recommended to avoid low unauthenticated limits)

## Running the Bot (Polling)

Run:

```bash
cd ai-contribution-agent
python telegram/bot.py
```

Expected behavior:

- If `TELEGRAM_BOT_TOKEN` is missing, the process fails fast with a clear error.

## Deployment (Linux server)

Minimal steps (DigitalOcean droplet style):

- Create a non-root user and install Python 3.10+
- Copy the `ai-contribution-agent/` folder to the server
- Create a venv and install requirements
- Set environment variables (prefer systemd env over `.env`)
- Run as a systemd service so the bot restarts automatically

Systemd example (adjust paths):

```ini
[Unit]
Description=AI Contribution Mentor Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ai-contribution-agent
ExecStart=/opt/ai-contribution-agent/.venv/bin/python telegram/bot.py
Restart=always
RestartSec=5
Environment=TELEGRAM_BOT_TOKEN=...
Environment=GROQ_API_KEY=...
Environment=GITHUB_TOKEN=...

[Install]
WantedBy=multi-user.target
```

## Performance Evaluation

Benchmark script compares agent output vs a baseline LLM output for the same issue and uses a Groq judge:

```bash
cd ai-contribution-agent
python evaluation/benchmark.py --issue-url "https://github.com/<owner>/<repo>/issues/<number>"
```

Output is JSON including judge metrics and token usage. Scoring details are in `evaluation/metrics.md`.

Example (illustrative) benchmark:

- Accuracy: 0.90
- Relevance: 0.95
- Clarity: 0.92
- Total tokens: ~7000
- Baseline score: ~6400
- Agent pipeline score: ~7600

In practice the agent tends to outperform the baseline on structure, implementation detail, and PR readiness while using more tokens.

## Cursor Integration

- `.cursorrules` describes the intended modular structure and workflow.
- `dev_log.txt` is the single source of truth for decisions, mistakes, and fixes made while building the project.

