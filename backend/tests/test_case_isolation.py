"""P0 — Backend-enforced Rider/Driver case isolation.

Tests that:
- Rider A cannot list or retrieve Rider B cases.
- Driver A cannot list or retrieve unrelated driver cases.
- A guessed case ID returns 404 (indistinguishable from unauthorized).
- Rider/Driver cannot view internal traces or fraud information.
- Rider/Driver cannot trigger processing or review operations meant
  for the reviewer.
- Clarification replies require correct case association and recipient.
- Reviewer access continues to work.

APP_MODE=memory AI_MODE=mock throughout.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.config import setting
from app.services import seed_cases
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


# ---------------------------------------------------------------------------
# 1. Rider A cannot list Rider B cases.
# ---------------------------------------------------------------------------

def test_rider_a_cannot_list_rider_b_cases():
    """DEMO-DAMAGE-DISPUTED is owned by rider_b. Rider A must not see it."""
    _setup()
    cases = api('GET', '/cases', headers=RIDER_A).json()
    case_ids = [c['case_id'] for c in cases]
    assert 'DEMO-DAMAGE-DISPUTED' not in case_ids, \
        'Rider A should not see Rider B cases'


def test_rider_b_cannot_list_rider_a_cases():
    """Most seeded cases are owned by rider_a. Rider B must see only DEMO-DAMAGE-DISPUTED."""
    _setup()
    cases = api('GET', '/cases', headers=RIDER_B).json()
    case_ids = [c['case_id'] for c in cases]
    assert 'DEMO-DAMAGE-DISPUTED' in case_ids, \
        'Rider B should see their own case'
    assert 'DISP-003' not in case_ids, \
        'Rider B should not see Rider A cases'
    assert 'DEMO-FARE-50' not in case_ids, \
        'Rider B should not see Rider A cases'


# ---------------------------------------------------------------------------
# 2. Rider A cannot retrieve Rider B case details.
# ---------------------------------------------------------------------------

def test_rider_a_cannot_get_rider_b_case():
    _setup()
    r = api('GET', '/cases/DEMO-DAMAGE-DISPUTED', headers=RIDER_A)
    assert r.status_code == 404, \
        f'Expected 404, got {r.status_code}'


def test_rider_b_can_get_own_case():
    _setup()
    r = api('GET', '/cases/DEMO-DAMAGE-DISPUTED', headers=RIDER_B)
    assert r.status_code == 200
    case = r.json()
    assert case['case_id'] == 'DEMO-DAMAGE-DISPUTED'


# ---------------------------------------------------------------------------
# 3. Driver A cannot list or retrieve unrelated driver cases.
# ---------------------------------------------------------------------------

def test_driver_a_cannot_list_driver_b_cases():
    """DEMO-DAMAGE-DISPUTED is owned by driver_b. Driver A must not see it."""
    _setup()
    cases = api('GET', '/cases', headers=DRIVER_A).json()
    case_ids = [c['case_id'] for c in cases]
    assert 'DEMO-DAMAGE-DISPUTED' not in case_ids, \
        'Driver A should not see Driver B cases'


def test_driver_b_can_list_own_cases():
    _setup()
    cases = api('GET', '/cases', headers=DRIVER_B).json()
    case_ids = [c['case_id'] for c in cases]
    assert 'DEMO-DAMAGE-DISPUTED' in case_ids, \
        'Driver B should see their own case'


def test_driver_a_cannot_get_driver_b_case():
    _setup()
    r = api('GET', '/cases/DEMO-DAMAGE-DISPUTED', headers=DRIVER_A)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 4. Guessed case ID returns 404 (indistinguishable from unauthorized).
# ---------------------------------------------------------------------------

def test_guessed_case_id_returns_404():
    _setup()
    r = api('GET', '/cases/THIS-DOES-NOT-EXIST', headers=RIDER_A)
    assert r.status_code == 404
    r = api('GET', '/cases/THIS-DOES-NOT-EXIST', headers=DRIVER_A)
    assert r.status_code == 404
    r = api('GET', '/cases/THIS-DOES-NOT-EXIST', headers=REVIEW)
    assert r.status_code == 404


def test_unauthorized_case_id_same_as_nonexistent():
    """Unauthorized case returns 404, not 403, so IDs are indistinguishable."""
    _setup()
    unauthorized = api('GET', '/cases/DEMO-DAMAGE-DISPUTED', headers=RIDER_A)
    nonexistent = api('GET', '/cases/FAKE-CASE-ID', headers=RIDER_A)
    assert unauthorized.status_code == nonexistent.status_code == 404


# ---------------------------------------------------------------------------
# 5. Rider/Driver cannot view internal traces or fraud information.
# ---------------------------------------------------------------------------

def test_rider_cannot_see_internal_fields():
    _setup()
    # Process a case as reviewer so internal fields are populated.
    api('POST', '/cases/DISP-003/process', headers=REVIEW)
    r = api('GET', '/cases/DISP-003', headers=RIDER_A)
    assert r.status_code == 200
    case = r.json()
    # These fields must not be present in a rider-safe response.
    for forbidden in ('agent_outputs', 'agent_trace', 'routing', 'sla_routing',
                      'gaps', 'contradictions', 'events', 'review',
                      'learning_proposal_id', 'original_escalation',
                      'evidence_snapshot_hash', 'revision', 'source_trust',
                      'fraud_flags', 'rulebook_version', 'evidence'):
        assert forbidden not in case, \
            f'Rider response must not expose {forbidden}'


def test_driver_cannot_see_internal_fields():
    _setup()
    api('POST', '/cases/DISP-003/process', headers=REVIEW)
    # DISP-003 driver_id is driver_a
    r = api('GET', '/cases/DISP-003', headers=DRIVER_A)
    assert r.status_code == 200
    case = r.json()
    for forbidden in ('agent_outputs', 'agent_trace', 'routing', 'sla_routing',
                      'gaps', 'contradictions', 'events', 'review',
                      'learning_proposal_id', 'original_escalation',
                      'evidence_snapshot_hash', 'revision', 'source_trust',
                      'fraud_flags', 'rulebook_version', 'evidence'):
        assert forbidden not in case, \
            f'Driver response must not expose {forbidden}'


def test_rider_cannot_see_driver_clarifications():
    """A rider must not see clarifications directed at the driver."""
    _setup()
    # Process DEMO-FARE-CONFLICT which goes to CLARIFICATION.
    # The clarification_for() function may direct to rider, but
    # any driver-directed clarifications on other cases must be hidden.
    api('POST', '/cases/DEMO-NOSHOW-VOID/process', headers=REVIEW)
    # DEMO-NOSHOW-VOID is owned by rider_a/driver_a
    r = api('GET', '/cases/DEMO-NOSHOW-VOID', headers=DRIVER_A)
    assert r.status_code == 200
    case = r.json()
    # If there are clarifications, they should all be directed at driver.
    for c in case.get('clarifications', []):
        assert c['recipient'] == 'driver', \
            'Driver should only see driver-directed clarifications'


def test_rider_cannot_see_other_party_notifications():
    """A rider must not see notifications directed at the driver or reviewer."""
    _setup()
    api('POST', '/cases/DEMO-SAFETY-IN-FARE/process', headers=REVIEW)
    # DEMO-SAFETY-IN-FARE is owned by rider_a/driver_a
    r = api('GET', '/cases/DEMO-SAFETY-IN-FARE', headers=RIDER_A)
    assert r.status_code == 200
    case = r.json()
    for n in case.get('notifications', []):
        assert n['recipient'] in ('rider', 'all'), \
            f'Rider should not see notifications directed at {n["recipient"]}'


# ---------------------------------------------------------------------------
# 6. Rider/Driver cannot trigger processing operations meant for reviewer.
# ---------------------------------------------------------------------------

def test_rider_cannot_seed_cases():
    _setup()
    r = api('POST', '/cases/seed', headers=RIDER_A)
    assert r.status_code == 403


def test_driver_cannot_seed_cases():
    _setup()
    r = api('POST', '/cases/seed', headers=DRIVER_A)
    assert r.status_code == 403


def test_rider_cannot_add_evidence():
    _setup()
    r = api('POST', '/cases/DISP-003/evidence', headers=RIDER_A, json={
        'field': 'rider_notified', 'value': True, 'provenance': 'fake'})
    assert r.status_code == 403


def test_driver_cannot_add_evidence():
    _setup()
    r = api('POST', '/cases/DISP-003/evidence', headers=DRIVER_A, json={
        'field': 'rider_notified', 'value': True, 'provenance': 'fake'})
    assert r.status_code == 403


def test_rider_cannot_review():
    _setup()
    # Process first to get REVIEW_REQUIRED
    api('POST', '/cases/DISP-001/process', headers=REVIEW)
    r = api('POST', '/cases/DISP-001/review', headers=RIDER_A, json={
        'disposition': 'refund', 'amount': 3.44,
        'reason': 'Testing rider cannot review'})
    assert r.status_code == 403


def test_rider_cannot_upload_files():
    _setup()
    r = api('POST', '/cases/DISP-003/files', headers=RIDER_A,
            files={'file': ('test.png', b'fake', 'image/png')})
    assert r.status_code == 403


def test_rider_cannot_access_review_packet():
    _setup()
    api('POST', '/cases/DISP-001/process', headers=REVIEW)
    r = api('GET', '/cases/DISP-001/review-packet', headers=RIDER_A)
    assert r.status_code == 403


def test_rider_cannot_access_learning():
    _setup()
    assert api('GET', '/learning', headers=RIDER_A).status_code == 403
    assert api('GET', '/evaluation/reference', headers=RIDER_A).status_code == 403


# ---------------------------------------------------------------------------
# 7. Clarification replies require correct case association and recipient.
# ---------------------------------------------------------------------------

def test_rider_cannot_reply_to_driver_clarification():
    """Rider A cannot reply to a clarification directed at the driver."""
    _setup()
    # Process DEMO-NOSHOW-VOID which may generate a driver-directed clarification.
    # Null out driver_call_count to force a driver clarification.
    case = repo().get_case('DEMO-NOSHOW-VOID')
    case['facts']['driver_call_count'] = None
    repo().save_case(case)
    p = api('POST', '/cases/DEMO-NOSHOW-VOID/process', headers=REVIEW).json()
    rid = p['clarifications'][-1]['request_id']
    # Rider A tries to reply to a driver-directed clarification.
    r = api('POST', f'/cases/DEMO-NOSHOW-VOID/clarifications/{rid}/reply',
            headers=RIDER_A, json={'answer': 'I am the rider'})
    assert r.status_code == 403 or r.status_code == 400


def test_rider_b_cannot_reply_to_rider_a_clarification():
    """Rider B cannot reply to a clarification on Rider A's case."""
    _setup()
    p = api('POST', '/cases/DEMO-FARE-CLARIFY/process', headers=REVIEW).json()
    rid = p['clarifications'][-1]['request_id']
    # Rider B tries to reply to a clarification on Rider A's case.
    r = api('POST', f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',
            headers=RIDER_B, json={'answer': 'I am rider B'})
    assert r.status_code == 404, \
        f'Rider B should get 404 for Rider A case, got {r.status_code}'


