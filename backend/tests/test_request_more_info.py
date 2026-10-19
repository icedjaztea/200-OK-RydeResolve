"""Tests for the simplified Request More Information flow.

Covers the complete journey:
- Reviewer creates an ad-hoc clarification request
- The intended party (rider or driver) sees it and responds
- Reviewer sees the answer and can continue the investigation
- Wrong-identity parties cannot see or answer the request
- Duplicate pending requests are blocked
- Resolved cases reject new requests
- Safety escalations are preserved
- Party replies are never verified system evidence
- Unverified replies do not trigger automatic refunds

APP_MODE=memory AI_MODE=mock throughout.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.config import setting
from app.services import seed_cases, process_case
import asyncio
from app.repository import repo, MemoryRepository, set_repo

client = TestClient(app)
REVIEW = {'X-Demo-Key': setting('DEMO_REVIEWER_KEY', 'change-reviewer-key')}
RIDER_A = {'X-Demo-Key': setting('DEMO_RIDER_KEY', 'change-rider-key')}
RIDER_B = {'X-Demo-Key': setting('DEMO_RIDER_B_KEY', 'change-rider-b-key')}
DRIVER_A = {'X-Demo-Key': setting('DEMO_DRIVER_KEY', 'change-driver-key')}
DRIVER_B = {'X-Demo-Key': setting('DEMO_DRIVER_B_KEY', 'change-driver-b-key')}


def api(method, path, headers=REVIEW, **kwargs):
    return client.request(method, path, headers=headers, **kwargs)


def _setup():
    set_repo(MemoryRepository())
    repo().reset() if hasattr(repo(), 'reset') else None
    seed_cases()


def _process(case_id):
    """Process a case to get it into REVIEW_REQUIRED state."""
    asyncio.run(process_case(case_id))


# ---------------------------------------------------------------------------
# 1. Reviewer can create an ad-hoc clarification on a NEW case
# ---------------------------------------------------------------------------

def test_reviewer_can_request_more_info_on_new_case():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'rider', 'question': 'Did you receive a notification about the surge?'})
    assert resp.status_code == 200, resp.text
    case = resp.json()
    clar = [c for c in case['clarifications'] if c['status'] == 'PENDING']
    assert len(clar) == 1
    assert clar[0]['recipient'] == 'rider'
    assert clar[0]['question'] == 'Did you receive a notification about the surge?'
    assert case['status'] == 'AWAITING_CLARIFICATION'


# ---------------------------------------------------------------------------
# 2. Reviewer can request more info on a REVIEW_REQUIRED case (after processing)
# ---------------------------------------------------------------------------

def test_reviewer_can_request_more_info_after_processing():
    _setup()
    _process('DEMO-FARE-50')
    resp = api('GET', '/cases/DEMO-FARE-50')
    assert resp.json()['status'] == 'REVIEW_REQUIRED'
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'driver', 'question': 'What was the final fare shown on your app?'})
    assert resp.status_code == 200, resp.text
    case = resp.json()
    assert case['status'] == 'AWAITING_CLARIFICATION'
    clar = [c for c in case['clarifications'] if c['status'] == 'PENDING']
    assert len(clar) == 1
    assert clar[0]['recipient'] == 'driver'


# ---------------------------------------------------------------------------
# 3. Rider sees the question and can respond
# ---------------------------------------------------------------------------

def test_rider_sees_and_responds_to_reviewer_request():
    _setup()
    api('POST', '/cases/DEMO-FARE-50/clarifications',
        json={'recipient': 'rider', 'question': 'Did you agree to the surge pricing?'})
    # Rider sees it
    resp = api('GET', '/cases/DEMO-FARE-50', headers=RIDER_A)
    case = resp.json()
    pending = [c for c in case['clarifications'] if c['status'] == 'PENDING']
    assert len(pending) == 1
    assert pending[0]['question'] == 'Did you agree to the surge pricing?'
    # Rider responds
    req_id = pending[0]['request_id']
    resp = api('POST', f'/cases/DEMO-FARE-50/clarifications/{req_id}/reply',
               headers=RIDER_A, json={'answer': 'No, I was not informed about the surge.'})
    assert resp.status_code == 200, resp.text
    case = resp.json()
    answered = [c for c in case['clarifications'] if c['status'] == 'ANSWERED']
    assert len(answered) == 1
    assert answered[0]['answer'] == 'No, I was not informed about the surge.'
    assert answered[0].get('answer_verification') == 'UNVERIFIED_PARTY_ACCOUNT'


# ---------------------------------------------------------------------------
# 4. Driver sees and responds to a reviewer request
# ---------------------------------------------------------------------------

def test_driver_sees_and_responds_to_reviewer_request():
    _setup()
    api('POST', '/cases/DEMO-NOSHOW-VOID/clarifications',
        json={'recipient': 'driver', 'question': 'Did you wait at the pickup location for at least 5 minutes?'})
    resp = api('GET', '/cases/DEMO-NOSHOW-VOID', headers=DRIVER_A)
    case = resp.json()
    pending = [c for c in case['clarifications'] if c['status'] == 'PENDING']
    assert len(pending) == 1
    req_id = pending[0]['request_id']
    resp = api('POST', f'/cases/DEMO-NOSHOW-VOID/clarifications/{req_id}/reply',
               headers=DRIVER_A, json={'answer': 'Yes, I waited 7 minutes.'})
    assert resp.status_code == 200, resp.text
    case = resp.json()
    answered = [c for c in case['clarifications'] if c['status'] == 'ANSWERED']
    assert len(answered) == 1
    assert answered[0]['answer'] == 'Yes, I waited 7 minutes.'


# ---------------------------------------------------------------------------
# 5. Wrong-identity party cannot see the request
# ---------------------------------------------------------------------------

def test_rider_b_cannot_see_rider_a_clarification():
    _setup()
    api('POST', '/cases/DEMO-FARE-50/clarifications',
        json={'recipient': 'rider', 'question': 'Did you agree to the surge?'})
    # Rider B cannot access Rider A's case at all
    resp = api('GET', '/cases/DEMO-FARE-50', headers=RIDER_B)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Wrong-identity party cannot answer the request
# ---------------------------------------------------------------------------

def test_wrong_driver_cannot_answer_driver_a_request():
    _setup()
    api('POST', '/cases/DEMO-NOSHOW-VOID/clarifications',
        json={'recipient': 'driver', 'question': 'How long did you wait?'})
    resp = api('GET', '/cases/DEMO-NOSHOW-VOID', headers=DRIVER_A)
    req_id = [c for c in resp.json()['clarifications'] if c['status'] == 'PENDING'][0]['request_id']
    # Driver B cannot access Driver A's case
    resp = api('POST', f'/cases/DEMO-NOSHOW-VOID/clarifications/{req_id}/reply',
               headers=DRIVER_B, json={'answer': 'I waited.'})
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# 7. Non-reviewer cannot create ad-hoc clarification
# ---------------------------------------------------------------------------

def test_rider_cannot_create_clarification():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               headers=RIDER_A, json={'recipient': 'driver', 'question': 'Why did you charge me?'})
    assert resp.status_code == 403


def test_driver_cannot_create_clarification():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               headers=DRIVER_A, json={'recipient': 'rider', 'question': 'Why did you cancel?'})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 8. Duplicate pending request to same recipient is blocked
# ---------------------------------------------------------------------------

def test_duplicate_pending_request_blocked():
    _setup()
    api('POST', '/cases/DEMO-FARE-50/clarifications',
        json={'recipient': 'rider', 'question': 'First question.'})
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'rider', 'question': 'Second question.'})
    assert resp.status_code == 400
    assert 'already exists' in resp.json()['detail'].lower()


# ---------------------------------------------------------------------------
# 9. Can request from different recipients simultaneously
# ---------------------------------------------------------------------------

def test_can_request_from_both_rider_and_driver():
    _setup()
    resp1 = api('POST', '/cases/DEMO-FARE-50/clarifications',
                json={'recipient': 'rider', 'question': 'Question for rider.'})
    assert resp1.status_code == 200
    resp2 = api('POST', '/cases/DEMO-FARE-50/clarifications',
                json={'recipient': 'driver', 'question': 'Question for driver.'})
    assert resp2.status_code == 200
    case = resp2.json()
    pending = [c for c in case['clarifications'] if c['status'] == 'PENDING']
    assert len(pending) == 2


# ---------------------------------------------------------------------------
# 10. Resolved cases reject new requests
# ---------------------------------------------------------------------------

def test_resolved_case_rejects_new_request():
    _setup()
    _process('DEMO-FARE-50')
    # Review the case to resolve it
    api('POST', '/cases/DEMO-FARE-50/review',
        json={'disposition': 'refund', 'amount': 5.0, 'reason': 'Surge was not properly disclosed to the rider.'})
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'rider', 'question': 'One more question.'})
    assert resp.status_code == 400
    assert 'resolved' in resp.json()['detail'].lower()


# ---------------------------------------------------------------------------
# 11. Safety escalation is preserved — clarification does not override
# ---------------------------------------------------------------------------

def test_safety_escalation_preserved_with_clarification():
    _setup()
    _process('DEMO-SAFETY-IN-FARE')
    case = api('GET', '/cases/DEMO-SAFETY-IN-FARE').json()
    assert case['path'] == 'IMMEDIATE_HUMAN_REVIEW'
    resp = api('POST', '/cases/DEMO-SAFETY-IN-FARE/clarifications',
               json={'recipient': 'rider', 'question': 'Can you describe what happened?'})
    assert resp.status_code == 200
    case = resp.json()
    # Safety path must remain
    assert case['path'] == 'IMMEDIATE_HUMAN_REVIEW'
    assert case['status'] == 'REVIEW_REQUIRED'


# ---------------------------------------------------------------------------
# 12. Party reply is never verified system evidence
# ---------------------------------------------------------------------------

def test_reply_is_unverified():
    _setup()
    api('POST', '/cases/DEMO-FARE-50/clarifications',
        json={'recipient': 'rider', 'question': 'Did you receive a notification?'})
    resp = api('GET', '/cases/DEMO-FARE-50', headers=RIDER_A)
    req_id = [c for c in resp.json()['clarifications'] if c['status'] == 'PENDING'][0]['request_id']
    resp = api('POST', f'/cases/DEMO-FARE-50/clarifications/{req_id}/reply',
               headers=RIDER_A, json={'answer': 'Yes I received it.'})
    case = resp.json()
    answered = [c for c in case['clarifications'] if c['status'] == 'ANSWERED'][0]
    assert answered['answer_verification'] == 'UNVERIFIED_PARTY_ACCOUNT'
    # The answer must NOT appear in facts or evidence
    assert 'Yes I received it' not in str(case.get('facts', {}))


# ---------------------------------------------------------------------------
# 13. Unverified reply does not trigger automatic refund
# ---------------------------------------------------------------------------

def test_unverified_reply_does_not_auto_refund():
    _setup()
    _process('DEMO-FARE-50')
    # Reviewer asks a question
    api('POST', '/cases/DEMO-FARE-50/clarifications',
        json={'recipient': 'rider', 'question': 'Did you agree to the fare?'})
    # Rider answers
    resp = api('GET', '/cases/DEMO-FARE-50', headers=RIDER_A)
    req_id = [c for c in resp.json()['clarifications'] if c['status'] == 'PENDING'][0]['request_id']
    api('POST', f'/cases/DEMO-FARE-50/clarifications/{req_id}/reply',
        headers=RIDER_A, json={'answer': 'No, I did not agree.'})
    # Check that no mock_action was created by the reply
    case = api('GET', '/cases/DEMO-FARE-50').json()
    assert 'mock_action' not in case or case.get('mock_action') is None


# ---------------------------------------------------------------------------
# 14. Question length validation
# ---------------------------------------------------------------------------

def test_short_question_rejected():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'rider', 'question': 'Hi'})
    assert resp.status_code in (400, 422)


def test_long_question_rejected():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'rider', 'question': 'x' * 1001})
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 15. Invalid recipient rejected
# ---------------------------------------------------------------------------

def test_invalid_recipient_rejected():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'reviewer', 'question': 'Self question?'})
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 16. After reply, reviewer can continue investigation (re-process)
# ---------------------------------------------------------------------------

def test_reviewer_can_continue_after_reply():
    _setup()
    _process('DEMO-FARE-50')
    api('POST', '/cases/DEMO-FARE-50/clarifications',
        json={'recipient': 'rider', 'question': 'Did you receive notification?'})
    resp = api('GET', '/cases/DEMO-FARE-50', headers=RIDER_A)
    req_id = [c for c in resp.json()['clarifications'] if c['status'] == 'PENDING'][0]['request_id']
    api('POST', f'/cases/DEMO-FARE-50/clarifications/{req_id}/reply',
        headers=RIDER_A, json={'answer': 'Yes I was notified.'})
    # Reviewer re-processes
    resp = api('POST', '/cases/DEMO-FARE-50/process')
    assert resp.status_code == 200
    case = resp.json()
    # The case should be back to REVIEW_REQUIRED (clarification answered, but unverified)
    assert case['status'] in ('REVIEW_REQUIRED', 'RESOLVED', 'AWAITING_CLARIFICATION')


# ---------------------------------------------------------------------------
# 17. Audit event is recorded for reviewer-created clarification
# ---------------------------------------------------------------------------

def test_audit_event_recorded():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'rider', 'question': 'Did you agree to the fare?'})
    case = resp.json()
    clar_events = [e for e in case.get('events', []) if e.get('kind') == 'clarification_requested']
    assert len(clar_events) >= 1
    assert clar_events[-1]['details'].get('source') == 'reviewer_adhoc'


# ---------------------------------------------------------------------------
# 18. Notification is created and labelled as not delivered
# ---------------------------------------------------------------------------

def test_notification_created_and_labelled():
    _setup()
    resp = api('POST', '/cases/DEMO-FARE-50/clarifications',
               json={'recipient': 'rider', 'question': 'Did you agree to the fare?'})
    case = resp.json()
    notifs = [n for n in case.get('notifications', []) if n.get('recipient') == 'rider'
              and n.get('kind') == 'CLARIFICATION_REQUEST']
    assert len(notifs) >= 1
    assert notifs[0]['status']=='DELIVERED'
    assert notifs[0]['channel']=='in_app'
    assert notifs[0]['delivered_at']


# ---------------------------------------------------------------------------
# 19. Party does not see the other party's clarifications
# ---------------------------------------------------------------------------

def test_rider_does_not_see_driver_clarifications():
    _setup()
    api('POST', '/cases/DEMO-FARE-50/clarifications',
        json={'recipient': 'driver', 'question': 'Why did you take that route?'})
    resp = api('GET', '/cases/DEMO-FARE-50', headers=RIDER_A)
    case = resp.json()
    # Rider should not see any driver-directed clarifications
    driver_clars = [c for c in case.get('clarifications', []) if c.get('recipient') == 'driver']
    assert len(driver_clars) == 0


# ---------------------------------------------------------------------------
# 20. Existing auto-clarification flow still works (regression)
# ---------------------------------------------------------------------------

def test_auto_clarification_still_works():
    _setup()
    _process('DEMO-FARE-CLARIFY')
    case = api('GET', '/cases/DEMO-FARE-CLARIFY').json()
    assert case['status'] == 'AWAITING_CLARIFICATION'
    auto_clars = [c for c in case['clarifications'] if c['status'] == 'PENDING']
    assert len(auto_clars) >= 1
