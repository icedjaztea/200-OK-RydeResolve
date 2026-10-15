"""Step 41 — Notification & Outcome Explanation Outbox.

Tests the simulated outbox: CLARIFICATION_REQUEST, SAFETY_REVIEW_ALERT,
and RESOLUTION_RECEIPT with readable messages, explicit NOT DELIVERED
status, dedup on retry, human-reviewed notifications, and safe
rider/driver wording for safety cases.

APP_MODE=memory AI_MODE=mock throughout.
"""
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.config import setting
from app.services import seed_cases, process_case, human_review
from app.repository import repo, MemoryRepository, set_repo

client = TestClient(app)
REVIEW = {'X-Demo-Key': setting('DEMO_REVIEWER_KEY', 'change-reviewer-key')}
RIDER = {'X-Demo-Key': setting('DEMO_RIDER_KEY', 'change-rider-key')}


def api(method, path, headers=REVIEW, **kwargs):
    return client.request(method, path, headers=headers, **kwargs)


def _process(case_id, headers=REVIEW):
    return api('POST', f'/cases/{case_id}/process', headers=headers).json()


def _setup():
    set_repo(MemoryRepository())
    repo().reset() if hasattr(repo(), 'reset') else None
    seed_cases()


# ---------------------------------------------------------------------------
# 1. Clarification request: no duplicate notification on retry.
# ---------------------------------------------------------------------------
def test_clarification_no_duplicate_on_retry():
    _setup()
    p = _process('DEMO-FARE-CLARIFY')
    assert p['path'] == 'CLARIFICATION'
    notes = [n for n in p['notifications'] if n['kind'] == 'CLARIFICATION_REQUEST']
    assert len(notes) == 1, f'Expected 1 clarification notification, got {len(notes)}'
    assert 'message' in notes[0]
    assert notes[0]['message']  # non-empty readable message
    assert notes[0]['status'] == 'SIMULATED_OUTBOX_NOT_DELIVERED'

    # Retry process — should not create a duplicate notification
    again = _process('DEMO-FARE-CLARIFY')
    notes2 = [n for n in again['notifications'] if n['kind'] == 'CLARIFICATION_REQUEST']
    assert len(notes2) == 1, 'Retry created a duplicate CLARIFICATION_REQUEST notification'


# ---------------------------------------------------------------------------
# 2. Safety alert: no Judge ruling, immediate human review.
# ---------------------------------------------------------------------------
def test_safety_alert_no_judge_no_mock_payment():
    _setup()
    p = _process('DEMO-SAFETY-IN-FARE')
    assert p['path'] == 'IMMEDIATE_HUMAN_REVIEW'
    assert 'Judge' not in p.get('agent_outputs', {})
    assert 'mock_action' not in p

    safety_notes = [n for n in p['notifications'] if n['kind'] == 'SAFETY_REVIEW_ALERT']
    assert len(safety_notes) >= 1  # at least reviewer alert
    for n in safety_notes:
        assert n['status'] == 'SIMULATED_OUTBOX_NOT_DELIVERED'
        assert 'message' in n and n['message']  # readable message present
    # Reviewer alert should mention safety/human review
    reviewer_note = next(n for n in safety_notes if n['recipient'] == 'reviewer')
    assert 'safety' in reviewer_note['message'].lower() or 'review' in reviewer_note['message'].lower()


# ---------------------------------------------------------------------------
# 3. DISP-003 SGD 4.50 simulated refund notification.
# ---------------------------------------------------------------------------
def test_disp003_simulated_refund_notification():
    _setup()
    p = _process('DISP-003')
    assert p['path'] == 'AUTO_ELIGIBLE'
    assert p['mock_action']['amount'] == 4.5
    assert p['mock_action']['disposition'] == 'refund'

    receipts = [n for n in p['notifications'] if n['kind'] == 'RESOLUTION_RECEIPT']
    assert len(receipts) == 1
    msg = receipts[0]['message']
    assert 'SGD 4.50' in msg or '4.5' in msg
    assert 'refund' in msg.lower()
    assert 'no real' in msg.lower() or 'not' in msg.lower()  # payment destination unknown / not executed
    assert receipts[0]['status'] == 'SIMULATED_OUTBOX_NOT_DELIVERED'
    assert receipts[0]['recipient'] == 'rider'


# ---------------------------------------------------------------------------
# 4. Human-reviewed DISP-001 gets a notification.
# ---------------------------------------------------------------------------
def test_human_reviewed_disp001_gets_notification():
    _setup()
    _process('DISP-001')
    before = len(repo().actions)
    reviewed = api('POST', '/cases/DISP-001/review',
                   json={'disposition': 'refund', 'amount': 3.44,
                         'reason': 'Human approved excess distance refund after review'})
    assert reviewed.status_code == 200, reviewed.text
    case = reviewed.json()
    receipts = [n for n in case['notifications'] if n['kind'] == 'RESOLUTION_RECEIPT']
    assert len(receipts) == 1, 'Human review should produce a RESOLUTION_RECEIPT notification'
    msg = receipts[0]['message']
    assert 'refund' in msg.lower()
    assert 'SGD' in msg
    assert receipts[0]['status'] == 'SIMULATED_OUTBOX_NOT_DELIVERED'