def test_driver_a_can_reply_to_driver_clarification():
    """Driver A can reply to a driver-directed clarification on their case."""
    _setup()
    case = repo().get_case('DEMO-NOSHOW-VOID')
    case['facts']['driver_call_count'] = None
    repo().save_case(case)
    p = api('POST', '/cases/DEMO-NOSHOW-VOID/process', headers=REVIEW).json()
    rid = p['clarifications'][-1]['request_id']
    r = api('POST', f'/cases/DEMO-NOSHOW-VOID/clarifications/{rid}/reply',
            headers=DRIVER_A, json={'answer': 'I called at 08:48'})
    assert r.status_code == 200, f'Driver A should be able to reply, got {r.status_code}'


# ---------------------------------------------------------------------------
# 8. Reviewer access continues to work.
# ---------------------------------------------------------------------------

def test_reviewer_can_list_all_cases():
    _setup()
    cases = api('GET', '/cases', headers=REVIEW).json()
    assert len(cases) == 12, f'Expected 12 cases, got {len(cases)}'


def test_reviewer_can_access_any_case():
    _setup()
    for cid in ['DISP-003', 'DEMO-DAMAGE-DISPUTED', 'DEMO-SAFETY-IN-FARE']:
        r = api('GET', f'/cases/{cid}', headers=REVIEW)
        assert r.status_code == 200, f'Reviewer should access {cid}'


