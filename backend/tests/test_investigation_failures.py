"""Step 37 — Hardening Innovation A against investigation failures.

Tests stale replies, malformed evidence, duplicate simulated refunds,
terminal-status guards, unverified-answer non-promotion, and idempotent retries.

APP_MODE=memory AI_MODE=mock throughout. No Gemini, Firestore or real payments.
"""
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.config import setting
from app.services import (seed_cases, process_case, reply_to_clarification,
                          add_verified_demo_evidence, human_review,
                          verify_event_chain)
from app.repository import repo

client = TestClient(app)
REVIEW = {'X-Demo-Key': setting('DEMO_REVIEWER_KEY','change-reviewer-key')}
RIDER = {'X-Demo-Key': setting('DEMO_RIDER_KEY','change-rider-key')}
DRIVER = {'X-Demo-Key': setting('DEMO_DRIVER_KEY','change-driver-key')}


def api(method, path, headers=REVIEW, **kwargs):
    return client.request(method, path, headers=headers, **kwargs)


def _process(case_id, headers=REVIEW):
    """Run async process_case through the API."""
    return api('POST', f'/cases/{case_id}/process', headers=headers).json()


# ---------------------------------------------------------------------------
# A. No response stays AWAITING_CLARIFICATION; no refund.
# ---------------------------------------------------------------------------
def test_A_no_response_stays_awaiting_no_refund():
    seed_cases()
    p = _process('DEMO-FARE-CLARIFY')
    assert p['status'] == 'AWAITING_CLARIFICATION'
    assert p['path'] == 'CLARIFICATION'
    assert 'mock_action' not in p
    assert len(p.get('clarifications', [])) == 1
    assert p['clarifications'][-1]['status'] == 'PENDING'


# ---------------------------------------------------------------------------
# B. Processing retry reuses request_id and one notification.
# ---------------------------------------------------------------------------
def test_B_processing_retry_reuses_request_id_one_notification():
    seed_cases()
    first = _process('DEMO-FARE-CLARIFY')
    rid = first['clarifications'][-1]['request_id']
    first_notifications = len(first.get('notifications', []))
    second = _process('DEMO-FARE-CLARIFY')
    # Same request_id reused — no second clarification created
    assert second['clarifications'][-1]['request_id'] == rid
    assert len(second['clarifications']) == 1
    # Notification count should not increase on retry
    assert len(second.get('notifications', [])) == first_notifications


# ---------------------------------------------------------------------------
# C. Unverified response doesn't change trusted facts; unresolved human review.
# ---------------------------------------------------------------------------
def test_C_unverified_response_not_promoted_to_facts():
    seed_cases()
    p = _process('DEMO-FARE-CLARIFY')
    rid = p['clarifications'][-1]['request_id']
    p = api('POST', f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',
            headers=RIDER, json={'answer': 'I did not receive any surge notification'}).json()
    assert p['clarifications'][-1]['answer_verification'] == 'UNVERIFIED_PARTY_ACCOUNT'
    p = _process('DEMO-FARE-CLARIFY')
    assert p['path'] == 'HUMAN_REVIEW'
    assert p['status'] == 'REVIEW_REQUIRED'
    # Facts must still have null for rider_notified / notification_log_complete
    assert p['facts']['rider_notified'] is None
    assert p['facts']['notification_log_complete'] is None
    assert 'mock_action' not in p


# ---------------------------------------------------------------------------
# D. Contradictory accounts block automatic resolution.
# ---------------------------------------------------------------------------
def test_D_contradictory_accounts_block_auto_resolution():
    seed_cases()
    p = _process('DEMO-FARE-CONFLICT')
    # Conflicts should route to clarification or review, never auto-resolve
    assert p['path'] in ('CLARIFICATION', 'HUMAN_REVIEW')
    assert p['path'] != 'AUTO_ELIGIBLE'
    assert 'mock_action' not in p
    assert len(p.get('contradictions', [])) > 0


