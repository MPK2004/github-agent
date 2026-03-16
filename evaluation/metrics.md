# Evaluation Metrics

This project evaluates the agent by comparing its output to a baseline LLM output for the same GitHub issue.

## Metrics

All metric components are scaled to \(0..1\).

- Accuracy: How correct and technically sound the guidance is, given the issue and repo README.
- Recommendation relevance: How well the advice aligns with the issue context and avoids irrelevant suggestions.
- Clarity: How readable and actionable the response is (structure, step-by-step guidance, concreteness).
- Token usage: Total tokens used across baseline generation + judge + (optionally) agent calls.

## Judge

We use a Groq LLM-as-judge that reads:

- the GitHub issue URL
- the agent output
- the baseline output

and returns JSON:

```json
{
  "accuracy": 0.0,
  "relevance": 0.0,
  "clarity": 0.0,
  "notes": "..."
}
```

## Agent Score (1–10000)

We compute:

\[
\text{score} = \text{clamp}_{1..10000}\left(\left(\frac{\text{accuracy} \times \text{relevance} \times \text{clarity}}{\max(1,\ \text{token\_usage})}\right)\times 2{,}000{,}000\right)
\]

This heavily rewards quality while penalizing token usage.

## How to run

From the `ai-contribution-agent/` directory:

```bash
python evaluation/benchmark.py --issue-url "https://github.com/<owner>/<repo>/issues/<number>"
```

Optional output to file:

```bash
python evaluation/benchmark.py --issue-url "https://github.com/<owner>/<repo>/issues/<number>" --output-json "benchmark_result.json"
```

