"""Step 39 — Escalation & Reviewer Decision Packet.

Tests the Reviewer Decision Packet endpoint for REVIEW_REQUIRED cases.
Covers DISP-001 (route deviation 4.3 km, proposed 3.44),
DISP-002 (historical fraud flag), safety case (no Judge, SF-5.1/SF-5.2
gate reasons), reviewer authorization/timestamp/receipt, non-safety
candidate labeled PROPOSAL ONLY, safety with NO AI fault/remedy,
and human decision separate from AI recommendation.

APP_MODE=memory AI_MODE=mock throughout.
"""
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.config import setting
from app.services import seed_cases, build_review_packet, human_review
from app.repository import repo

client = TestClient(app)
REVIEW = {'X-Demo-Key': setting('DEMO_REVIEWER_KEY','change-reviewer-key')}
RIDER = {'X-Demo-Key': setting('DEMO_RIDER_KEY','change-rider-key')}


def api(method, path, headers=REVIEW, **kwargs):
    return client.request(method, path, headers=headers, **kwargs)


def _process(case_id, headers=REVIEW):
    return api('POST', f'/cases/{case_id}/process', headers=headers).json()


# ---------------------------------------------------------------------------
# 1. DISP-001: route deviation 4.3 km, proposed 3.44 vs review.
# ---------------------------------------------------------------------------
def test_disp001_route_packet_proposed_vs_review():
    """DISP-001 is a 4.3 km route deviation with excess_distance_fare=3.44.
    The packet shows the candidate amount, gate reasons, and PROPOSAL ONLY label.
    """
    seed_cases()
    p = _process('DISP-001')
    assert p['status'] == 'REVIEW_REQUIRED'
    assert p['path'] == 'HUMAN_REVIEW'

    pkt = api('GET', '/cases/DISP-001/review-packet').json()

    # Case details
    cd = pkt['case_details']
    assert cd['case_id'] == 'DISP-001'
    assert cd['category'] == 'route_deviation'
    assert cd['filed_by'] == 'rider'
    assert cd['policy_version'] == '2.1'
    assert cd['dispute_value'] == 3.44
    assert cd['dispute_value_basis'] == 'amount_in_dispute'

    # Filed-by allegation mentions 4.3 km
    assert '4.3' in pkt['filed_by_allegation']

    # Structured facts include route deviation fields with provenance
    fact_fields = {f['field'] for f in pkt['structured_facts']}
    assert 'actual_distance_km' in fact_fields
    assert 'recommended_distance_km' in fact_fields
    assert 'rider_notified' in fact_fields
    assert 'excess_distance_fare' in fact_fields
    for f in pkt['structured_facts']:
        assert 'provenance' in f
        assert 'verification' in f

    # Candidate policy IDs present
    assert len(pkt['candidate_policy_ids']) > 0
    assert 'RD-1.2' in pkt['candidate_policy_ids'] or 'RD-1.4' in pkt['candidate_policy_ids']

    # Gate reasons present and human-readable
    assert len(pkt['gate_reasons']) > 0
    # Route deviation > 2 km should trigger TH-6.2-ROUTE
    assert any('reviewer' in r.lower() or 'route' in r.lower() for r in pkt['gate_reasons'])

    # Escalation blocking rule IDs present
    assert len(pkt['escalation_blocking_rule_ids']) > 0

    # AI recommendation is proposal only (non-safety)
    assert pkt['ai_recommendation']['is_proposal_only'] is True
    assert pkt['ai_recommendation']['amount'] == 3.44
    assert pkt['ai_recommendation']['disposition'] == 'refund'

    # Safety note should be None (this is not a safety case)
    assert pkt['is_safety'] is False
    assert pkt['safety_note'] is None

    # No human decision yet
    assert pkt['human_decision'] is None

    # Synthetic warning present
    assert 'SYNTHETIC' in pkt['synthetic_warning']

    # Original escalation preserved
    assert pkt['original_escalation'] == 'HUMAN_REVIEW'


