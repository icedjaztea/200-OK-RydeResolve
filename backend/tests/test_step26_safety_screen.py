"""Step 26 regression tests for improved safety_screen().

Verifies:
1. All four original phrases are correctly detected:
   - "The driver threatened me."       → True (was already detected)
   - "I felt unsafe during the trip."  → True (was already detected)
   - "The driver intimidated me."      → True (was False before fix)
   - "The driver followed me home."    → True (was False before fix)
2. Additional variations: stalking, chasing, "felt threatened", "threatened me".
3. False positives avoided: "I followed the GPS route home" etc.
4. Cross-category safety: safety in fare_dispute / no_show_charge escalates.
5. Full pipeline: safety detection → IMMEDIATE_HUMAN_REVIEW, REVIEW_REQUIRED,
   no Judge ruling, no mock_action, SAFETY_REVIEW_ALERT recorded.
"""
import asyncio, os, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault('AI_MODE', 'mock')
os.environ.setdefault('APP_MODE', 'memory')

from app.evidence import safety_screen, SAFETY_TERMS, SAFETY_PATTERNS
from app.sla import route_priority
from app.services import seed_cases, process_case
from app.repository import set_repo, MemoryRepository


def _case(description, category='fare_dispute', evidence=None):
    return {
        'case_id': 'TEST-SAFETY',
        'category': category,
        'description': description,
        'facts': {},
        'evidence': evidence or [],
        'dispute_amount': 5.0,
        'dispute_value_basis': 'amount_in_dispute',
        'fraud_flags': 0,
    }


# ── 1. Four original phrases ─────────────────────────────────────────────

class TestOriginalFourPhrases:

    def test_threatened_me_detected(self):
        assert safety_screen(_case('The driver threatened me.')) is True

    def test_felt_unsafe_detected(self):
        assert safety_screen(_case('I felt unsafe during the trip.')) is True

    def test_intimidated_detected(self):
        assert safety_screen(_case('The driver intimidated me.')) is True

    def test_followed_home_detected(self):
        assert safety_screen(_case('The driver followed me home.')) is True


# ── 2. Additional safety variations ──────────────────────────────────────

class TestAdditionalSafetyPhrases:

    def test_i_was_intimidated(self):
        assert safety_screen(_case('I was intimidated by the driver.')) is True

    def test_intimidating_behavior(self):
        assert safety_screen(_case('The driver displayed intimidating behavior.')) is True

    def test_stalking_me(self):
        assert safety_screen(_case('He was stalking me after the trip.')) is True

    def test_stalked_me(self):
        assert safety_screen(_case('The driver stalked me to my car.')) is True

    def test_felt_threatened(self):
        assert safety_screen(_case('I felt threatened during the ride.')) is True

    def test_threatened_me_variation(self):
        assert safety_screen(_case('The driver threatened me with violence.')) is True

    def test_threatened_us(self):
        assert safety_screen(_case('The driver threatened us.')) is True

    def test_threatened_the_rider(self):
        assert safety_screen(_case('He threatened the rider.')) is True

    def test_chased_me(self):
        assert safety_screen(_case('The driver chased me out of the car.')) is True

    def test_followed_me_to_my_house(self):
        assert safety_screen(_case('The driver followed me to my house.')) is True

    def test_followed_me_to_my_address(self):
        assert safety_screen(_case('The driver followed me to my address.')) is True

    def test_followed_me_to_my_apartment(self):
        assert safety_screen(_case('The driver followed me to my apartment.')) is True

    def test_she_followed_me_home(self):
        assert safety_screen(_case('She followed me home after drop-off.')) is True

    def test_they_followed_us_home(self):
        assert safety_screen(_case('They followed us home.')) is True


# ── 3. False positive avoidance ──────────────────────────────────────────

class TestFalsePositiveAvoidance:

    def test_followed_gps_route_home_not_safety(self):
        assert safety_screen(_case('I followed the GPS route home.')) is False

    def test_followed_directions_home_not_safety(self):
        assert safety_screen(_case('The driver followed the directions to my home.')) is False

    def test_route_deviation_without_safety(self):
        assert safety_screen(_case(
            'The driver took a different route to my home, it was longer.',
            category='route_deviation',
        )) is False

    def test_pure_fare_dispute_not_safety(self):
        assert safety_screen(_case(
            'I was charged surge without notification. The fare went from 12 to 16.50.',
        )) is False

    def test_pure_no_show_not_safety(self):
        assert safety_screen(_case(
            'Driver never showed up. I waited 15 minutes.',
            category='no_show_charge',
        )) is False

    def test_followed_by_rider_not_driver_not_safety(self):
        """'I followed' (rider's action) should not trigger, even with 'home'."""
        assert safety_screen(_case(
            'I followed the driver\'s car after the trip to see where he went.',
        )) is False


# ── 4. Cross-category safety detection ───────────────────────────────────

class TestCrossCategorySafety:

    def test_safety_in_fare_dispute_detected(self):
        case = _case(
            'The driver intimidated me and charged surge without notification.',
            category='fare_dispute',
        )
        assert safety_screen(case) is True

    def test_safety_in_no_show_charge_detected(self):
        case = _case(
            'The driver stalked me after I reported the no-show.',
            category='no_show_charge',
        )
        assert safety_screen(case) is True

    def test_safety_in_route_deviation_detected(self):
        case = _case(
            'The driver followed me home after I complained about the route.',
            category='route_deviation',
        )
        assert safety_screen(case) is True

    def test_safety_in_property_damage_detected(self):
        case = _case(
            'The driver threatened me when I pointed out the damage.',
            category='property_damage',
        )
        assert safety_screen(case) is True

    def test_safety_incident_category_always_detected(self):
        case = _case('Just a normal description.', category='safety_incident')
        assert safety_screen(case) is True


