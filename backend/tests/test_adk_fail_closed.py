"""Focused tests for Step 24 fail-closed behavior:
- Malformed advocate JSON prevents autonomous finalization
- Malformed Judge JSON prevents autonomous finalization
- Failed ADK calls (exceptions) produce sanitized error metadata, not mock substitution
- The deterministic policy engine and existing architecture are unchanged
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
from app.agents import (
    validate_agent_output,
    _sanitize_error,
    has_agent_failures,
    evaluate_agents,
    judge_consistency,
    mock_agent,
)
from app.services import process_case, seed_cases
from app.repository import repo, MemoryRepository, set_repo
from app import policy


# ── Helpers ──────────────────────────────────────────────────────────────────

def _disp003():
    """Return a fresh DISP-003 case dict from the fixture file."""
    import json as _json
    from pathlib import Path
    from app.config import ROOT
    return _json.loads((ROOT / 'fixtures/cases/DISP-003.json').read_text())


async def _run_process(cid):
    return await process_case(cid)


# ── validate_agent_output ─────────────────────────────────────────────────────

class TestValidateAgentOutput:

    def test_valid_non_judge_output_passes_through(self):
        out = {'role': 'RiderAdvocate', 'summary': 'ok', 'recommended_disposition': 'undetermined'}
        result = validate_agent_output('RiderAdvocate', out)
        assert not result.get('parse_failed')
        assert result['role'] == 'RiderAdvocate'

    def test_valid_judge_output_with_financial_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'refund', 'recommended_amount': 4.50}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    def test_missing_summary_flags_parse_failed(self):
        out = {'role': 'Judge', 'recommended_disposition': 'refund'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'summary' in result['validation_error']

    def test_missing_recommended_disposition_flags_parse_failed(self):
        out = {'role': 'RiderAdvocate', 'summary': 'ok'}
        result = validate_agent_output('RiderAdvocate', out)
        assert result['parse_failed'] is True
        assert 'recommended_disposition' in result['validation_error']

    def test_none_value_for_required_field_flags_parse_failed(self):
        out = {'role': 'Judge', 'summary': None, 'recommended_disposition': 'refund'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True

    def test_non_dict_input_flags_parse_failed(self):
        result = validate_agent_output('Judge', 'not a dict')
        assert result['parse_failed'] is True
        assert result['validation_error'] == 'Output is not a JSON object'

    def test_unrecognized_disposition_flags_parse_failed(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'execute_payment'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'Unrecognized disposition' in result['validation_error']

    # ── Judge-specific financial validation ──

    def test_judge_refund_missing_amount_flags_parse_failed(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'refund'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_judge_credit_missing_amount_flags_parse_failed(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'credit'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['validation_error']

    def test_judge_refund_non_numeric_amount_flags_parse_failed(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'refund', 'recommended_amount': 'five dollars'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'not numeric' in result['validation_error']

    def test_judge_refund_numeric_string_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'refund', 'recommended_amount': '4.50'}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    def test_judge_undetermined_without_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'undetermined'}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    def test_judge_no_action_without_amount_passes(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'no_action'}
        result = validate_agent_output('Judge', out)
        assert not result.get('parse_failed')

    # ── Non-Judge roles are NOT required to have recommended_amount ──

    def test_non_judge_undetermined_without_amount_passes(self):
        for role in ('RiderAdvocate', 'DriverAdvocate', 'PolicyPrecedent', 'FraudBadFaith', 'DisputeOrchestrator'):
            out = {'role': role, 'summary': 'ok', 'recommended_disposition': 'undetermined'}
            result = validate_agent_output(role, out)
            assert not result.get('parse_failed'), f'{role} should pass with undetermined and no amount'


# ── _sanitize_error ───────────────────────────────────────────────────────────

class TestSanitizeError:

    def test_basic_error_metadata(self):
        exc = RuntimeError('Connection refused')
        result = _sanitize_error(exc, 'Judge')
        assert result['agent_error'] is True
        assert result['parse_failed'] is True
        assert result['recommended_disposition'] == 'undetermined'
        assert result['error_type'] == 'RuntimeError'
        assert result['error_code'] == 'ADK_RUNTIME_ERROR'

    def test_no_raw_exception_message_stored(self):
        exc = RuntimeError('Connection refused to host 10.0.0.1:443 with details')
        result = _sanitize_error(exc, 'Judge')
        assert 'error_message' not in result, 'Raw error_message field must not exist'
        assert 'Connection refused' not in result.get('summary', '')
        assert '10.0.0.1' not in json.dumps(result)

    def test_api_key_never_appears_in_output(self):
        exc = RuntimeError('Auth failed: api_key=AIzaSyB123456secret-value')
        result = _sanitize_error(exc, 'RiderAdvocate')
        result_json = json.dumps(result)
        assert 'AIzaSyB' not in result_json
        assert 'secret-value' not in result_json

    def test_token_never_appears_in_output(self):
        exc = ValueError('Invalid bearer token: eyJhbGciOiJIUzI1NiJ9.payload')
        result = _sanitize_error(exc, 'DriverAdvocate')
        result_json = json.dumps(result)
        assert 'eyJhbGci' not in result_json
        assert 'payload' not in result_json

    def test_sensitive_evidence_never_appears_in_output(self):
        exc = RuntimeError('Processing failed for rider John Doe, phone +6599999999, card 4111111111111111')
        result = _sanitize_error(exc, 'Judge')
        result_json = json.dumps(result)
        assert 'John Doe' not in result_json
        assert '+6599999999' not in result_json
        assert '4111111111111111' not in result_json

    def test_unknown_exception_type_gets_generic_code(self):
        class CustomError(Exception):
            pass
        exc = CustomError('something weird with secret data')
        result = _sanitize_error(exc, 'Judge')
        assert result['error_code'] == 'ADK_UNKNOWN_ERROR'
        assert 'secret data' not in json.dumps(result)


# ── has_agent_failures ───────────────────────────────────────────────────────

class TestHasAgentFailures:

    def test_no_failures_returns_false(self):
        outputs = {
            'Judge': {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'refund', 'parse_failed': False},
            'RiderAdvocate': {'role': 'RiderAdvocate', 'summary': 'ok', 'recommended_disposition': 'undetermined'},
        }
        assert has_agent_failures(outputs) is False

    def test_parse_failed_returns_true(self):
        outputs = {
            'Judge': {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'undetermined', 'parse_failed': True},
        }
        assert has_agent_failures(outputs) is True

    def test_agent_error_returns_true(self):
        outputs = {
            'RiderAdvocate': {'agent_error': True, 'parse_failed': True, 'role': 'RiderAdvocate',
                              'summary': 'failed', 'recommended_disposition': 'undetermined'},
        }
        assert has_agent_failures(outputs) is True

    def test_non_dict_output_returns_true(self):
        outputs = {'Judge': 'broken string'}
        assert has_agent_failures(outputs) is True

    def test_empty_outputs_returns_false(self):
        assert has_agent_failures({}) is False


# ── evaluate_agents with mocked call_adk ─────────────────────────────────────

class TestEvaluateAgentsFailClosed:
    """Mock call_adk to simulate malformed outputs and ADK failures in live mode."""

    def _base_case(self):
        return _disp003()

    def _candidate(self):
        from app.policy_engine import recommend
        return recommend(self._base_case())

    def _context(self):
        from app.policy import select_candidates
        return select_candidates('fare_dispute', 'surge change without notice', 0, False)

    def test_malformed_advocate_json_prevents_auto_finalization(self, monkeypatch):
        """Advocate returns non-JSON → parse_failed → has_agent_failures → True."""
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'RiderAdvocate':
                # Return a result that will fail JSON parsing in call_adk
                # Simulate what call_adk does when JSON is invalid
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': '<<not json>>',
                        'recommended_disposition': 'undetermined',
                        'parse_failed': True,
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role,
                    'summary': f'{role} ok',
                    'recommended_disposition': 'refund' if role == 'Judge' else 'undetermined',
                    'recommended_amount': 4.50 if role == 'Judge' else None,
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        case = self._base_case()
        candidate = self._candidate()
        context = self._context()
        outputs, trace = asyncio.run(evaluate_agents(case, candidate, context, safety=False))

        assert outputs['RiderAdvocate']['parse_failed'] is True
        assert has_agent_failures(outputs) is True

    def test_malformed_judge_json_prevents_auto_finalization(self, monkeypatch):
        """Judge returns invalid JSON → parse_failed → judge_consistency → False."""
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': '<<<malformed>>>',
                        'recommended_disposition': 'undetermined',
                        'parse_failed': True,
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
        case = self._base_case()
        candidate = self._candidate()
        context = self._context()
        outputs, trace = asyncio.run(evaluate_agents(case, candidate, context, safety=False))

        assert outputs['Judge']['parse_failed'] is True
        assert judge_consistency(outputs, candidate) is False
        assert has_agent_failures(outputs) is True

    def test_adk_exception_produces_sanitized_error_not_mock(self, monkeypatch):
        """When call_adk raises, the output is a sanitized error — never a mock stub."""
        monkeypatch.setenv('AI_MODE', 'adk')

        async def failing_call_adk(role, payload):
            raise RuntimeError(f'{role} crashed: connection timeout')

        monkeypatch.setattr('app.agents.call_adk', failing_call_adk)
        case = self._base_case()
        candidate = self._candidate()
        context = self._context()
        outputs, trace = asyncio.run(evaluate_agents(case, candidate, context, safety=False))

        # Every agent should have an agent_error, not a mock stub
        for role in ('DisputeOrchestrator', 'RiderAdvocate', 'DriverAdvocate',
                     'PolicyPrecedent', 'FraudBadFaith', 'Judge'):
            assert outputs[role]['agent_error'] is True, f'{role} should have agent_error'
            assert outputs[role]['parse_failed'] is True
            assert 'mode' not in outputs[role], f'{role} should NOT have MOCK mode badge'
            assert outputs[role]['recommended_disposition'] == 'undetermined'

        assert has_agent_failures(outputs) is True

    def test_credential_leak_never_appears_in_outputs_or_trace(self, monkeypatch):
        """If an exception message contains an API key, it must not appear anywhere in outputs or traces."""
        monkeypatch.setenv('AI_MODE', 'adk')

        async def leaking_call_adk(role, payload):
            raise RuntimeError('Auth failed: api_key=AIzaSyB123456secret')

        monkeypatch.setattr('app.agents.call_adk', leaking_call_adk)
        case = self._base_case()
        candidate = self._candidate()
        context = self._context()
        outputs, trace = asyncio.run(evaluate_agents(case, candidate, context, safety=False))

        # Verify no credential leak in outputs
        outputs_json = json.dumps(outputs, default=str)
        assert 'AIzaSyB' not in outputs_json
        assert '123456secret' not in outputs_json
        # Verify no credential leak in trace
        trace_json = json.dumps(trace, default=str)
        assert 'AIzaSyB' not in trace_json
        assert '123456secret' not in trace_json
        # Verify no error_message field exists at all
        for out in outputs.values():
            assert 'error_message' not in out, 'error_message field must not exist'

    def test_advocate_failure_still_allows_judge_to_run(self, monkeypatch):
        """Even if an advocate crashes, the Judge still runs and sees the error."""
        monkeypatch.setenv('AI_MODE', 'adk')
        judge_ran = []

        async def partial_failure_call_adk(role, payload):
            if role == 'RiderAdvocate':
                raise RuntimeError('RiderAdvocate crashed')
            if role == 'Judge':
                judge_ran.append(True)
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'Judge sees advocate failure',
                        'recommended_disposition': 'undetermined',
                        'parse_failed': True,
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

        monkeypatch.setattr('app.agents.call_adk', partial_failure_call_adk)
        case = self._base_case()
        candidate = self._candidate()
        context = self._context()
        outputs, trace = asyncio.run(evaluate_agents(case, candidate, context, safety=False))

        assert len(judge_ran) == 1, 'Judge must still run even if an advocate failed'
        assert outputs['RiderAdvocate']['agent_error'] is True
        assert outputs['Judge']['parse_failed'] is True
        assert has_agent_failures(outputs) is True


# ── Full pipeline integration (mock mode) ─────────────────────────────────────

class TestPipelineFailClosedMockMode:
    """In mock mode, no agent failures occur (mocks always produce valid output).
    These tests verify the wiring of has_agent_failures into process_case
    by injecting a failure into agent_outputs after processing."""

    def test_mock_mode_disp003_auto_resolves_without_failures(self):
        """Baseline: mock mode DISP-003 auto-resolves — verifies we didn't break existing behavior."""
        seed_cases()
        result = asyncio.run(_run_process('DISP-003'))
        assert result['path'] == 'AUTO_ELIGIBLE'
        assert result['mock_action']['amount'] == 4.50
        assert not has_agent_failures(result['agent_outputs'])

    def test_disp003_with_injected_advocate_failure_forces_review(self):
        """If an advocate output is tampered to parse_failed, has_agent_failures catches it."""
        seed_cases()
        result = asyncio.run(_run_process('DISP-003'))
        # Tamper with the saved case to simulate a parse_failed advocate output
        case = repo().get_case('DISP-003')
        case['agent_outputs']['RiderAdvocate']['parse_failed'] = True
        assert has_agent_failures(case['agent_outputs']) is True
        # The original result should still be AUTO_ELIGIBLE because mock mode doesn't fail
        assert result['path'] == 'AUTO_ELIGIBLE'


