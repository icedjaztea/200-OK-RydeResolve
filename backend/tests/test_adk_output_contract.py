"""Step 69.4D — Live ADK output-contract reliability tests.

Covers:
- Judge must provide a finite, non-negative numerical recommended_amount
  whenever recommending refund or credit (missing, NaN, Infinity, negative
  all fail).
- Invalid disposition labels are rejected.
- no_action vs reject_claim distinction documented in Judge instructions.
- FraudBadFaith must always use undetermined — cannot independently
  recommend a financial remedy.
- Mock Judge produces its own independent summary, not a raw copy.
- No auto-correction of missing amounts by injecting the policy engine amount.
- FraudBadFaith role boundary enforcement in mock_agent.
- Policy gate and financial calculations unchanged.

AI_MODE=mock throughout; live-model validation noted as remaining.
"""
import asyncio
import json
import math
import pytest
from app.agents import (
    validate_agent_output,
    mock_agent,
    judge_consistency,
    has_agent_failures,
    NON_FINANCIAL_ROLES,
)
from app.policy_engine import recommend, gate
from app.config import ROOT


# ── Helpers ──────────────────────────────────────────────────────────────────

def _case(cid):
    return json.loads((ROOT / f'fixtures/cases/{cid}.json').read_text())


# ── Judge recommended_amount validation ──────────────────────────────────────

class TestJudgeAmountContract:
    """Judge must provide finite non-negative recommended_amount for
    refund/credit.  Missing, non-numeric, NaN, Infinity, and negative
    values must all trigger parse_failed."""

    def test_refund_with_valid_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund', 'recommended_amount': 4.50}
        assert not validate_agent_output('Judge', out).get('parse_failed')

    def test_refund_with_zero_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund', 'recommended_amount': 0}
        assert not validate_agent_output('Judge', out).get('parse_failed')

    def test_refund_missing_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_refund_none_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund', 'recommended_amount': None}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_refund_string_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund',
               'recommended_amount': 'five dollars'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_refund_nan_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund',
               'recommended_amount': float('nan')}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_refund_infinity_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund',
               'recommended_amount': float('inf')}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_refund_negative_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund',
               'recommended_amount': -1.00}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_credit_missing_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'credit'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_credit_negative_amount_fails(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'credit',
               'recommended_amount': -5.00}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True

    def test_no_action_without_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'no_action'}
        assert not validate_agent_output('Judge', out).get('parse_failed')

    def test_reject_claim_without_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'reject_claim'}
        assert not validate_agent_output('Judge', out).get('parse_failed')

    def test_undetermined_without_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'undetermined'}
        assert not validate_agent_output('Judge', out).get('parse_failed')

    def test_numeric_string_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund',
               'recommended_amount': '4.50'}
        assert not validate_agent_output('Judge', out).get('parse_failed')


# ── Invalid disposition labels ──────────────────────────────────────────────

class TestInvalidDispositions:
    """Unrecognized disposition strings must be rejected for any role."""

    @pytest.mark.parametrize('bad_label', [
        'refund_surge_differential',
        'partial_refund',
        'pending',
        'n/a',
        'approved',
        'deny',
        'REFUND',
        '',
    ])
    def test_invalid_disposition_fails(self, bad_label):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': bad_label}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'Unrecognized disposition' in result['validation_error']

    def test_invalid_disposition_for_advocate_fails(self):
        out = {'role': 'RiderAdvocate', 'summary': 'ok',
               'recommended_disposition': 'pay_rider'}
        result = validate_agent_output('RiderAdvocate', out)
        assert result['parse_failed'] is True


# ── FraudBadFaith role boundary ──────────────────────────────────────────────

