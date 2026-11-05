# Workshop Parts Desk

Agentic AI solution for **KSIT Hackmatrix 1.0** (Dept. of AI & ML).

An LLM-assisted Python controller that clears a workshop's parts requests safely. For each request it either dispatches a compatible, in-stock part or escalates to a human, while staying within a shared tool budget.

## Problem summary
- 6 natural-language requests and 12 fictional parts per batch
- Each request needs the right voltage, connector and minimum wattage (10 W or 20 W; higher is allowed)
- Tools: `inspect` (1 unit), `clarify` (2), `verify` (2). Shared budget: 14 units, max 60 actions
- Every request ends in `dispatch` or `escalate`
- One incompatible dispatch makes the whole batch score zero

## Project structure
