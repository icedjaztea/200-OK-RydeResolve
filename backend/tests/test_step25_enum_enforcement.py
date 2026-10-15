"""Regression tests for Step 25 FastAPI failure: DriverAdvocate returned
"refund_surge_differential" which is not in VALID_DISPOSITIONS.

Verifies:
1. Agent instructions explicitly contain the accepted enum.
2. refund_surge_differential remains invalid.
3. refund and undetermined are valid when appropriate.
4. Invalid outputs still prevent automatic financial execution (fail-closed).
"""
import asyncio, json, os, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault('AI_MODE', 'mock')
os.environ.setdefault('APP_MODE', 'memory')

from app.agents import (
    validate_agent_output,
    has_agent_failures,
    agent_instructions,
    VALID_DISPOSITIONS,
)
from app.services import process_case, seed_cases
from app.repository import set_repo, MemoryRepository


# ── 1. Agent instructions contain the accepted enum ──────────────────────

class TestPromptContainsEnum:

    def test_common_instructions_list_all_five_dispositions(self):
        prompt = agent_instructions('DriverAdvocate')
        for label in ('refund', 'credit', 'no_action', 'reject_claim', 'undetermined'):
            assert f'"{label}"' in prompt, f'Label "{label}" not found in prompt'

    def test_common_instructions_forbid_custom_labels(self):
        prompt = agent_instructions('DriverAdvocate')
        assert 'No custom labels' in prompt
        assert 'compound labels' in prompt
        assert 'synonyms are permitted' in prompt

    def test_common_instructions_show_invalid_example(self):
        prompt = agent_instructions('DriverAdvocate')
        assert 'refund_surge_differential' in prompt
        assert 'INVALID' in prompt

    def test_common_instructions_explain_summary_alternative(self):
        prompt = agent_instructions('DriverAdvocate')
        assert 'summary field' in prompt

    def test_all_roles_get_enum_instructions(self):
        for role in ('DisputeOrchestrator', 'RiderAdvocate', 'DriverAdvocate',
                     'Judge', 'FraudBadFaith', 'PolicyPrecedent'):
            prompt = agent_instructions(role)
            assert 'MUST be EXACTLY one of' in prompt, f'{role} missing enum constraint'

    def test_driver_advocate_particular_prefers_undetermined(self):
        prompt = agent_instructions('DriverAdvocate')
        assert 'undetermined' in prompt
        assert 'NOT the final Judge' in prompt


# ── 2. refund_surge_differential remains invalid ─────────────────────────

class TestCompoundLabelInvalid:

    def test_refund_surge_differential_rejected(self):
        out = {'role': 'DriverAdvocate', 'summary': 'argues driver case',
               'recommended_disposition': 'refund_surge_differential'}
        result = validate_agent_output('DriverAdvocate', out)
        assert result['parse_failed'] is True
        assert 'recommended_disposition' in result['invalid_fields']
        assert result['failure_kind'] == 'invalid_fields'

    def test_partial_refund_rejected(self):
        out = {'role': 'DriverAdvocate', 'summary': 'ok',
               'recommended_disposition': 'partial_refund'}
        result = validate_agent_output('DriverAdvocate', out)
        assert result['parse_failed'] is True

    def test_pending_rejected(self):
        out = {'role': 'DriverAdvocate', 'summary': 'ok',
               'recommended_disposition': 'pending'}
        result = validate_agent_output('DriverAdvocate', out)
        assert result['parse_failed'] is True

    def test_na_rejected(self):
        out = {'role': 'DriverAdvocate', 'summary': 'ok',
               'recommended_disposition': 'n/a'}
        result = validate_agent_output('DriverAdvocate', out)
        assert result['parse_failed'] is True


# ── 3. refund and undetermined are valid when appropriate ────────────────

