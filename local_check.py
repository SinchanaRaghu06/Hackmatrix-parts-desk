"""Check every initial controller request in a selected public file.
Run python local_check.py [training.json|practice.json|adaptation.json].
This checks JSON only, not model inference, world tools or outcome scores.
"""
import json
from pathlib import Path
import sys
from solution import decide

if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('practice.json')
    examples = json.loads(path.read_text())
    assert isinstance(examples, list) and examples, 'Expected nonempty public examples'
    for sample in examples:
        result = decide(sample['observation'], {})
        assert isinstance(result, dict) and set(result) == {'action', 'state'}
        assert isinstance(result['state'], dict)
        assert isinstance(result['action'], dict) and result['action']['op'] == 'llm'
        json.dumps(result, allow_nan=False)
    print(f'{len(examples)} controller requests checked; configure and check your team gateway in the portal.')