class TestFraudBadFaithRoleBoundary:
    """FraudBadFaith must always use undetermined. It must not
    independently recommend refund, credit, no_action, or reject_claim."""

    def test_fraud_bad_faith_refund_fails(self):
        out = {'role': 'FraudBadFaith', 'summary': 'risk indicators present',
               'recommended_disposition': 'refund', 'recommended_amount': 5.00}
        result = validate_agent_output('FraudBadFaith', out)
        assert result['parse_failed'] is True
        assert 'FraudBadFaith' in result['validation_error']
        assert 'undetermined' in result['validation_error']

    def test_fraud_bad_faith_credit_fails(self):
        out = {'role': 'FraudBadFaith', 'summary': 'risk indicators present',
               'recommended_disposition': 'credit', 'recommended_amount': 5.00}
        result = validate_agent_output('FraudBadFaith', out)
        assert result['parse_failed'] is True

    def test_fraud_bad_faith_no_action_fails(self):
        out = {'role': 'FraudBadFaith', 'summary': 'risk indicators present',
               'recommended_disposition': 'no_action'}
        result = validate_agent_output('FraudBadFaith', out)
        assert result['parse_failed'] is True

    def test_fraud_bad_faith_reject_claim_fails(self):
        out = {'role': 'FraudBadFaith', 'summary': 'risk indicators present',
               'recommended_disposition': 'reject_claim'}
        result = validate_agent_output('FraudBadFaith', out)
        assert result['parse_failed'] is True

    def test_fraud_bad_faith_undetermined_passes(self):
        out = {'role': 'FraudBadFaith', 'summary': 'risk indicators present',
               'recommended_disposition': 'undetermined'}
        result = validate_agent_output('FraudBadFaith', out)
        assert not result.get('parse_failed')

    def test_other_non_financial_roles_undetermined_only(self):
        for role in ('DisputeOrchestrator', 'PolicyPrecedent',
                     'ClarificationAgent', 'ImageAnalysis'):
            out = {'role': role, 'summary': 'ok',
                   'recommended_disposition': 'refund', 'recommended_amount': 5.0}
            result = validate_agent_output(role, out)
            assert result['parse_failed'] is True, \
                f'{role} should not be able to recommend refund'


# ── Mock agent produces independent Judge output ──────────────────────────────

class TestMockJudgeIndependence:
    """The mock Judge should produce its own independent summary and
    structure, not a raw copy of the candidate dict.  It should have
    a distinct summary string, its own agent_name, and the mode label."""

    def _candidate(self):
        return recommend(_case('DISP-003'))

    def _context(self):
        from app.policy import select_candidates
        return select_candidates('fare_dispute', 'surge change', 0, False)

    def test_mock_judge_has_independent_summary(self):
        case = _case('DISP-003')
        candidate = self._candidate()
        context = self._context()
        judge = mock_agent('Judge', case, candidate, context)
        # The mock Judge should have its own summary text — not empty,
        # not just the candidate's reason field.
        assert judge['summary'], 'Judge mock must have a summary'
        assert judge['summary'] != candidate.get('reason', ''), \
            'Mock Judge summary should not simply copy candidate reason'

    def test_mock_judge_has_mode_label(self):
        case = _case('DISP-003')
        candidate = self._candidate()
        context = self._context()
        judge = mock_agent('Judge', case, candidate, context)
        assert judge['mode'] == 'MOCK_NOT_MODEL_OUTPUT'

    def test_mock_judge_has_agent_name(self):
        case = _case('DISP-003')
        candidate = self._candidate()
        context = self._context()
        judge = mock_agent('Judge', case, candidate, context)
        assert judge['agent_name'] == 'Judge'

    def test_mock_fraud_bad_faith_is_undetermined(self):
        case = _case('DISP-003')
        candidate = self._candidate()
        context = self._context()
        fbf = mock_agent('FraudBadFaith', case, candidate, context)
        assert fbf['recommended_disposition'] == 'undetermined'
        assert fbf['recommended_amount'] is None
        assert fbf['mode'] == 'MOCK_NOT_MODEL_OUTPUT'

    def test_mock_dispute_orchestrator_is_undetermined(self):
        case = _case('DISP-003')
        candidate = self._candidate()
        context = self._context()
        do = mock_agent('DisputeOrchestrator', case, candidate, context)
        assert do['recommended_disposition'] == 'undetermined'

    def test_mock_policy_precedent_is_undetermined(self):
        case = _case('DISP-003')
        candidate = self._candidate()
        context = self._context()
        pp = mock_agent('PolicyPrecedent', case, candidate, context)
        assert pp['recommended_disposition'] == 'undetermined'


# ── No auto-correction of missing amounts ────────────────────────────────────