# ---------------------------------------------------------------------------
# 5. No duplicate review/processing notifications.
# ---------------------------------------------------------------------------
def test_no_duplicate_review_processing_notifications():
    _setup()
    # Process DISP-001 -> REVIEW_REQUIRED (no notifications until review or safety)
    p1 = _process('DISP-001')
    notes_after_process = len(p1.get('notifications', []))
    # Process again — should not create duplicates
    p2 = _process('DISP-001')
    assert len(p2.get('notifications', [])) == notes_after_process, \
        'Re-processing created duplicate notifications'

    # Human review creates a RESOLUTION_RECEIPT
    reviewed = api('POST', '/cases/DISP-001/review',
                   json={'disposition': 'no_action', 'amount': 0,
                         'reason': 'Reviewer found no valid claim after evidence review'})
    assert reviewed.status_code == 200
    case = reviewed.json()
    receipts = [n for n in case['notifications'] if n['kind'] == 'RESOLUTION_RECEIPT']
    assert len(receipts) == 1, 'Human review produced duplicate notification'

    # Retry review — should be blocked (already reviewed)
    again = api('POST', '/cases/DISP-001/review',
                json={'disposition': 'refund', 'amount': 3.44,
                      'reason': 'Trying again to create duplicate'})
    assert again.status_code == 400  # Already reviewed


# ---------------------------------------------------------------------------
# 6. no_action: no money transfer in message.
# ---------------------------------------------------------------------------
def test_no_action_no_money():
    _setup()
    _process('DISP-001')
    reviewed = api('POST', '/cases/DISP-001/review',
                   json={'disposition': 'no_action', 'amount': 0,
                         'reason': 'Reviewer found no valid claim after evidence review'})
    assert reviewed.status_code == 200, reviewed.text
    case = reviewed.json()
    receipts = [n for n in case['notifications'] if n['kind'] == 'RESOLUTION_RECEIPT']
    assert len(receipts) == 1
    msg = receipts[0]['message']
    assert 'no action' in msg.lower() or 'no transfer' in msg.lower()
    assert 'not' in msg.lower() or 'no payment' in msg.lower()


# ---------------------------------------------------------------------------
# 7. Credit: not original-card refund.
# ---------------------------------------------------------------------------
def test_credit_not_card_refund():
    _setup()
    _process('DISP-001')
    reviewed = api('POST', '/cases/DISP-001/review',
                   json={'disposition': 'credit', 'amount': 3.44,
                         'reason': 'Reviewer approved in-app credit after evidence review'})
    assert reviewed.status_code == 200, reviewed.text
    case = reviewed.json()
    receipts = [n for n in case['notifications'] if n['kind'] == 'RESOLUTION_RECEIPT']
    assert len(receipts) == 1
    msg = receipts[0]['message']
    assert 'credit' in msg.lower()
    assert 'not a card refund' in msg.lower()


# ---------------------------------------------------------------------------
# 8. Safe distinct rider/driver wording for safety cases.
# ---------------------------------------------------------------------------
def test_safe_distinct_rider_driver_wording():
    _setup()
    p = _process('DEMO-SAFETY-IN-FARE')
    safety_notes = [n for n in p['notifications'] if n['kind'] == 'SAFETY_REVIEW_ALERT']
    rider_note = next(n for n in safety_notes if n['recipient'] == 'rider')
    driver_note = next(n for n in safety_notes if n['recipient'] == 'driver')

    # Messages must be distinct
    assert rider_note['message'] != driver_note['message']

    # Rider message should not contain driver-specific allegations
    assert 'threat' not in rider_note['message'].lower()
    assert 'assault' not in rider_note['message'].lower()
    # Driver message should not contain rider-specific allegations
    assert 'threat' not in driver_note['message'].lower()
    assert 'assault' not in driver_note['message'].lower()

    # Both must mention the case ID and synthetic demo
    assert 'DEMO-SAFETY-IN-FARE' in rider_note['message']
    assert 'DEMO-SAFETY-IN-FARE' in driver_note['message']
    assert 'synthetic' in rider_note['message'].lower()
    assert 'synthetic' in driver_note['message'].lower()

    # Both must NOT contain historical fraud flag references
    assert 'fraud' not in rider_note['message'].lower()
    assert 'fraud' not in driver_note['message'].lower()

    # Reviewer message can be more detailed but rider/driver are privacy-filtered
    reviewer_note = next(n for n in safety_notes if n['recipient'] == 'reviewer')
    assert reviewer_note['message'] != rider_note['message']


# ---------------------------------------------------------------------------
# 9. All outbox entries explicitly simulated/not delivered.
# ---------------------------------------------------------------------------
def test_all_outbox_entries_simulated_not_delivered():
    _setup()
    # Process multiple case types
    _process('DEMO-FARE-CLARIFY')        # CLARIFICATION_REQUEST
    _process('DEMO-SAFETY-IN-FARE')     # SAFETY_REVIEW_ALERT
    _process('DISP-003')                 # RESOLUTION_RECEIPT (auto-resolve)

    for cid in ['DEMO-FARE-CLARIFY', 'DEMO-SAFETY-IN-FARE', 'DISP-003']:
        case = api('GET', f'/cases/{cid}').json()
        for n in case.get('notifications', []):
            assert n['status'] == 'SIMULATED_OUTBOX_NOT_DELIVERED', \
                f'{cid}: notification {n["kind"]} has status {n["status"]}'
            assert 'message' in n and n['message'], \
                f'{cid}: notification {n["kind"]} missing readable message'
            assert 'created_at' in n, \
                f'{cid}: notification {n["kind"]} missing timestamp'
            assert 'recipient' in n, \
                f'{cid}: notification {n["kind"]} missing recipient'

    # Also check human-reviewed case
    _process('DISP-001')
    reviewed = api('POST', '/cases/DISP-001/review',
                   json={'disposition': 'refund', 'amount': 3.44,
                         'reason': 'Reviewer approved after full evidence review'})
    assert reviewed.status_code == 200
    case = reviewed.json()
    for n in case.get('notifications', []):
        assert n['status'] == 'SIMULATED_OUTBOX_NOT_DELIVERED'
        assert 'message' in n and n['message']
        assert 'created_at' in n
        assert 'recipient' in n