class TestValidLabelsAccepted:

    def test_undetermined_valid_for_driver_advocate(self):
        out = {'role': 'DriverAdvocate', 'summary': 'presents driver evidence',
               'recommended_disposition': 'undetermined'}
        result = validate_agent_output('DriverAdvocate', out)
        assert not result.get('parse_failed')

    def test_refund_valid_for_judge(self):
        out = {'role': 'Judge', 'summary': 'proposes refund',
               'recommended_disposition': 'refund', 'recommended_amount': 4.50}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    def test_credit_valid_for_judge(self):
        out = {'role': 'Judge', 'summary': 'proposes credit',
               'recommended_disposition': 'credit', 'recommended_amount': 10.00}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    def test_no_action_valid_for_any_role(self):
        out = {'role': 'RiderAdvocate', 'summary': 'concedes',
               'recommended_disposition': 'no_action'}
        result = validate_agent_output('RiderAdvocate', out)
        assert not result.get('parse_failed')

    def test_reject_claim_valid_for_any_role(self):
        out = {'role': 'FraudBadFaith', 'summary': 'fraud confirmed',
               'recommended_disposition': 'reject_claim'}
        result = validate_agent_output('FraudBadFaith', out)
        assert not result.get('parse_failed')


# ── 4. Invalid outputs prevent automatic financial execution ─────────────

class TestFailClosedOnInvalidDisposition:

    def test_invalid_disposition_sets_parse_failed(self):
        out = {'role': 'DriverAdvocate', 'summary': 'surge differential refund',
               'recommended_disposition': 'refund_surge_differential'}
        result = validate_agent_output('DriverAdvocate', out)
        assert result['parse_failed'] is True

    def test_has_agent_failures_true_with_invalid_disposition(self):
        outputs = {
            'DriverAdvocate': validate_agent_output('DriverAdvocate', {
                'role': 'DriverAdvocate', 'summary': 'ok',
                'recommended_disposition': 'refund_surge_differential',
            }),
            'Judge': validate_agent_output('Judge', {
                'role': 'Judge', 'summary': 'refund 4.50',
                'recommended_disposition': 'refund', 'recommended_amount': 4.50,
            }),
        }
        assert has_agent_failures(outputs) is True

    def test_has_agent_failures_false_when_all_valid(self):
        outputs = {
            'DriverAdvocate': validate_agent_output('DriverAdvocate', {
                'role': 'DriverAdvocate', 'summary': 'driver evidence',
                'recommended_disposition': 'undetermined',
            }),
            'Judge': validate_agent_output('Judge', {
                'role': 'Judge', 'summary': 'refund 4.50',
                'recommended_disposition': 'refund', 'recommended_amount': 4.50,
            }),
        }
        assert has_agent_failures(outputs) is False

    def test_invalid_driver_advocate_forces_human_review(self, monkeypatch):
        """End-to-end: DriverAdvocate with refund_surge_differential → HUMAN_REVIEW."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'DriverAdvocate':
                return {
                    'result': validate_agent_output(role, {
                        'role': role, 'summary': 'driver argues surge differential',
                        'recommended_disposition': 'refund_surge_differential',
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role, 'summary': 'refund 4.50',
                        'recommended_disposition': 'refund',
                        'recommended_amount': 4.50,
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role, 'summary': f'{role} ok',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert result['agent_outputs']['DriverAdvocate']['parse_failed'] is True
        assert 'recommended_disposition' in result['agent_outputs']['DriverAdvocate']['invalid_fields']

    def test_valid_undetermined_driver_advocate_allows_auto(self, monkeypatch):
        """When DriverAdvocate returns undetermined and Judge matches engine → AUTO_ELIGIBLE."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role, 'summary': 'refund 4.50',
                        'recommended_disposition': 'refund',
                        'recommended_amount': 4.50,
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role, 'summary': f'{role} ok',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        assert result['path'] == 'AUTO_ELIGIBLE'
        assert not has_agent_failures(result['agent_outputs'])


# ── 5. VALID_DISPOSITIONS is exactly the 5 expected values ───────────────

class TestValidDispositionsEnum:

    def test_exactly_five_valid_dispositions(self):
        assert VALID_DISPOSITIONS == frozenset({
            'refund', 'credit', 'no_action', 'reject_claim', 'undetermined',
        })

    def test_refund_surge_differential_not_in_enum(self):
        assert 'refund_surge_differential' not in VALID_DISPOSITIONS
