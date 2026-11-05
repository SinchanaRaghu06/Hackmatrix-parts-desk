"""Frozen controller: submit as solution.py. Gateway/model stays on team infrastructure.
After eight inference requests, conservatively hand off remaining tickets. This
keeps the starter valid when the model spends calls on queries; improve the policy
inside your own frozen controller to make better use of the shared limits.
"""
import json


def decide(observation, state):
    state = dict(state or {})
    if 'llm_response' in observation:
        text = observation['llm_response'].strip()
        if text.startswith('```'):
            text = '\n'.join(text.splitlines()[1:-1])
        action = json.loads(text)
        if not isinstance(action, dict):
            raise ValueError('Model must return an action object')
        state.setdefault('history', []).append({'action':action})
        return {'action':action, 'state':state}
    if state.get('model_calls', 0) >= 8:
        decided = set(observation.get('decided_ticket_ids', []))
        remaining = [t['id'] for t in observation.get('tickets', []) if t['id'] not in decided]
        action = {'op':'escalate', 'ticket_id':remaining[0]} if remaining else {'op':'finish'}
        return {'action':action, 'state':state}
    state['model_calls'] = state.get('model_calls', 0) + 1
    history = state.setdefault('history', [])
    if 'result' in observation:
        history.append({'result':observation['result']})
    prompt = ('Operate the simulated parts desk. Follow the observation policy and tools. '
              'Return only a JSON world action with op and its required arguments. '
              'Use tools selectively; dispatches are irreversible.\n' + json.dumps(
                  {'observation':observation, 'history':history}, ensure_ascii=False))
    return {'action':{'op':'llm', 'messages':[{'role':'user','content':prompt}],
                      'max_output_tokens':512}, 'state':state}