# ── 5. Safety detected in evidence content, not just description ─────────

class TestSafetyInEvidence:

    def test_safety_in_chat_evidence(self):
        case = _case('Fare dispute over surge.', evidence=[
            {'id': 'EV-001', 'type': 'chat', 'content': 'The driver intimidated me in the chat.'},
        ])
        assert safety_screen(case) is True

    def test_safety_in_claim_evidence(self):
        case = _case('Fare dispute over surge.', evidence=[
            {'id': 'EV-002', 'type': 'claim', 'content': 'I felt threatened by the driver.'},
        ])
        assert safety_screen(case) is True

    def test_safety_in_transcript_evidence(self):
        case = _case('Fare dispute over surge.', evidence=[
            {'id': 'EV-003', 'type': 'transcript', 'content': 'He was stalking me.'},
        ])
        assert safety_screen(case) is True

    def test_non_scanned_evidence_type_ignored(self):
        """Evidence types not in (chat, claim, transcript) are not scanned."""
        case = _case('Normal fare dispute.', evidence=[
            {'id': 'EV-004', 'type': 'image_or_document', 'content': 'The driver intimidated me.'},
        ])
        assert safety_screen(case) is False


# ── 6. SLA priority for safety cases ─────────────────────────────────────

class TestSLAPriority:

    def test_safety_case_gets_p0(self):
        case = _case('The driver intimidated me.')
        routing = route_priority(case)
        assert routing['priority'] == 'P0_SAFETY'
        assert routing['queue'] == 'SAFETY_REVIEW'
        assert routing['requires_immediate_attention'] is True

    def test_non_safety_does_not_get_p0(self):
        case = _case('I was charged surge without notification.')
        routing = route_priority(case)
        assert routing['priority'] != 'P0_SAFETY'


# ── 7. Full pipeline: safety → IMMEDIATE_HUMAN_REVIEW ────────────────────

class TestPipelineSafetyEscalation:

    def test_cross_category_safety_escalates_to_immediate_review(self):
        """A fare_dispute with safety content must escalate like a safety case."""
        set_repo(MemoryRepository())
        seed_cases()
        # DEMO-SAFETY-IN-FARE is a fare_dispute with "The driver threatened me"
        result = asyncio.run(process_case('DEMO-SAFETY-IN-FARE'))
        assert result['path'] == 'IMMEDIATE_HUMAN_REVIEW'
        assert result['status'] == 'REVIEW_REQUIRED'
        assert result['gate']['can_auto'] is False
        assert 'Judge' not in result.get('agent_outputs', {})
        assert 'mock_action' not in result
        # SAFETY_REVIEW_ALERT must be in notifications
        notifications = result.get('notifications', [])
        kinds = [n.get('kind') for n in notifications]
        assert 'SAFETY_REVIEW_ALERT' in kinds
        alert = next(n for n in notifications if n['kind'] == 'SAFETY_REVIEW_ALERT')
        assert alert['recipient'] == 'reviewer'
        assert alert['status'] == 'SIMULATED_OUTBOX_NOT_DELIVERED'

    def test_safety_candidate_is_undetermined(self):
        set_repo(MemoryRepository())
        seed_cases()
        result = asyncio.run(process_case('DEMO-SAFETY-IN-FARE'))
        assert result['candidate']['disposition'] == 'undetermined'
        assert result['candidate']['amount'] == 0

    def test_safety_event_recorded(self):
        set_repo(MemoryRepository())
        seed_cases()
        result = asyncio.run(process_case('DEMO-SAFETY-IN-FARE'))
        kinds = [e['kind'] for e in result.get('events', [])]
        assert 'mandatory_safety_escalation' in kinds

    def test_pure_fare_dispute_does_not_escalate_to_safety(self):
        """DISP-003 is a pure fare dispute without safety content."""
        set_repo(MemoryRepository())
        seed_cases()
        result = asyncio.run(process_case('DISP-003'))
        assert result['path'] != 'IMMEDIATE_HUMAN_REVIEW'
        assert 'SAFETY_REVIEW_ALERT' not in [
            n.get('kind') for n in result.get('notifications', [])
        ]


# ── 8. Term and pattern structure ────────────────────────────────────────

class TestSafetyTermsStructure:

    def test_original_terms_preserved(self):
        """All original SAFETY_TERMS must still be present."""
        expected = {'unsafe', 'assault', 'threat', 'harass', 'reckless',
                    'dangerous driving', 'accident', 'sexual', 'hit me',
                    'hurt me', 'weapon', 'drunk driving', 'felt scared',
                    'physical abuse'}
        assert expected.issubset(set(SAFETY_TERMS))

    def test_new_terms_added(self):
        assert 'intimidated' in SAFETY_TERMS
        assert 'intimidating' in SAFETY_TERMS
        assert 'stalking' in SAFETY_TERMS
        assert 'stalked' in SAFETY_TERMS
        assert 'felt threatened' in SAFETY_TERMS
        assert 'threatened me' in SAFETY_TERMS

    def test_patterns_compiled(self):
        for p in SAFETY_PATTERNS:
            assert hasattr(p, 'search')
