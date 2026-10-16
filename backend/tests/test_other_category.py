"""Regression tests for "Other / I'm not sure" dispute intake category.

Tests that:
- Rider can submit an "other" case successfully.
- The case belongs to the authenticated Rider identity.
- Rider B cannot access Rider A's "other" case.
- Reviewer can view the case and its original description.
- "Other" cannot auto-resolve or automatically transfer money.
- Safety allegations under "other" trigger immediate human review and skip Judge.
- Reviewer cannot apply refund/credit to unclassified "other" case.
- Reviewer can reclassify "other" to a specific category.
- After reclassification, the case can be processed normally.
- Original category is preserved for audit after reclassification.
- Non-"other" cases cannot be reclassified.
- Existing six categories still work unchanged.

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


def api(method, path, headers=REVIEW, **kwargs):
    return client.request(method, path, headers=headers, **kwargs)


def _setup():
    set_repo(MemoryRepository())
    repo().reset() if hasattr(repo(), 'reset') else None


def _submit_other_case(case_id='OTHER-TEST-001', headers=RIDER_A, description='Something happened during the trip that I am not sure how to categorize. The driver took a weird route and I was also charged extra.'):
    """Helper: submit an 'other' case as the given identity."""
    return api('POST', '/cases', headers=headers, json={
        'case_id': case_id,
        'trip_id': 'TRIP-OTHER-001',
        'category': 'other',
        'filed_by': 'rider',
        'description': description,
        'synthetic': True,
    })


# ---------------------------------------------------------------------------
# 1. Rider can submit an "other" case successfully.
# ---------------------------------------------------------------------------

def test_rider_can_submit_other_case():
    """Rider A can submit a case with category='other'."""
    _setup()
    r = _submit_other_case()
    assert r.status_code == 200, r.text
    case = r.json()
    assert case['case_id'] == 'OTHER-TEST-001'
    assert case['category'] == 'other'
    assert case['status'] == 'NEW'
    assert case['description'] == 'Something happened during the trip that I am not sure how to categorize. The driver took a weird route and I was also charged extra.'


# ---------------------------------------------------------------------------
# 2. The case belongs to the authenticated Rider identity.
# ---------------------------------------------------------------------------

def test_other_case_belongs_to_rider():
    """The 'other' case is owned by the submitting rider."""
    _setup()
    _submit_other_case()
    # Rider A can see the case in their list.
    r = api('GET', '/cases', headers=RIDER_A)
    assert r.status_code == 200
    cases = r.json()
    assert any(c['case_id'] == 'OTHER-TEST-001' for c in cases)
    # Rider A can access the case detail.
    r = api('GET', '/cases/OTHER-TEST-001', headers=RIDER_A)
    assert r.status_code == 200
    assert r.json()['category'] == 'other'


# ---------------------------------------------------------------------------
# 3. Rider B cannot access Rider A's new case.
# ---------------------------------------------------------------------------

def test_rider_b_cannot_access_rider_a_other_case():
    """Rider B cannot list or retrieve Rider A's 'other' case."""
    _setup()
    _submit_other_case()
    # Rider B should not see it in their list.
    r = api('GET', '/cases', headers=RIDER_B)
    assert r.status_code == 200
    assert not any(c['case_id'] == 'OTHER-TEST-001' for c in r.json())
    # Rider B should get 404 on direct access.
    r = api('GET', '/cases/OTHER-TEST-001', headers=RIDER_B)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 4. Reviewer can view the case and its original description.
# ---------------------------------------------------------------------------

def test_reviewer_can_view_other_case():
    """Reviewer can view the 'other' case with full detail."""
    _setup()
    _submit_other_case()
    r = api('GET', '/cases/OTHER-TEST-001', headers=REVIEW)
    assert r.status_code == 200
    case = r.json()
    assert case['category'] == 'other'
    assert 'description' in case
    assert 'weird route' in case['description']


# ---------------------------------------------------------------------------
# 5. "Other" cannot auto-resolve or automatically transfer money.
# ---------------------------------------------------------------------------

def test_other_cannot_auto_resolve():
    """Processing an 'other' case routes to HUMAN_REVIEW, never RESOLVED."""
    _setup()
    _submit_other_case()
    r = api('POST', '/cases/OTHER-TEST-001/process', headers=REVIEW)
    assert r.status_code == 200
    case = r.json()
    assert case['status'] == 'REVIEW_REQUIRED'
    assert case['path'] == 'HUMAN_REVIEW'
    assert case['gate']['can_auto'] is False
    # No financial action recorded.
    assert 'mock_action' not in case
    assert case['candidate']['disposition'] == 'undetermined'
    assert case['candidate']['amount'] == 0