# ---------------------------------------------------------------------------
# 2. DISP-002: historical fraud flag.
# ---------------------------------------------------------------------------
def test_disp002_historical_flag_packet():
    """DISP-002 has fraud_flags=1 which triggers TH-6.3 historical flag review."""
    seed_cases()
    p = _process('DISP-002')
    assert p['status'] == 'REVIEW_REQUIRED'

    pkt = api('GET', '/cases/DISP-002/review-packet').json()

    # Case details
    assert pkt['case_details']['case_id'] == 'DISP-002'
    assert pkt['case_details']['category'] == 'no_show_charge'

    # Historical fraud flag gate reason should mention TH-6.3
    assert any('fraud' in r.lower() or 'historical' in r.lower() or 'threshold' in r.lower()
               for r in pkt['gate_reasons'])

    # Escalation blocking rule IDs should include TH-6.3
    assert 'TH-6.3' in pkt['escalation_blocking_rule_ids']

    # PROPOSAL ONLY (non-safety)
    assert pkt['ai_recommendation']['is_proposal_only'] is True
    assert pkt['is_safety'] is False


# ---------------------------------------------------------------------------
# 3. Safety case: no Judge, safety reasons referencing SF-5.1 and SF-5.2.
# ---------------------------------------------------------------------------
def test_safety_no_judge_gate_reasons_sf51_sf52():
    """Safety case: immediate human review, no Judge agent, gate reasons
    reference SF-5.1 and SF-5.2.
    """
    seed_cases()
    p = _process('DEMO-SAFETY-IN-FARE')
    assert p['path'] == 'IMMEDIATE_HUMAN_REVIEW'

    pkt = api('GET', '/cases/DEMO-SAFETY-IN-FARE/review-packet').json()

    # Safety flag
    assert pkt['is_safety'] is True

    # Safety note present — NO AI fault/remedy proposal
    assert pkt['safety_note'] is not None
    assert 'fault' in pkt['safety_note'].lower() or 'remedy' in pkt['safety_note'].lower()

    # Gate reasons reference SF-5.1 and SF-5.2
    all_reasons = ' '.join(pkt['gate_reasons'])
    assert 'SF-5.1' in all_reasons
    assert 'SF-5.2' in all_reasons

    # Escalation blocking rules include SF-5.1 and SF-5.2
    assert 'SF-5.1' in pkt['escalation_blocking_rule_ids']
    assert 'SF-5.2' in pkt['escalation_blocking_rule_ids']

    # No Judge in advocate summaries
    assert 'Judge' not in pkt['advocate_summaries']

    # AI recommendation is undetermined (no remedy proposed)
    assert pkt['ai_recommendation']['disposition'] == 'undetermined'
    assert pkt['ai_recommendation']['amount'] == 0

    # Original escalation preserved as IMMEDIATE_HUMAN_REVIEW
    assert pkt['original_escalation'] == 'IMMEDIATE_HUMAN_REVIEW'


# ---------------------------------------------------------------------------
# 4. Reviewer authorization, timestamp, and one simulated action and audit.
# ---------------------------------------------------------------------------
def test_reviewer_authorization_timestamp_one_action_audit():
    """After reviewer decision: human decision recorded with authorization,
    timestamp, and simulated receipt. Only one mock action and audit chain valid.
    """
    seed_cases()
    _process('DISP-001')
    actions_before = len(repo().actions)

    reviewed = api('POST', '/cases/DISP-001/review',
                   json={'disposition': 'refund', 'amount': 3.44,
                         'reason': 'Human approved excess distance refund after review'})
    assert reviewed.status_code == 200, reviewed.text

    # Only one action created
    assert len(repo().actions) == actions_before + 1

    # Get the packet after review
    pkt = api('GET', '/cases/DISP-001/review-packet').json()

    # Human decision present with all required fields
    hd = pkt['human_decision']
    assert hd is not None
    assert hd['disposition'] == 'refund'
    assert hd['amount'] == 3.44
    assert hd['reason'] == 'Human approved excess distance refund after review'
    assert hd['authorized_by'] == 'demo_reviewer'
    assert hd['timestamp'] is not None
    assert hd['simulated_receipt'] is not None
    assert hd['simulated_receipt'].startswith('MOCK-')

    # AI recommendation separate from human decision
    assert pkt['ai_recommendation']['disposition'] == 'refund'
    assert pkt['ai_recommendation']['amount'] == 3.44
    # Both present, independent fields
    assert pkt['ai_recommendation'] != pkt['human_decision']

    # Audit chain valid
    assert api('GET', '/cases/DISP-001/verify-audit').json()['valid'] is True

    # Original escalation preserved for traceability
    assert pkt['original_escalation'] == 'HUMAN_REVIEW'