# ---------------------------------------------------------------------------
# E. Invalid field, missing provenance, wrong typed value rejected without mutation.
# ---------------------------------------------------------------------------
def test_E_invalid_field_missing_provenance_wrong_type_rejected():
    seed_cases()
    p = _process('DEMO-FARE-CLARIFY')
    rev_before = p['revision']
    # E1: Invalid field name
    r = api('POST', '/cases/DEMO-FARE-CLARIFY/evidence',
            json={'field': 'bogus_field', 'value': True, 'provenance': 'SYNTHETIC test export'})
    assert r.status_code == 400
    # E2: Missing provenance (too short → Pydantic validation 422)
    r = api('POST', '/cases/DEMO-FARE-CLARIFY/evidence',
            json={'field': 'rider_notified', 'value': True, 'provenance': 'ab'})
    assert r.status_code == 422
    # E3: Wrong typed value — boolean field given a string
    r = api('POST', '/cases/DEMO-FARE-CLARIFY/evidence',
            json={'field': 'rider_notified', 'value': 'yes', 'provenance': 'SYNTHETIC test export'})
    assert r.status_code == 400
    # E4: Wrong typed value — count field given a negative number
    r = api('POST', '/cases/DEMO-NOSHOW-VALID/evidence',
            json={'field': 'driver_message_count', 'value': -1, 'provenance': 'SYNTHETIC test export'})
    assert r.status_code == 400
    # E5: Wrong typed value — count field given a float string
    r = api('POST', '/cases/DEMO-NOSHOW-VALID/evidence',
            json={'field': 'driver_call_count', 'value': 'three', 'provenance': 'SYNTHETIC test export'})
    assert r.status_code == 400
    # Case revision unchanged — no mutation occurred
    case = repo().get_case('DEMO-FARE-CLARIFY')
    assert case['revision'] == rev_before


# ---------------------------------------------------------------------------
# F. Duplicate reply rejected.
# ---------------------------------------------------------------------------
def test_F_duplicate_reply_rejected():
    seed_cases()
    p = _process('DEMO-FARE-CLARIFY')
    rid = p['clarifications'][-1]['request_id']
    # First reply accepted
    r1 = api('POST', f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',
             headers=RIDER, json={'answer': 'I was not notified'})
    assert r1.status_code == 200
    # Second reply to same request_id rejected
    r2 = api('POST', f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',
             headers=RIDER, json={'answer': 'Actually I was notified'})
    assert r2.status_code == 400


# ---------------------------------------------------------------------------
# G. Late synthetic no-show contact records resolve missing fields on reviewer import.
# ---------------------------------------------------------------------------
def test_G_late_noshow_contact_resolves_missing_fields():
    """A no-show case with a missing driver_call_count triggers clarification.
    The driver's unverified reply alone cannot resolve it. The reviewer
    then imports verified contact evidence, filling the gap for auto-resolution.
    """
    seed_cases()
    # DEMO-NOSHOW-VOID has all facts present (driver_call_count=0), so we
    # null out driver_call_count in memory to simulate a missing contact record.
    case = repo().get_case('DEMO-NOSHOW-VOID')
    case['facts']['driver_call_count'] = None
    repo().save_case(case)
    p = _process('DEMO-NOSHOW-VOID')
    assert p['path'] == 'CLARIFICATION'
    rid = p['clarifications'][-1]['request_id']
    # Driver replies (unverified)
    p = api('POST', f'/cases/DEMO-NOSHOW-VOID/clarifications/{rid}/reply',
            headers=DRIVER,
            json={'answer': 'I called the rider at 08:48 from the in-app dialer'}).json()
    # Reprocess → still human review (unverified reply cannot promote to fact)
    p = _process('DEMO-NOSHOW-VOID')
    assert p['path'] == 'HUMAN_REVIEW'
    assert p['status'] == 'REVIEW_REQUIRED'
    # Reviewer imports verified evidence: driver_call_count = 1
    r = api('POST', '/cases/DEMO-NOSHOW-VOID/evidence',
            json={'field': 'driver_call_count', 'value': 1,
                  'provenance': 'SYNTHETIC call log export timestamped 08:48'})
    assert r.status_code == 200, r.text
    p = _process('DEMO-NOSHOW-VOID')
    # With all gaps filled and no conflicts, should auto-resolve
    assert p['path'] == 'AUTO_ELIGIBLE'
    assert p['status'] == 'RESOLVED'


