"""Read the supplied v2.1 policy and separate draft routing index by exact rule id.

Rulebook is a DISCOVERY INDEX, NEVER an execution policy. Do not use eval()
for the condition strings in the supplied JSON.
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from .config import ROOT, signoff_path

POLICY_DIR = ROOT / 'policy'
POLICY_FILE = POLICY_DIR / '02_policy_rules.json'
RULEBOOK_FILE = POLICY_DIR / '04_rulebook.json'
SOURCE_FILE = POLICY_DIR / 'policy_v2.1.md'


def load_policy() -> dict:
    return json.loads(POLICY_FILE.read_text(encoding='utf-8'))


def load_rulebook() -> dict:
    return json.loads(RULEBOOK_FILE.read_text(encoding='utf-8'))


def contract_report() -> dict:
    policy, rulebook = load_policy(), load_rulebook()
    ids = [x['rule_id'] for x in policy['structured_rules']]
    index_ids = [x['rule_id'] for x in rulebook['rule_entries']]
    actual_hash = hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()
    problems = []
    if len(ids) != len(set(ids)) or len(index_ids) != len(set(index_ids)):
        problems.append('Duplicate rule_id found')
    if set(ids) != set(index_ids):
        problems.append('Rulebook/index rule_id sets do not match')
    if rulebook['policy_version'] != policy['version']:
        problems.append('Policy version mismatch')
    if actual_hash != policy['source_sha256'] or actual_hash != rulebook['source_policy_sha256']:
        problems.append('Source policy SHA-256 mismatch')
    if not all(x['read_full_rule_from'] == '02_policy_rules.json' for x in rulebook['rule_entries']):
        problems.append('Rulebook entries do not point to authoritative JSON')
    return {'valid': not problems, 'problems': problems, 'policy_version':policy['version'],
            'rule_count':len(ids), 'index_count':len(index_ids),'source_sha256':actual_hash,
            'policy_status':policy.get('runtime_approval_status'), 'rulebook_status':rulebook.get('status')}


def signoff_valid() -> bool:
    check = contract_report()
    path = signoff_path()
    if not check['valid'] or not path.exists():
        return False
    try:
        approval = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return False
    return bool(approval.get('team_review_acknowledged')) and approval.get('source_sha256') == check['source_sha256'] and approval.get('policy_version') == '2.1' and approval.get('rulebook_version') == load_rulebook()['version'] and bool(approval.get('reviewer'))


def full_rules(rule_ids: list[str]) -> list[dict]:
    rule_map={r['rule_id']: r for r in load_policy()['structured_rules']}
    return [rule_map[i] for i in rule_ids if i in rule_map]


def select_candidates(category: str, narrative: str = '', fraud_flags: int = 0, safety: bool = False) -> dict:
    """Routable candidates include every category rule + cross-cutting safety/value gates.
    Index phrases increase trace information only; they do not establish facts.
    """
    index=load_rulebook()
    rules=[]; evidence=[]; matched=[]
    for row in index['rule_entries']:
        cats=row.get('dispute_categories',[])
        if category in cats or 'all' in cats or (category=='driver_no_show' and 'no_show_charge' in cats):
            rid=row['rule_id']
            if rid=='TH-6.3' and not fraud_flags:
                continue
            if rid in ('SF-5.1','SF-5.2') and not safety:
                # Safety is always screened; cross-cutting check remains visible.
                pass
            rules.append(rid)
            evidence += row.get('evidence_to_fetch',[])
            if any(t.lower() in narrative.lower() for t in row.get('search_phrases',[])):
                matched.append(rid)
    return {'candidate_rule_ids': list(dict.fromkeys(rules)),
            'matched_phrase_rule_ids': matched,
            'evidence_to_fetch': list(dict.fromkeys(evidence)),
            'uncertain_conditions': [], 'safety_screen': 'flag' if safety else 'not_observed',
            'policy_version':index['policy_version'], 'rulebook_version':index['version']}


def lookup_precedents(category: str) -> list[dict]:
    return [p for p in load_policy()['precedents'] if p['category']==category]