def test_other_no_judge_no_agent_outputs():
    """An 'other' case should not invoke the Judge or produce agent outputs."""
    _setup()
    _submit_other_case()
    r = api('POST', '/cases/OTHER-TEST-001/process', headers=REVIEW)
    case = r.json()
    # No agents were invoked.
    assert case.get('agent_outputs') == {}
    assert case.get('agent_trace') == []
    # No Judge entry.
    assert 'Judge' not in case.get('agent_outputs', {})


# ---------------------------------------------------------------------------
# 6. Safety allegations under "other" trigger immediate human review and skip Judge.
# ---------------------------------------------------------------------------

def test_other_with_safety_triggers_immediate_review():
    """An 'other' case with safety allegations in the description triggers
    safety screening, immediate human review, and Judge skipped."""
    _setup()
    r = api('POST', '/cases', headers=RIDER_A, json={
        'case_id': 'OTHER-SAFE-001',
        'trip_id': 'TRIP-SAFE-001',
        'category': 'other',
        'filed_by': 'rider',
        'description': 'I felt unsafe during the trip. The driver was driving aggressively and I feared for my safety.',
        'synthetic': True,
    })
    assert r.status_code == 200
    # Process it — safety screen should catch it.
    r = api('POST', '/cases/OTHER-SAFE-001/process', headers=REVIEW)
    assert r.status_code == 200
    case = r.json()
    assert case['status'] == 'REVIEW_REQUIRED'
    assert case['path'] == 'IMMEDIATE_HUMAN_REVIEW'
    assert case['gate']['can_auto'] is False
    assert 'SF-5.1' in case['gate']['blocking_rules']
    # Judge should not be in agent_outputs (skipped for safety).
    assert 'Judge' not in case.get('agent_outputs', {})
    # No financial action.
    assert 'mock_action' not in case


# ---------------------------------------------------------------------------
# 7. Reviewer cannot apply refund/credit to unclassified "other" case.
# ---------------------------------------------------------------------------

def test_reviewer_cannot_refund_other_case():
    """Reviewer cannot apply refund to unclassified 'other' case."""
    _setup()
    _submit_other_case()
    api('POST', '/cases/OTHER-TEST-001/process', headers=REVIEW)
    r = api('POST', '/cases/OTHER-TEST-001/review', headers=REVIEW, json={
        'disposition': 'refund',
        'amount': 10.0,
        'reason': 'I think a refund is appropriate here.',
    })
    assert r.status_code == 400
    assert 'reclassify' in r.json()['detail'].lower()


def test_reviewer_cannot_credit_other_case():
    """Reviewer cannot apply credit to unclassified 'other' case."""
    _setup()
    _submit_other_case()
    api('POST', '/cases/OTHER-TEST-001/process', headers=REVIEW)
    r = api('POST', '/cases/OTHER-TEST-001/review', headers=REVIEW, json={
        'disposition': 'credit',
        'amount': 5.0,
        'reason': 'A credit seems fair.',
    })
    assert r.status_code == 400
    assert 'reclassify' in r.json()['detail'].lower()


def test_reviewer_can_reject_other_case():
    """Reviewer can reject an 'other' case (no financial action)."""
    _setup()
    _submit_other_case()
    api('POST', '/cases/OTHER-TEST-001/process', headers=REVIEW)
    r = api('POST', '/cases/OTHER-TEST-001/review', headers=REVIEW, json={
        'disposition': 'reject_claim',
        'amount': 0,
        'reason': 'No basis for any remedy after review.',
    })
    assert r.status_code == 200


def test_reviewer_can_no_action_other_case():
    """Reviewer can apply no_action to an 'other' case (no financial action)."""
    _setup()
    _submit_other_case()
    api('POST', '/cases/OTHER-TEST-001/process', headers=REVIEW)
    r = api('POST', '/cases/OTHER-TEST-001/review', headers=REVIEW, json={
        'disposition': 'no_action',
        'amount': 0,
        'reason': 'No monetary remedy owed.',
    })
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 8. Reviewer reclassification workflow.
# ---------------------------------------------------------------------------

def test_reviewer_can_reclassify_other_case():
    """Reviewer can reclassify an 'other' case to fare_dispute."""
    _setup()
    _submit_other_case()
    r = api('POST', '/cases/OTHER-TEST-001/reclassify', headers=REVIEW, json={
        'category': 'fare_dispute',
        'reason': 'Description mentions extra charge — fits fare dispute.',
    })
    assert r.status_code == 200
    case = r.json()
    assert case['category'] == 'fare_dispute'
    assert case['original_category'] == 'other'
    assert case['status'] == 'NEW'
    assert case['reclassification_reason']


