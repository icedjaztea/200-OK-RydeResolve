"""Safe response schemas for Rider/Driver API consumers.

Riders and Drivers receive only case fields that are relevant and safe
for them to see.  Internal Judge reasoning, fraud indicators, reviewer
notes, other parties' clarification messages, and technical traces are
stripped.

Reviewer endpoints continue to return the full case document unchanged.
"""
from __future__ import annotations

from typing import Any


# Fields that a Rider is allowed to see on a case detail.
# Everything else is stripped from the response.
_RIDER_SAFE_KEYS: set[str] = {
    'case_id', 'trip_id', 'category', 'filed_by', 'description',
    'dispute_amount', 'dispute_value_basis', 'status', 'path',
    'policy_version', 'candidate', 'gate', 'mock_action',
    'clarifications',  # filtered per-recipient below
    'notifications',  # filtered per-recipient below
    'synthetic',
    # Reclassification info — parties see what the reviewer classified it as.
    'original_category',
}

# Fields that a Driver is allowed to see on a case detail.
_DRIVER_SAFE_KEYS: set[str] = _RIDER_SAFE_KEYS


def _filter_clarifications(clarifications: list[dict], role: str) -> list[dict]:
    """Return only clarifications directed at this role.

    A rider sees only rider-directed clarifications.
    A driver sees only driver-directed clarifications.
    The reviewer (handled separately) sees all.
    """
    result = []
    for c in clarifications or []:
        if c.get('recipient') == role:
            # Strip internal-only fields from party view.
            safe = {
                'request_id': c.get('request_id'),
                'recipient': c.get('recipient'),
                'question': c.get('question'),
                'status': c.get('status'),
                'created_at': c.get('created_at'),
            }
            if c.get('status') == 'ANSWERED':
                safe['answer'] = c.get('answer')
                safe['answer_verification'] = c.get('answer_verification')
            result.append(safe)
    return result


def _filter_notifications(notifications: list[dict], role: str) -> list[dict]:
    """Return only notifications directed at this role (or 'all')."""
    result = []
    for n in notifications or []:
        recipient = n.get('recipient')
        if recipient == role or recipient == 'all':
            safe = {
                'kind': n.get('kind'),
                'recipient': n.get('recipient'),
                'message': n.get('message'),
                'status': n.get('status'),
                'created_at': n.get('created_at'),
            }
            if n.get('receipt'):
                safe['receipt'] = n['receipt']
            result.append(safe)
    return result


def _strip_case(case: dict, safe_keys: set[str], role: str) -> dict:
    """Return a copy of the case with only safe keys and filtered sub-collections."""
    result: dict[str, Any] = {}
    for key in safe_keys:
        if key in case:
            result[key] = case[key]

    # Filter sub-collections per-recipient.
    result['clarifications'] = _filter_clarifications(case.get('clarifications', []), role)
    result['notifications'] = _filter_notifications(case.get('notifications', []), role)

    # Never expose internal-only top-level fields even if they exist.
    for forbidden in ('agent_outputs', 'agent_trace', 'routing', 'sla_routing',
                      'gaps', 'contradictions', 'events', 'review',
                      'learning_proposal_id', 'original_escalation',
                      'evidence_snapshot_hash', 'revision', 'source_trust',
                      'fraud_flags', 'rulebook_version', 'evidence'):
        result.pop(forbidden, None)

    return result


def safe_case_for_rider(case: dict) -> dict:
    """Return a rider-safe view of a case."""
    return _strip_case(case, _RIDER_SAFE_KEYS, 'rider')


def safe_case_for_driver(case: dict) -> dict:
    """Return a driver-safe view of a case."""
    return _strip_case(case, _DRIVER_SAFE_KEYS, 'driver')


def safe_case_list_item(case: dict, role: str) -> dict:
    """Return a safe summary item for the case list endpoint.

    The list endpoint already returned a minimal shape; this ensures
    it stays minimal and consistent.
    """
    return {
        'case_id': case.get('case_id'),
        'category': case.get('category'),
        'status': case.get('status'),
        'path': case.get('path'),
        'dispute_amount': case.get('dispute_amount'),
        'filed_by': case.get('filed_by'),
    }