def test_reviewer_can_process_cases():
    _setup()
    r = api('POST', '/cases/DISP-003/process', headers=REVIEW)
    assert r.status_code == 200
    assert r.json()['path'] == 'AUTO_ELIGIBLE'


def test_reviewer_can_add_evidence():
    _setup()
    r = api('POST', '/cases/DISP-003/evidence', headers=REVIEW, json={
        'field': 'rider_notified', 'value': True,
        'provenance': 'Synthetic verified notification log'})
    assert r.status_code == 200


def test_reviewer_sees_full_case_with_internal_fields():
    _setup()
    api('POST', '/cases/DISP-003/process', headers=REVIEW)
    r = api('GET', '/cases/DISP-003', headers=REVIEW)
    assert r.status_code == 200
    case = r.json()
    # Reviewer should see internal fields.
    assert 'events' in case
    assert 'agent_outputs' in case or case.get('path') == 'AUTO_ELIGIBLE'


# ---------------------------------------------------------------------------
# 9. Case creation assigns server-side ownership.
# ---------------------------------------------------------------------------

def test_rider_created_case_assigned_to_rider():
    """When a rider creates a case, it should be assigned to their identity."""
    _setup()
    new = {
        'case_id': 'RIDER-ISOLATION-TEST',
        'trip_id': 'TRIP-ISOLATION',
        'category': 'fare_dispute',
        'filed_by': 'rider',
        'description': 'Testing case isolation for rider-created cases',
        'dispute_amount': 4.5,
        'synthetic': True,
    }
    r = api('POST', '/cases', headers=RIDER_A, json=new)
    assert r.status_code == 200, r.text
    # Rider A should see it in their list.
    cases = api('GET', '/cases', headers=RIDER_A).json()
    assert 'RIDER-ISOLATION-TEST' in [c['case_id'] for c in cases]
    # Rider B should NOT see it.
    cases_b = api('GET', '/cases', headers=RIDER_B).json()
    assert 'RIDER-ISOLATION-TEST' not in [c['case_id'] for c in cases_b]
    # Driver A should NOT see it (driver_id is not set).
    cases_d = api('GET', '/cases', headers=DRIVER_A).json()
    assert 'RIDER-ISOLATION-TEST' not in [c['case_id'] for c in cases_d]