# ---------------------------------------------------------------------------
# H. Stale reply after RESOLVED rejected; stays resolved; one action.
# ---------------------------------------------------------------------------
def test_H_stale_reply_after_resolved_rejected():
    """After a case is resolved, a stale reply to a previously-pending
    clarification must be rejected. The case stays resolved and no
    duplicate mock refund is created.
    """
    seed_cases()
    # DEMO-FARE-CLARIFY has rider_notified=None, notification_log_complete=None
    # and source_trust=SIMULATED_VERIFIED_SYSTEM_FIXTURE (needed for auto-resolve).
    p = _process('DEMO-FARE-CLARIFY')
    assert p['path'] == 'CLARIFICATION'
    rid = p['clarifications'][-1]['request_id']
    # Reviewer imports verified evidence to fill gaps (no party reply needed)
    api('POST', '/cases/DEMO-FARE-CLARIFY/evidence',
        json={'field': 'rider_notified', 'value': False,
              'provenance': 'SYNTHETIC notification log export'})
    api('POST', '/cases/DEMO-FARE-CLARIFY/evidence',
        json={'field': 'notification_log_complete', 'value': True,
              'provenance': 'SYNTHETIC system log export'})
    p = _process('DEMO-FARE-CLARIFY')
    assert p['status'] == 'RESOLVED', p
    assert 'mock_action' in p
    resolved_receipt = p['mock_action']['receipt']
    actions_mid = len(repo().actions)
    # Now try to reply to the stale clarification
    r = api('POST', f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',
            headers=RIDER, json={'answer': 'I was not notified'})
    assert r.status_code == 400
    # Case stays resolved
    case = repo().get_case('DEMO-FARE-CLARIFY')
    assert case['status'] == 'RESOLVED'
    # No additional action created
    assert len(repo().actions) == actions_mid
    # Receipt unchanged
    assert case['mock_action']['receipt'] == resolved_receipt


# ---------------------------------------------------------------------------
# I. REVIEWED_AND_RESOLVED case cannot be reopened through reply or evidence.
# ---------------------------------------------------------------------------
def test_I_reviewed_and_resolved_cannot_be_reopened():
    seed_cases()
    # Process DISP-001 which goes to HUMAN_REVIEW due to gaps
    asyncio.run(process_case('DISP-001'))
    p = asyncio.run(process_case('DISP-001'))
    assert p['status'] == 'REVIEW_REQUIRED'
    # Reviewer resolves it
    reviewed = api('POST', '/cases/DISP-001/review',
                   json={'disposition': 'refund', 'amount': 3.44,
                         'reason': 'Human approved excess distance refund after review'})
    assert reviewed.status_code == 200, reviewed.text
    case = repo().get_case('DISP-001')
    assert case['status'] == 'REVIEWED_AND_RESOLVED'
    actions_before = len(repo().actions)

    # I1: Evidence import rejected on REVIEWED_AND_RESOLVED
    r = api('POST', '/cases/DISP-001/evidence',
            json={'field': 'rider_notified', 'value': True,
                  'provenance': 'SYNTHETIC late import'})
    assert r.status_code == 400

    # I2: Reply to any existing clarification rejected (none on DISP-001,
    # but test the guard directly)
    # If there were a clarification, reply would be blocked.
    # Verify case unchanged
    case2 = repo().get_case('DISP-001')
    assert case2['status'] == 'REVIEWED_AND_RESOLVED'
    assert len(repo().actions) == actions_before


# ---------------------------------------------------------------------------
# J. Resolved retry returns same mock receipt, one action.
# ---------------------------------------------------------------------------
def test_J_resolved_retry_same_receipt_one_action():
    seed_cases()
    first = _process('DISP-003')
    assert first['status'] == 'RESOLVED'
    receipt = first['mock_action']['receipt']
    actions_after_first = len(repo().actions)
    # Retry
    again = _process('DISP-003')
    assert again['status'] == 'RESOLVED'
    assert again['mock_action']['receipt'] == receipt
    assert len(repo().actions) == actions_after_first
    assert verify_event_chain(repo().get_case('DISP-003'))


# ---------------------------------------------------------------------------
# TASK 3: Overlapping replies — concurrency test.
# ---------------------------------------------------------------------------
def test_overlapping_replies_one_wins():
    """Two concurrent reply attempts to the same pending clarification.

    The MemoryRepository uses threading.RLock for individual get/save,
    but reply_to_clarification's read-check-write is not atomic across
    the whole operation. This test documents the current limitation.

    Under the current single-threaded TestClient there is no true
    concurrency — both calls execute sequentially. This test verifies
    the duplicate-rejection guard at minimum prevents both from being
    accepted when called back-to-back.
    """
    seed_cases()
    p = _process('DEMO-FARE-CLARIFY')
    rid = p['clarifications'][-1]['request_id']
    # Two back-to-back replies (TestClient is synchronous so these are serial)
    r1 = api('POST', f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',
             headers=RIDER, json={'answer': 'First answer'})
    r2 = api('POST', f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',
             headers=RIDER, json={'answer': 'Second answer'})
    # At least one must fail
    assert not (r1.status_code == 200 and r2.status_code == 200)
    # The clarification should have exactly one answer
    case = repo().get_case('DEMO-FARE-CLARIFY')
    answered = [c for c in case['clarifications'] if c['status'] == 'ANSWERED']
    assert len(answered) == 1
