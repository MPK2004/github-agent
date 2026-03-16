# Evaluation Metrics

This project evaluates the agent by comparing its output to a baseline LLM output for the same GitHub issue.

## Metrics

All metric components are scaled to \(0..1\).

- Accuracy: How correct and technically sound the guidance is, given the issue and repo README.
- Recommendation relevance: How well the advice aligns with the issue context and avoids irrelevant suggestions.
- Clarity: How readable and actionable the response is (structure, step-by-step guidance, concreteness).
- Token usage: Total tokens used across agent calls + baseline generation + judge.

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
\text{quality} = \frac{\text{accuracy} + \text{relevance} + \text{clarity}}{3}
\]

\[
\text{score} = \text{clamp}_{1..10000}\left(\text{quality} \times 9000 - \frac{\text{token\_usage}}{10}\right)
\]

This rewards high model quality while applying a softer penalty for long outputs.

## How to run

From the `ai-contribution-agent/` directory:

```bash
python evaluation/benchmark.py --issue-url "https://github.com/<owner>/<repo>/issues/<number>"
```

Optional output to file:

```bash
python evaluation/benchmark.py --issue-url "https://github.com/<owner>/<repo>/issues/<number>" --output-json "benchmark_result.json"
```

