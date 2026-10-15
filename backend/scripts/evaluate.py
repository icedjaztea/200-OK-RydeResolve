import json
from app.services import evaluate_suite
result=evaluate_suite(approved=True)
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['all_passed'] else 1)