def test_reclassify_preserves_original_category_for_audit():
    """Reclassification preserves the original 'other' category for audit."""
    _setup()
    _submit_other_case()
    api('POST', '/cases/OTHER-TEST-001/reclassify', headers=REVIEW, json={
        'category': 'route_deviation',
        'reason': 'Rider mentions weird route — reclassify to route deviation.',
    })
    r = api('GET', '/cases/OTHER-TEST-001', headers=REVIEW)
    case = r.json()
    assert case['category'] == 'route_deviation'
    assert case['original_category'] == 'other'


def test_reclassify_records_event():
    """Reclassification records a case_reclassified event in the audit chain."""
    _setup()
    _submit_other_case()
    api('POST', '/cases/OTHER-TEST-001/reclassify', headers=REVIEW, json={
        'category': 'property_damage',
        'reason': 'Damage mentioned — reclassify to property damage.',
    })
    r = api('GET', '/cases/OTHER-TEST-001', headers=REVIEW)
    case = r.json()
    events = case.get('events', [])
    assert any(e['kind'] == 'case_reclassified' for e in events)
    # Audit chain should still be valid.
    r = api('GET', '/cases/OTHER-TEST-001/verify-audit', headers=REVIEW)
    assert r.json()['valid'] is True


def test_cannot_reclassify_non_other_case():
    """Reclassification only works on 'other' category cases."""
    _setup()
    seed_cases()
    r = api('POST', '/cases/DISP-003/reclassify', headers=REVIEW, json={
        'category': 'fare_dispute',
        'reason': 'This is already fare_dispute.',
    })
    assert r.status_code == 400


def test_cannot_reclassify_to_other():
    """Cannot reclassify to 'other' — only specific categories."""
    _setup()
    _submit_other_case()
    r = api('POST', '/cases/OTHER-TEST-001/reclassify', headers=REVIEW, json={
        'category': 'other',
        'reason': 'Trying to reclassify to other.',
    })
    assert r.status_code == 422  # Pydantic validation rejects 'other'


def test_rider_cannot_reclassify():
    """Only reviewer can reclassify."""
    _setup()
    _submit_other_case()
    r = api('POST', '/cases/OTHER-TEST-001/reclassify', headers=RIDER_A, json={
        'category': 'fare_dispute',
        'reason': 'Rider trying to reclassify.',
    })
    assert r.status_code == 403


def test_reclassified_case_can_be_processed():
    """After reclassification, the case can be processed under the new category."""
    _setup()
    _submit_other_case()
    # Reclassify to fare_dispute.
    api('POST', '/cases/OTHER-TEST-001/reclassify', headers=REVIEW, json={
        'category': 'fare_dispute',
        'reason': 'Reclassify to fare dispute for processing.',
    })
    # Now process — should run the fare_dispute policy path (likely clarification
    # or human review because the case has no fare facts, but it should NOT
    # be in the "other" manual-classification triage path).
    r = api('POST', '/cases/OTHER-TEST-001/process', headers=REVIEW)
    assert r.status_code == 200
    case = r.json()
    # Should not be in the "other" triage path anymore — path should be
    # something other than the manual classification message.
    candidate_reason = (case.get('candidate') or {}).get('reason', '')
    assert candidate_reason != 'Unclassified "other" category: manual classification required'
    # Should have actually attempted policy processing (gaps or agents).
    assert case.get('path') in ('CLARIFICATION', 'HUMAN_REVIEW', 'AUTO_ELIGIBLE')


def test_reclassify_to_safety_not_allowed():
    """Cannot reclassify to safety_incident — safety is determined by the screen."""
    _setup()
    _submit_other_case()
    r = api('POST', '/cases/OTHER-TEST-001/reclassify', headers=REVIEW, json={
        'category': 'safety_incident',
        'reason': 'Trying to reclassify to safety.',
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 9. Existing categories still work unchanged.
# ---------------------------------------------------------------------------

def test_existing_fare_dispute_still_works():
    """Existing fare_dispute category cases still process normally."""
    _setup()
    seed_cases()
    r = api('POST', '/cases/DISP-003/process', headers=REVIEW)
    assert r.status_code == 200
    case = r.json()
    assert case['path'] == 'AUTO_ELIGIBLE'
    assert case['status'] == 'RESOLVED'
    assert case['mock_action']['amount'] == 4.5


def test_existing_safety_case_still_works():
    """Existing safety_incident case still triggers immediate human review."""
    _setup()
    seed_cases()
    r = api('POST', '/cases/DEMO-SAFETY-IN-FARE/process', headers=REVIEW)
    assert r.status_code == 200
    case = r.json()
    assert case['path'] == 'IMMEDIATE_HUMAN_REVIEW'
    assert 'Judge' not in case.get('agent_outputs', {})


def test_full_regression_suite_still_passes():
    """The deterministic evaluation suite still passes for all existing cases."""
    _setup()
    seed_cases()
    r = api('GET', '/evaluation/reference')
    assert r.status_code == 200
    result = r.json()
    assert result['all_passed'] is True
