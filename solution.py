"""Frozen LLM-assisted controller for the Workshop Parts Desk.

The controller never calls the internet directly. The portal relays each
'op=llm' request to the team's registered HTTPS gateway and returns the model
text in observation['llm_response'].
"""
import json
import re


MAX_MODEL_CALLS = 8
MAX_MESSAGE_CHARS = 43000
MAX_OUTPUT_TOKENS = 768

TOOL_ARGUMENTS = {
    "inspect": {"part_id"},
    "verify": {"part_id"},
    "clarify": {"ticket_id"},
    "dispatch": {"ticket_id", "part_id"},
    "escalate": {"ticket_id"},
    "finish": set(),
}


def _current_approved_documents(documents):
    """Keep the latest approved revision per entity, ignoring drafts/retries."""
    best = {}
    for doc in documents or []:
        if not isinstance(doc, dict) or doc.get("status") != "approved":
            continue
        entity = doc.get("entity_id")
        if not entity:
            continue

        key = (
            int(doc.get("revision", 0) or 0),
            int(doc.get("issued_at", 0) or 0),
            int(doc.get("received_at", 0) or 0),
        )

        if entity not in best or key > best[entity][0]:
            best[entity] = (key, doc)

    return [item[1] for item in best.values()]


def _compact_observation(observation):
    """Keep decision-relevant evidence while staying inside gateway limits."""
    obs = observation if isinstance(observation, dict) else {}
    compact = {}

    for key in (
        "case_id", "policy", "budget_remaining", "steps_remaining",
        "tools", "tickets", "catalog", "decided_ticket_ids", "done",
        "result", "data_quality", "as_of",
    ):
        if key in obs:
            compact[key] = obs[key]

    if "request_documents" in obs:
        compact["current_approved_request_documents"] = (
            _current_approved_documents(obs.get("request_documents"))
        )

    if "catalog_documents" in obs:
        compact["current_approved_catalog_documents"] = (
            _current_approved_documents(obs.get("catalog_documents"))
        )

    known = set(compact) | {
        "request_documents", "catalog_documents", "llm_response",
        "llm_usage",
    }

    for key, value in obs.items():
        if key not in known and key not in ("world", "answers", "labels"):
            compact[key] = value

    return compact


def _undecided_ticket_ids(observation):
    tickets = observation.get("tickets", []) if isinstance(observation, dict) else []
    decided = set(observation.get("decided_ticket_ids", []) or [])

    return [
        ticket.get("id")
        for ticket in tickets
        if isinstance(ticket, dict)
        and ticket.get("id")
        and ticket.get("id") not in decided
    ]


def _safe_handoff(observation):
    remaining = _undecided_ticket_ids(observation)

    if remaining:
        return {"op": "escalate", "ticket_id": remaining[0]}

    return {"op": "finish"}


def _extract_json_object(text):
    """Accept plain JSON or a fenced JSON object; reject non-object replies."""
    if not isinstance(text, str):
        raise ValueError("Missing model text")

    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*", "", text,
            count=1, flags=re.I
        )
        text = re.sub(r"\s*```$", "", text, count=1)

    decoder = json.JSONDecoder()
    start = text.find("{")

    if start < 0:
        raise ValueError("No JSON object in model response")

    value, _ = decoder.raw_decode(text[start:])

    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")

    return value


def _validate_world_action(action, observation):
    """Validate action shape and IDs before spending a world action."""
    if not isinstance(action, dict):
        return False

    op = action.get("op")

    if op not in TOOL_ARGUMENTS:
        return False

    if set(action) != ({"op"} | TOOL_ARGUMENTS[op]):
        return False

    tickets = {
        item.get("id") for item in observation.get("tickets", [])
        if isinstance(item, dict)
    }

    parts = {
        item.get("id") for item in observation.get("catalog", [])
        if isinstance(item, dict)
    }

    decided = set(observation.get("decided_ticket_ids", []) or [])

    if op in ("clarify", "dispatch", "escalate"):
        ticket_id = action.get("ticket_id")

        if ticket_id not in tickets or ticket_id in decided:
            return False

    if op in ("inspect", "verify", "dispatch"):
        if action.get("part_id") not in parts:
            return False

    return True