class TestNoAmountAutoCorrection:
    """The pipeline must never inject the policy engine's expected amount
    into a Judge output that is missing one.  A Judge that omits the amount
    must fail validation and force human review."""

    def test_missing_amount_not_corrected_by_validation(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        # The validation result must NOT contain an auto-filled amount.
        assert result.get('recommended_amount') is None or \
            result['recommended_amount'] == out.get('recommended_amount'), \
            'Validation must not auto-fill recommended_amount'

    def test_invalid_amount_not_corrected_by_validation(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund',
               'recommended_amount': 'invalid'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        # The invalid value must NOT be replaced with a valid one.
        assert result.get('recommended_amount') in (None, 'invalid'), \
            'Validation must not auto-correct invalid recommended_amount'

    def test_nan_amount_not_corrected(self):
        out = {'role': 'Judge', 'summary': 'ok',
               'recommended_disposition': 'refund',
               'recommended_amount': float('nan')}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True


# ── No-show label handling ───────────────────────────────────────────────────

class TestNoShowLabelHandling:
    """The deterministic engine and validation must correctly distinguish
    no_action (driver met all requirements, rider absent) from
    reject_claim (claim is unfounded) for no-show cases."""

    def test_noshow_valid_recommends_no_action(self):
        """DEMO-NOSHOW-VALID: driver arrived, waited, called, rider absent.
        Policy engine recommends no_action (not reject_claim)."""
        case = _case('DEMO-NOSHOW-VALID')
        decision = recommend(case)
        assert decision['disposition'] == 'no_action', \
            'Valid no-show with rider absent should be no_action, not reject_claim'

    def test_noshow_valid_judge_no_action_passes_validation(self):
        out = {'role': 'Judge', 'summary': 'rider absent, driver met requirements',
               'recommended_disposition': 'no_action'}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    def test_noshow_valid_judge_reject_claim_passes_validation(self):
        """Judge CAN use reject_claim — it's a valid label.  The point is
        that no_action and reject_claim are distinct labels, and both
        pass structural validation."""
        out = {'role': 'Judge', 'summary': 'claim unsupported by evidence',
               'recommended_disposition': 'reject_claim'}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    def test_noshow_void_recommends_refund(self):
        """DEMO-NOSHOW-VOID: driver did not complete required chat and call.
        Policy engine recommends refund."""
        case = _case('DEMO-NOSHOW-VOID')
        decision = recommend(case)
        assert decision['disposition'] == 'refund'

    def test_noshow_labels_not_interchangeable_in_instructions(self):
        """The Judge instructions must explain the difference between
        no_action and reject_claim."""
        from app.agents import agent_instructions
        instructions = agent_instructions('Judge')
        assert 'no_action' in instructions
        assert 'reject_claim' in instructions
        # Must contain guidance distinguishing the two
        assert 'NOT interchangeable' in instructions or 'not interchangeable' in instructions, \
            'Instructions must state that no_action and reject_claim are not interchangeable'


# ── FraudBadFaith instructions contain role boundary ────────────────────────

class TestFraudBadFaithInstructions:
    """The agent instructions for FraudBadFaith must explicitly require
    undetermined and forbid financial remedies."""

    def test_instructions_require_undetermined(self):
        from app.agents import agent_instructions
        instructions = agent_instructions('FraudBadFaith')
        assert 'undetermined' in instructions, \
            'FraudBadFaith instructions must mention undetermined'
        # Must contain a role-boundary warning
        assert 'role boundary' in instructions.lower() or \
               'must' in instructions.lower()

    def test_instructions_mention_risk_indicators_not_remedy(self):
        from app.agents import agent_instructions
        instructions = agent_instructions('FraudBadFaith')
        assert 'risk' in instructions.lower(), \
            'FraudBadFaith instructions must mention risk indicators'


# ── judge_consistency unchanged ───────────────────────────────────────────────

class TestJudgeConsistencyUnchanged:
    """judge_consistency still catches mismatches between Judge and
    deterministic candidate.  It does NOT auto-correct."""

    def test_consistent_judge_passes(self):
        candidate = recommend(_case('DISP-003'))
        outputs = {'Judge': {'recommended_disposition': 'refund',
                            'recommended_amount': 4.50, 'parse_failed': False}}
        # In mock mode, judge_consistency returns True (not live AI)
        assert judge_consistency(outputs, candidate) is True

    def test_parse_failed_judge_fails_consistency(self):
        candidate = recommend(_case('DISP-003'))
        outputs = {'Judge': {'recommended_disposition': 'undetermined',
                            'parse_failed': True}}
        assert judge_consistency(outputs, candidate) is False


# ── Policy engine unchanged ───────────────────────────────────────────────────

class TestPolicyEngineUnchanged:
    """verify recommend() and gate() still produce the same results."""

    def test_disp003_refund_450(self):
        decision = recommend(_case('DISP-003'))
        assert decision['disposition'] == 'refund'
        assert decision['amount'] == 4.50

    def test_disp003_gate_auto_eligible(self):
        case = _case('DISP-003')
        decision = recommend(case)
        assert gate(case, decision)['can_auto'] is True

    def test_disp001_refund_344(self):
        decision = recommend(_case('DISP-001'))
        assert decision['disposition'] == 'refund'
        assert decision['amount'] == 3.44

    def test_disp001_route_deviation_gate_blocks(self):
        """Route deviation cases must still require human review."""
        case = _case('DISP-001')
        decision = recommend(case)
        g = gate(case, decision)
        assert g['can_auto'] is False
        assert any('TH-6.2-ROUTE' in r for r in g.get('blocking_rules', []))

    def test_safety_case_still_immediate_review(self):
        case = _case('DEMO-SAFETY-IN-FARE')
        decision = recommend(case)
        assert decision['disposition'] == 'undetermined'
        g = gate(case, decision)
        assert g['path'] == 'IMMEDIATE_HUMAN_REVIEW'
        assert g['can_auto'] is False

    def test_noshow_valid_no_action(self):
        case = _case('DEMO-NOSHOW-VALID')
        decision = recommend(case)
        assert decision['disposition'] == 'no_action'
        assert decision['amount'] == 0

    def test_financial_thresholds_unchanged(self):
        """Value above 50 still triggers mandatory human review."""
        case = _case('DEMO-FARE-OVER50')
        decision = recommend(case)
        g = gate(case, decision)
        assert g['can_auto'] is False
        assert any('TH-6.1-HIGH' in r for r in g.get('blocking_rules', []))


# ── Full pipeline: missing Judge amount forces review ────────────────────────

class TestPipelineMissingAmountForcesReview:
    """End-to-end: if the live Judge omits recommended_amount, the pipeline
    must not auto-correct it — it must force human review."""

    def test_judge_missing_amount_forces_review(self, monkeypatch):
        from app.services import seed_cases, process_case
        from app.repository import repo, MemoryRepository, set_repo
        set_repo(MemoryRepository())
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'I recommend a refund.',
                        'recommended_disposition': 'refund',
                        # recommended_amount intentionally omitted
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role,
                    'summary': f'{role} ok',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert 'mock_action' not in result
        assert result['agent_outputs']['Judge']['parse_failed'] is True

    def test_judge_nan_amount_forces_review(self, monkeypatch):
        from app.services import seed_cases, process_case
        from app.repository import repo, MemoryRepository, set_repo
        set_repo(MemoryRepository())
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'Refund of NaN.',
                        'recommended_disposition': 'refund',
                        'recommended_amount': float('nan'),
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role,
                    'summary': f'{role} ok',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert 'mock_action' not in result
        assert result['agent_outputs']['Judge']['parse_failed'] is True

    def test_fraud_bad_faith_financial_remedy_forces_review(self, monkeypatch):
        """If FraudBadFaith illegally returns refund, validation must catch it."""
        from app.services import seed_cases, process_case
        from app.repository import repo, MemoryRepository, set_repo
        set_repo(MemoryRepository())
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'FraudBadFaith':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'Risk indicators suggest refund needed.',
                        'recommended_disposition': 'refund',
                        'recommended_amount': 10.00,
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'Refund the verified differential.',
                        'recommended_disposition': 'refund',
                        'recommended_amount': 4.50,
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role,
                    'summary': f'{role} ok',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        # FraudBadFaith should have parse_failed because it proposed refund
        assert result['agent_outputs']['FraudBadFaith']['parse_failed'] is True
        # Pipeline must force review because of agent failures
        assert result['path'] == 'HUMAN_REVIEW'
        assert 'mock_action' not in result

    def test_judge_invalid_disposition_forces_review(self, monkeypatch):
        from app.services import seed_cases, process_case
        from app.repository import repo, MemoryRepository, set_repo
        set_repo(MemoryRepository())
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'I recommend partial_refund.',
                        'recommended_disposition': 'partial_refund',
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role,
                    'summary': f'{role} ok',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert 'mock_action' not in result
        assert result['agent_outputs']['Judge']['parse_failed'] is True

    def test_valid_judge_passes_pipeline(self, monkeypatch):
        """Baseline: valid Judge output matching candidate still auto-resolves."""
        from app.services import seed_cases, process_case
        from app.repository import repo, MemoryRepository, set_repo
        set_repo(MemoryRepository())
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'Independent assessment: refund the differential.',
                        'recommended_disposition': 'refund',
                        'recommended_amount': 4.50,
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role,
                    'summary': f'{role} analysis complete',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        assert result['path'] == 'AUTO_ELIGIBLE'
        assert result['mock_action']['amount'] == 4.50
        assert not has_agent_failures(result['agent_outputs'])
