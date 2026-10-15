"""Explicit TEAM signoff of the supplied draft policy->rulebook contract.
This does NOT imply Ryde or the hackathon organizers approved our interpretation.
"""
import argparse, json
from datetime import datetime, timezone
from app.policy import contract_report, load_rulebook
from app.config import signoff_path

p=argparse.ArgumentParser()
p.add_argument('--reviewer',required=True)
p.add_argument('--acknowledge',choices=['I_REVIEWED_POLICY_AMBIGUITIES'],required=True)
a=p.parse_args()
r=contract_report()
if not r['valid']:
    raise SystemExit(f"Cannot sign off invalid contract: {r['problems']}")
value={'team_review_acknowledged':True,'reviewer':a.reviewer,
       'reviewed_at':datetime.now(timezone.utc).isoformat(),
       'source_sha256':r['source_sha256'],'policy_version':r['policy_version'],
       'rulebook_version':load_rulebook()['version'],
       'scope':'synthetic_hackathon_demo_only_not_ryde_approval'}
path=signoff_path();path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(value,indent=2)+'\n')
print('TEAM SIGNOFF CREATED:',path)