# ---------------------------------------------------------------------------
# 5. Non-safety candidate labeled PROPOSAL ONLY; safety has NO AI proposal.
# ---------------------------------------------------------------------------
def test_proposal_only_label_non_safety_vs_safety():
    """Non-safety REVIEW_REQUIRED case has is_proposal_only=True.
    Safety case has safety_note and undetermined disposition.
    """
    seed_cases()

    # Non-safety: DISP-001
    _process('DISP-001')
    pkt_ns = api('GET', '/cases/DISP-001/review-packet').json()
    assert pkt_ns['is_safety'] is False
    assert pkt_ns['ai_recommendation']['is_proposal_only'] is True
    assert pkt_ns['safety_note'] is None
    assert pkt_ns['ai_recommendation']['disposition'] != 'undetermined'

    # Safety: DEMO-SAFETY-IN-FARE
    _process('DEMO-SAFETY-IN-FARE')
    pkt_s = api('GET', '/cases/DEMO-SAFETY-IN-FARE/review-packet').json()
    assert pkt_s['is_safety'] is True
    assert pkt_s['safety_note'] is not None
    assert pkt_s['ai_recommendation']['disposition'] == 'undetermined'
    assert pkt_s['ai_recommendation']['amount'] == 0


# ---------------------------------------------------------------------------
# 6. Packet uses only existing GET /cases/{id} data; no invented fields.
# ---------------------------------------------------------------------------
def test_packet_fields_match_case_data():
    """Verify packet structured_facts match the case's actual facts and evidence.
    No invented evidence, metrics, or rules.
    """
    seed_cases()
    _process('DISP-001')
    case = api('GET', '/cases/DISP-001').json()
    pkt = api('GET', '/cases/DISP-001/review-packet').json()

    # Every structured fact field exists in case.facts
    case_fact_keys = set(case.get('facts', {}).keys())
    for sf in pkt['structured_facts']:
        assert sf['field'] in case_fact_keys, f"Field {sf['field']} not in case facts"

    # Packet gate reasons come from case.gate.reasons
    case_gate_reasons = case.get('gate', {}).get('reasons', [])
    for gr in pkt['gate_reasons']:
        assert gr in case_gate_reasons, f"Gate reason '{gr}' not in case gate reasons"

    # Candidate policy IDs match case routing
    case_routing_ids = case.get('routing', {}).get('candidate_rule_ids', [])
    assert set(pkt['candidate_policy_ids']) == set(case_routing_ids)

    # No extra fabricated fields
    expected_top_keys = {'case_details', 'filed_by_allegation', 'structured_facts',
                         'gaps', 'contradictions', 'clarification_history',
                         'unverified_replies', 'candidate_policy_ids',
                         'escalation_blocking_rule_ids', 'gate_reasons',
                         'advocate_summaries', 'event_traces', 'ai_recommendation',
                         'safety_note', 'human_decision', 'original_escalation',
                         'is_safety', 'synthetic_warning'}
    assert set(pkt.keys()) == expected_top_keys


# ---------------------------------------------------------------------------
# 7. Reviewer-only authorization: non-reviewer cannot access packet.
# ---------------------------------------------------------------------------
def test_review_packet_reviewer_only():
    """Only reviewer key can access the decision packet endpoint."""
    seed_cases()
    _process('DISP-001')

    # Rider cannot access
    r = api('GET', '/cases/DISP-001/review-packet', headers=RIDER)
    assert r.status_code == 403

    # Reviewer can access
    r = api('GET', '/cases/DISP-001/review-packet', headers=REVIEW)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 8. Event traces labeled mock/live.
# ---------------------------------------------------------------------------
def test_event_traces_labeled_mock():
    """Event traces should carry a mode label (MOCK_NOT_MODEL_OUTPUT in mock mode)."""
    seed_cases()
    _process('DISP-001')
    pkt = api('GET', '/cases/DISP-001/review-packet').json()

    assert len(pkt['event_traces']) > 0
    for trace in pkt['event_traces']:
        assert 'mode' in trace
        assert trace['mode'] in ('MOCK_NOT_MODEL_OUTPUT', 'LIVE_ADK')
        # In mock mode, should be MOCK
        assert trace['mode'] == 'MOCK_NOT_MODEL_OUTPUT'
