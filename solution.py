
    # Save the result of the preceding world action before processing next step.
    _record_result(observation, state)

    # The relay returns model text in observation.llm_response.
    if "llm_response" in observation:
        try:
            parsed = _parse_json(observation["llm_response"])
            if not isinstance(parsed, dict):
                raise ValueError("Model response must be a JSON object")

            # Preferred output: {"action": {...}, "requirements": {...}}.
            # Also accept the starter's plain world-action JSON.
            if isinstance(parsed.get("action"), dict):
                action = parsed["action"]
                _remember_requirements(parsed, state)
            else:
                action = parsed

            if not _valid_shape(action, observation):
                action = _fallback(observation)
            elif action.get("op") == "dispatch":
                action, _reason = _validate_dispatch(action, observation, state)
                if not _valid_shape(action, observation):
                    action = _fallback(observation)

            state["last_action"] = dict(action)
            state["history"].append({"action": dict(action)})
            return {"action": action, "state": state}

        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            action = _fallback(observation)
            state["last_action"] = dict(action)
            state["history"].append({"action": dict(action), "model_parse_error": True})
            return {"action": action, "state": state}

    # No more than eight successful model calls are allowed per case.
    if state.get("model_calls", 0) >= MAX_MODEL_CALLS:
        action = _fallback(observation)
        state["last_action"] = dict(action)
        return {"action": action, "state": state}

    if observation.get("done"):
        action = {"op": "finish"}
        state["last_action"] = dict(action)
        return {"action": action, "state": state}

    if "result" in observation:
        state["history"].append({"result": observation["result"]})

    state["model_calls"] = state.get("model_calls", 0) + 1

    system_prompt = (
        "You operate a fictional workshop parts desk. Return ONLY one JSON object. "
        "Preferred format: {\"action\": WORLD_ACTION, \"requirements\": "
        "{\"ticket_id\":\"...\",\"voltage\":number_or_null,\"connector\":\"..._or_null\","
        "\"minimum_wattage\":number_or_null}}. The requirements object is required "
        "when you have interpreted a ticket; use null for unknown fields. "
        "WORLD_ACTION must be exactly one of: "
        "{\"op\":\"inspect\",\"part_id\":\"P...\"}, "
        "{\"op\":\"verify\",\"part_id\":\"P...\"}, "
        "{\"op\":\"clarify\",\"ticket_id\":\"T...\"}, "
        "{\"op\":\"dispatch\",\"ticket_id\":\"T...\",\"part_id\":\"P...\"}, "
        "{\"op\":\"escalate\",\"ticket_id\":\"T...\"}, or {\"op\":\"finish\"}. "
        "Use only IDs present in the observation. Match voltage and connector exactly; "
        "part watts must be >= minimum requested wattage. Never dispatch if a requirement "
        "is unknown, compatibility is uncertain, or stock is not established. "
        "Inspect gives desk snapshot; verify gives authoritative warehouse stock. "
        "Follow the current observation policy: if it says recent snapshots may be stale, "
        "verify stock before dispatch; otherwise recent snapshots are synchronized and "
        "aged snapshots need verification. Clarify if the customer request leaves required "
        "wattage unclear. Tool costs and budget are in observation. Avoid needless calls. "
        "Dispatch/escalate decisions are irreversible. Never use world/action feedback as "
        "correctness feedback; dispatch only acknowledges recording. Escalate rather than "
        "guess. Do not use markdown fences."
    )

    payload = {
        "observation": observation,
        "controller_evidence": {
            "part_evidence": state.get("part_evidence", {}),
            "ticket_requirements": state.get("ticket_requirements", {}),
            "clarifications": state.get("clarifications", {}),
            "used_parts": state.get("used_parts", []),
            "history": state.get("history", []),
        },
        "instructions": (
            "Choose exactly one next world action. If the latest result is a clarification, "
            "incorporate its reply into requirements. If a request is fully resolved, decide "
            "it now. Do not return an action for an already-decided ticket."
        ),
    }

    prompt = system_prompt + "\n\nINPUT:\n" + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )

    return {
        "action": {
            "op": "llm",
            "messages": [{"role": "user", "content": prompt}],
            "max_output_tokens": 700,
        },
        "state": state,
    }
