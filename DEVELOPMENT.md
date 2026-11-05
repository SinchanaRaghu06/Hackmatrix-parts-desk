# Development datasets — public-expanded-1

This packet replaces the small demonstration pool with 40 ordinary training examples and 12 separate ordinary practice examples. `smoke.json` is the first two training examples for a quick setup check; it is deliberately a subset, not a third independent dataset. `dataset_info.json` records counts, provenance and a group_index mapping each file row to its source group for tuning folds. `baseline_results.json` records the supplied starter's scores; it is a reference, not a target or a claim of optimal performance.

Keep all examples from one customer/world/source shard/source day together when making your own tuning folds. Changed variants remain in the same partition as their ordinary counterparts. The twist supplement contains changed training and changed practice only after release. Private official cohorts are unchanged.

## Run locally

Use Python 3.12; AIML additionally requires NumPy. Run commands from the extracted packet directory.

```sh
python local_runner.py solution.py smoke.json --mock
python local_runner.py solution.py training.json --gateway-url https://YOUR-GATEWAY/gateway --limit 5
python local_runner.py solution.py practice.json --gateway-url https://YOUR-GATEWAY/gateway
```

## Full Agentic episodes

The runner uses the same world transitions and score formula as the portal. It passes only observations to decide, maintains tool stock/budget/steps, relays op:llm, and reports per-case and aggregate scores. The public `world` member contains evaluator answers for these examples; never build a submission that looks up those answers. Public answers are not available for official worlds.

`--mock` is an offline handoff-only model substitute: it checks the complete pipeline, not your model's quality or official eligibility. Real model inference is explicitly selected with `--gateway-url`; put its bearer token in TEAM_GATEWAY_TOKEN (never in code or data). Each world requires 1–8 successful gateway calls, so use `--limit` while debugging to control your own model costs. Local execution is on your machine, not the portal sandbox. All local results are development results; official eligibility also requires the portal's runtime and inference review.
