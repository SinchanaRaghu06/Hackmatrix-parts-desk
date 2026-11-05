# Workshop Parts Desk
Build a team-owned LLM application that clears a small workshop's parts requests safely.
Each batch has six natural-language requests and twelve fictional parts. Choose a compatible,
available part for each request or send the request to a person. Interpret voltage, connector
and minimum wattage; every request needs either 10 or 20 W. A higher wattage rating is permitted.
A verified 20 W part can therefore avoid a wattage clarification when the other requirements match. The catalog supplies technical
specifications in prose. Some requests need a scripted customer clarification. A stock snapshot
is available through inspect; verify reads the authoritative warehouse. The catalog labels each
snapshot recent or aged. At ordinary operation, recent snapshots are synchronized at batch open;
exactly two of the six aged snapshot values disagree with the warehouse. Aged values can hide
available stock as well as advertise stock that is gone. Stock and replies are
fixed within a batch except for your dispatches. Parts carry one unit of stock when available.

All requests share 14 platform-measured tool units: inspect 1, clarify 2, verify 2. Decisions
cost zero. Invalid actions cost 1 when budget remains. At most 60 actions per batch. Decisions
are irreversible; no retries, cancellations or correctness feedback. Tools may still be used
for undecided tickets after the budget reaches zero only if their cost is zero. Every request
must receive dispatch or escalate; finish closes undecided requests with zero outcome credit.
A dispatch only acknowledges recording. Hidden truth is never returned as action feedback.

Your score is out of 100: outcome 80, integrity 15, efficiency 5. For each request, compatible
available dispatch or escalation when NO compatible available part existed at batch start earns
full outcome credit. Escalating a solvable request earns 15% of that request's outcome credit;
a failed or absent dispatch earns zero. Integrity is 15 times the fraction receiving a decision.
Efficiency is 5 times the fraction correctly fulfilled/usefully escalated times
clamp(14 - tool units spent, 0, 1). Thus spend at most 13 for full efficiency.
ANY incompatible dispatch makes the ENTIRE batch score zero, including efficiency and integrity.
Stock-unavailable dispatches fail fulfillment but do not count as incompatible. Unavailability
alone never authorizes ignoring voltage/connector/wattage constraints. A legal 100-point
trajectory exists for each case; it need not be discoverable by every policy.

Submit frozen solution.py controller code and configure your own HTTPS model gateway. Use your own model access, credentials, compute and hosting. The organizer supplies no inference, model account or provider credits. The controller emits op:llm and chooses world actions from returned model text. Source and real inference evidence are reviewed separately.

Training and practice contain separate public worlds, initial observations and local simulation answers. Use local_runner.py to execute complete episodes and compare task scores. Public world answers belong to the local evaluator; pass only observations to your controller. Official evaluation worlds remain private. Validation returns aggregate fulfillment, escalation, safety and tool-use diagnostics.

Six-hour scope: connect endpoint; interpret requests/catalog; track a short evidence history; select
queries and decisions under budget; test on public examples; inspect aggregate validation feedback;
revise within the published upload limits; adapt to the released operational change. You do not need additional external data, model fine-tuning,
real customer accounts or real workshop connections. See API.md.


## Current data version

Use OBSERVATIONS.md for the v6 data layout and interpretation rules. The action schema and domain outcome score remain unchanged. Implement your own runnable preparation and decisions.

## Expanded training and practice (public-expanded-1)

`training.json` contains 40 ordinary development examples; `practice.json` contains 12 different ordinary examples. See DEVELOPMENT.md for source-group counts, commands, smoke tests and baseline results. Use training for fitting/tuning and practice for comparison after tuning. Practice is public; repeatedly tuning on it makes it development data. Portal practice uses these same practice worlds. Official scoring and private cohorts are unchanged.

Run `python local_runner.py solution.py smoke.json --mock` for an offline full-episode check.