def _build_prompt(observation, state):
    compact = _compact_observation(observation)
    history = state.get("history", [])[-12:]

    instructions = (
        "You are the decision-making model for a fictional workshop parts desk. "
        "Choose exactly ONE next world action. Return ONLY one JSON object, no "
        "markdown and no explanation. Valid actions and exact schemas:\n"
        '{"op":"inspect","part_id":"PART_ID"}\n'
        '{"op":"verify","part_id":"PART_ID"}\n'
        '{"op":"clarify","ticket_id":"TICKET_ID"}\n'
        '{"op":"dispatch","ticket_id":"TICKET_ID","part_id":"PART_ID"}\n'
        '{"op":"escalate","ticket_id":"TICKET_ID"}\n'
        '{"op":"finish"}\n\n'

        "SAFETY AND SCORING RULES:\n"

        "1. A dispatch is irreversible. NEVER dispatch unless voltage matches "
        "exactly, connector matches exactly, and part watts are at least the "
        "ticket's required minimum. Higher wattage is allowed. Any incompatible "
        "dispatch makes the entire batch score zero.\n"

        "2. A part must be available. Use inspect for a recent snapshot in the "
        "ordinary condition; those snapshots are synchronized at batch open. "
        "Use verify for aged snapshots. If policy says both recent and aged "
        "snapshots may be stale, use verify for every candidate. Verify is the "
        "authoritative warehouse result. Do not treat an uninspected catalog "
        "entry as proof of stock.\n"

        "3. Each part has one unit. Do not reuse a part already dispatched in "
        "this batch, even if a later snapshot still says available. Use prior "
        "action history to track consumed part IDs.\n"

        "4. Read the latest APPROVED request/catalog document for each entity. "
        "Ignore drafts. A late-delivered retry of an older revision is not a "
        "new instruction. Duplicate deliveries are not extra tickets or parts. "
        "Normalize mV to V and mW to W. USB-C, USB Type-C and USB Type C are "
        "the same connector; barrel and barrel plug are the same connector.\n"

        "5. Missing wattage is unknown, not zero. If voltage and connector are "
        "known and an available matching 20 W part is confirmed, it satisfies "
        "either possible minimum (10 W or 20 W), so you can dispatch it without "
        "clarifying wattage. Otherwise use clarify to obtain the required watts "
        "before dispatching. Do not guess a missing voltage or connector.\n"

        "6. Tool costs: inspect=1, verify=2, clarify=2. Shared budget is shown "
        "in the observation. Be selective and preserve budget. Dispatch, "
        "escalate and finish cost zero. At most 8 successful model calls are "
        "available for this case; use them efficiently.\n"

        "7. Prefer a compatible, confirmed-available dispatch. Escalate only "
        "when no compatible available part exists, or required facts cannot be "
        "established safely within the remaining budget. Never dispatch merely "
        "to avoid escalation. Decide every ticket; finish only when all are "
        "decided.\n"

        "8. After inspect/verify/clarify, use the returned result before "
        "deciding. Dispatch acknowledgements do NOT reveal correctness or "
        "fulfillment. Do not infer correctness from an acknowledgement.\n\n"

        "CURRENT OBSERVATION (JSON):\n"
    )

    payload = {
        "observation": compact,
        "recent_action_and_result_history": history,
    }

    serialized = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )

    prompt = instructions + serialized

    if len(prompt) > MAX_MESSAGE_CHARS:
        payload["recent_action_and_result_history"] = history[-4:]
        compact.pop("data_quality", None)
        payload["observation"] = compact

        serialized = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        )

        prompt = instructions + serialized

    if len(prompt) > MAX_MESSAGE_CHARS:
        for key in ("current_approved_catalog_documents",):
            docs = compact.get(key, [])
            compact[key] = docs[:12]

        payload["observation"] = compact

        prompt = instructions + json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        )

    return prompt[:MAX_MESSAGE_CHARS]


def decide(observation, state):
    """Return exactly {'action': world_action, 'state': JSON_safe_state}."""
    observation = observation if isinstance(observation, dict) else {}
    state = dict(state or {})
    history = list(state.get("history", []))

    if "llm_response" in observation:
        try:
            action = _extract_json_object(
                observation.get("llm_response")
            )

            if not _validate_world_action(action, observation):
                raise ValueError("Invalid world action or unknown ID")

        except Exception:
            action = _safe_handoff(observation)

        history.append({
            "kind": "model_decision",
            "action": action,
            "result": observation.get("result"),
        })

        state["history"] = history[-16:]

        return {"action": action, "state": state}

    if "result" in observation:
        history.append({
            "kind": "tool_result",
            "result": observation.get("result")
        })

    if observation.get("done"):
        state["history"] = history[-16:]

        return {
            "action": {"op": "finish"},
            "state": state
        }

    calls = int(state.get("model_calls", 0) or 0)

    if calls >= MAX_MODEL_CALLS:
        action = _safe_handoff(observation)
        state["history"] = history[-16:]

        return {
            "action": action,
            "state": state
        }

    prompt = _build_prompt(
        observation,
        {"history": history}
    )

    state["model_calls"] = calls + 1
    state["history"] = history[-16:]

    return {
        "action": {
            "op": "llm",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        "state": state,
    }