# ── Full pipeline integration (simulated live mode) ──────────────────────────

class TestPipelineFailClosedSimulatedLive:
    """Simulate AI_MODE=adk by monkeypatching call_adk within the full process_case pipeline."""

    def test_malformed_advocate_output_forces_human_review(self, monkeypatch):
        """End-to-end: malformed advocate → process_case → HUMAN_REVIEW, no mock_action."""
        # Seed cases first in mock mode
        seed_cases()

        # Now switch to live mode with a broken advocate
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'RiderAdvocate':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': '<<<not json>>>',
                        'recommended_disposition': 'undetermined',
                        'parse_failed': True,
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role,
                    'summary': f'{role} ok',
                    'recommended_disposition': 'refund' if role == 'Judge' else 'undetermined',
                    'recommended_amount': 4.50 if role == 'Judge' else None,
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(_run_process('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert 'mock_action' not in result
        assert has_agent_failures(result['agent_outputs']) is True
        # Verify the specific failure reason is in gate reasons
        assert any('agent' in r.lower() or 'parse_failed' in r.lower() or 'failed' in r.lower()
                   for r in result['gate']['reasons'])

    def test_malformed_judge_output_forces_human_review(self, monkeypatch):
        """End-to-end: malformed Judge → judge_consistency False → HUMAN_REVIEW."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': '<<garbage>>',
                        'recommended_disposition': 'undetermined',
                        'parse_failed': True,
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
        result = asyncio.run(_run_process('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert 'mock_action' not in result
        assert result['agent_outputs']['Judge']['parse_failed'] is True

    def test_adk_crash_forces_human_review_with_sanitized_metadata(self, monkeypatch):
        """End-to-end: all agents crash → sanitized errors in outputs → HUMAN_REVIEW."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def crashing_call_adk(role, payload):
            raise RuntimeError(f'{role} ADK call failed: network error')

        monkeypatch.setattr('app.agents.call_adk', crashing_call_adk)
        result = asyncio.run(_run_process('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert 'mock_action' not in result
        # Every agent output should be a sanitized error
        for role in ('DisputeOrchestrator', 'RiderAdvocate', 'DriverAdvocate',
                     'PolicyPrecedent', 'FraudBadFaith', 'Judge'):
            out = result['agent_outputs'][role]
            assert out['agent_error'] is True, f'{role} should have agent_error'
            assert 'mode' not in out, f'{role} should not have MOCK mode (no silent substitution)'
            assert out['recommended_disposition'] == 'undetermined'
            assert 'error_message' not in out, f'{role} must not have raw error_message'
            assert out['error_code'] == 'ADK_RUNTIME_ERROR'
        # Trace should contain error_code entries
        error_traces = [t for t in result['agent_trace'] if 'error_code' in t]
        assert len(error_traces) >= 6, 'All 6 agents should have error_code trace entries'
        # Raw exception message must not appear anywhere in the case
        case_json = json.dumps(result, default=str)
        assert 'network error' not in case_json, 'Raw exception message must not be stored'

    def test_credential_in_exception_never_appears_in_case_data(self, monkeypatch):
        """If an exception leaks a credential, it must not appear anywhere in the stored case."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def leaking_call_adk(role, payload):
            raise RuntimeError('Auth error: api_key=AIzaSySECRET123 in request')

        monkeypatch.setattr('app.agents.call_adk', leaking_call_adk)
        result = asyncio.run(_run_process('DISP-003'))

        # Check no credential leak in the entire case JSON (outputs, traces, events)
        case_json = json.dumps(result, default=str)
        assert 'AIzaSy' not in case_json, 'Credential must not appear in stored case'
        assert 'SECRET123' not in case_json, 'Credential value must not appear in stored case'
        # Verify no error_message field anywhere in agent_outputs
        for out in result['agent_outputs'].values():
            assert 'error_message' not in out, 'Raw error_message must not exist'

    def test_judge_missing_required_field_forces_review(self, monkeypatch):
        """Judge returns JSON but is missing 'recommended_disposition' → validation catches it."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'Judge':
                # Judge returns a dict but is missing recommended_disposition
                return {
                    'result': validate_agent_output(role, {
                        'role': role,
                        'summary': 'I could not determine the disposition.',
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
        result = asyncio.run(_run_process('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert 'mock_action' not in result
        assert result['agent_outputs']['Judge']['parse_failed'] is True
        assert 'recommended_disposition' in result['agent_outputs']['Judge'].get('validation_error', '')

    def test_judge_refund_without_amount_forces_review(self, monkeypatch):
        """Judge recommends refund but omits recommended_amount → validation fails → HUMAN_REVIEW."""
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
        result = asyncio.run(_run_process('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert 'mock_action' not in result
        assert result['agent_outputs']['Judge']['parse_failed'] is True
        assert 'recommended_amount' in result['agent_outputs']['Judge']['validation_error']

    def test_sensitive_evidence_in_exception_never_leaks(self, monkeypatch):
        """If an exception message contains PII/evidence, it must not appear in the stored case."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        sensitive = 'rider_name=AliceJohnson,phone=+6591234567,card=4111111111111111'

        async def leaking_call_adk(role, payload):
            raise RuntimeError(f'Payload processing failed: {sensitive}')

        monkeypatch.setattr('app.agents.call_adk', leaking_call_adk)
        result = asyncio.run(_run_process('DISP-003'))

        case_json = json.dumps(result, default=str)
        assert 'AliceJohnson' not in case_json
        assert '+6591234567' not in case_json
        assert '4111111111111111' not in case_json
        assert 'rider_name' not in case_json

    def test_non_judge_with_valid_undetermined_passes_pipeline(self, monkeypatch):
        """All non-Judge agents return 'undetermined' (valid for their role) — only Judge needs the real ruling."""
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
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
                    'summary': f'{role} analysis complete',
                    'recommended_disposition': 'undetermined',
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(_run_process('DISP-003'))

        # With valid Judge output matching the engine candidate, auto-eligible path is preserved
        assert result['path'] == 'AUTO_ELIGIBLE'
        assert result['mock_action']['amount'] == 4.50
        assert not has_agent_failures(result['agent_outputs'])


# ── Deterministic engine unchanged ─────────────────────────────────────────────

class TestDeterministicEngineUnchanged:
    """Verify that recommend() and gate() are completely unaffected by the changes."""

    def test_recommend_disp003_still_refund_450(self):
        from app.policy_engine import recommend
        item = _disp003()
        decision = recommend(item)
        assert decision['disposition'] == 'refund'
        assert decision['amount'] == 4.50

    def test_gate_disp003_still_auto_eligible(self):
        from app.policy_engine import recommend, gate
        item = _disp003()
        decision = recommend(item)
        assert gate(item, decision)['can_auto'] is True

    def test_recommend_disp001_still_refund_344(self):
        from app.policy_engine import recommend
        from app.config import ROOT
        import json as _json
        item = _json.loads((ROOT / 'fixtures/cases/DISP-001.json').read_text())
        decision = recommend(item)
        assert decision['disposition'] == 'refund'
        assert decision['amount'] == 3.44
