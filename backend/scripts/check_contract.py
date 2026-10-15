import json
from app.policy import contract_report, signoff_valid
x=contract_report();x['team_signoff_valid']=signoff_valid()
print(json.dumps(x,indent=2))
if not x['valid']:
    raise SystemExit(1)