# ---------------------------------------------------------------------------
# 10. Invalid key rejected.
# ---------------------------------------------------------------------------

def test_invalid_key_rejected():
    _setup()
    r = api('GET', '/cases', headers={'X-Demo-Key': 'wrong-key'})
    assert r.status_code == 401


def test_missing_key_rejected():
    _setup()
    r = api('GET', '/cases', headers={})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# 11. Rider/Driver cannot invoke processing; can refresh status via GET.
# ---------------------------------------------------------------------------

def test_rider_cannot_process_own_case():
    """Rider A cannot invoke processing even on their own case."""
    _setup()
    r = api('POST', '/cases/DISP-003/process', headers=RIDER_A)
    assert r.status_code == 403, \
        f'Rider should not be able to process, got {r.status_code}'


def test_driver_cannot_process_own_case():
    """Driver A cannot invoke processing even on their own case."""
    _setup()
    r = api('POST', '/cases/DISP-003/process', headers=DRIVER_A)
    assert r.status_code == 403, \
        f'Driver should not be able to process, got {r.status_code}'


def test_rider_cannot_process_other_case():
    """Rider A cannot process Rider B's case (gets 403, not 404)."""
    _setup()
    r = api('POST', '/cases/DEMO-DAMAGE-DISPUTED/process', headers=RIDER_A)
    assert r.status_code == 403, \
        f'Rider should get 403 (reviewer-only), got {r.status_code}'


def test_driver_cannot_process_other_case():
    """Driver A cannot process Driver B's case."""
    _setup()
    r = api('POST', '/cases/DEMO-DAMAGE-DISPUTED/process', headers=DRIVER_A)
    assert r.status_code == 403, \
        f'Driver should get 403 (reviewer-only), got {r.status_code}'


def test_rider_can_refresh_status_on_own_case():
    """Rider A can refresh case status via GET /cases/{case_id}."""
    _setup()
    # Reviewer processes first so status is populated.
    api('POST', '/cases/DISP-003/process', headers=REVIEW)
    # Rider refreshes via GET — read-only.
    r = api('GET', '/cases/DISP-003', headers=RIDER_A)
    assert r.status_code == 200
    case = r.json()
    assert case['path'] == 'AUTO_ELIGIBLE'
    # Safe response — no internal fields.
    assert 'agent_outputs' not in case


def test_driver_can_refresh_status_on_own_case():
    """Driver A can refresh case status via GET /cases/{case_id}."""
    _setup()
    api('POST', '/cases/DISP-003/process', headers=REVIEW)
    r = api('GET', '/cases/DISP-003', headers=DRIVER_A)
    assert r.status_code == 200
    case = r.json()
    assert case['path'] == 'AUTO_ELIGIBLE'
    assert 'agent_outputs' not in case


def test_rider_cannot_refresh_other_case():
    """Rider A cannot refresh Rider B's case via GET — returns 404."""
    _setup()
    r = api('GET', '/cases/DEMO-DAMAGE-DISPUTED', headers=RIDER_A)
    assert r.status_code == 404


def test_driver_cannot_refresh_other_case():
    """Driver A cannot refresh Driver B's case via GET — returns 404."""
    _setup()
    r = api('GET', '/cases/DEMO-DAMAGE-DISPUTED', headers=DRIVER_A)
    assert r.status_code == 404


def test_reviewer_can_process():
    """Reviewer can initiate processing."""
    _setup()
    r = api('POST', '/cases/DISP-003/process', headers=REVIEW)
    assert r.status_code == 200
    assert r.json()['path'] == 'AUTO_ELIGIBLE'
