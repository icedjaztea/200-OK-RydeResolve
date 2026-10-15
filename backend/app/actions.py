"""Mock financial ledger. Zero connection to actual card/driver wallet APIs."""
from __future__ import annotations
import hashlib
from .evidence import now


def execute_mock(repo,case,disposition,amount):
    if disposition not in ('refund','credit','no_action','reject_claim'):
        raise ValueError('Only reviewed/validated dispositions are executable')
    action_key=f"{case['case_id']}:{case.get('revision',0)}:{disposition}:{float(amount):.2f}"
    # A deterministic receipt and Firestore document create() make retries idempotent.
    receipt='MOCK-'+hashlib.sha256(action_key.encode()).hexdigest()[:16].upper()
    action={'action_key':action_key,'case_id':case['case_id'], 'disposition':disposition,
            'amount':float(amount),'currency':'SGD','receipt':receipt,
            'status':'COMPLETED_SIMULATED','simulated':True,'created_at':now()}
    existing,created=repo.create_action(action_key,action)
    return existing,created
