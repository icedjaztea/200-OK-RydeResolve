"""Regression tests for Step 25: validation diagnostics for DisputeOrchestrator and PolicyPrecedent.

Tests that validate_agent_output emits safe structured diagnostics
(failure_kind, missing_fields, invalid_fields, validation_error_code)
and that the prompt explicitly instructs advisory agents to use "undetermined".

Also tests that _safe_diagnostics in live_eval captures per-agent validation
details without leaking raw model responses, credentials, or evidence.
"""
import asyncio, json, os, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault('AI_MODE', 'mock')
os.environ.setdefault('APP_MODE', 'memory')

from app.agents import (
    validate_agent_output,
    _sanitize_error,
    has_agent_failures,
    agent_instructions,
    evaluate_agents,
)
from app.services import process_case, seed_cases
from app.repository import repo, MemoryRepository, set_repo


# ── validate_agent_output structured diagnostics ──────────────────────────

class TestValidationDiagnostics:

    def test_missing_fields_emits_failure_kind_and_list(self):
        out = {'summary': 'ok', 'recommended_disposition': 'undetermined'}
        result = validate_agent_output('DisputeOrchestrator', out)
        assert result['parse_failed'] is True
        assert result['failure_kind'] == 'missing_fields'
        assert 'role' in result['missing_fields']
        assert result['invalid_fields'] == []
        assert result['validation_error_code'] == 'VAL_FAIL'

    def test_invalid_disposition_emits_failure_kind_and_list(self):
        out = {'role': 'DisputeOrchestrator', 'summary': 'ok', 'recommended_disposition': 'pending'}
        result = validate_agent_output('DisputeOrchestrator', out)
        assert result['parse_failed'] is True
        assert result['failure_kind'] == 'invalid_fields'
        assert 'recommended_disposition' in result['invalid_fields']
        assert result['missing_fields'] == []
        assert result['validation_error_code'] == 'VAL_FAIL'

    def test_missing_and_invalid_emits_combined_failure_kind(self):
        out = {'summary': 'ok', 'recommended_disposition': 'n/a'}
        result = validate_agent_output('PolicyPrecedent', out)
        assert result['parse_failed'] is True
        assert result['failure_kind'] == 'missing_and_invalid_fields'
        assert 'role' in result['missing_fields']
        assert 'recommended_disposition' in result['invalid_fields']

    def test_non_dict_emits_failure_kind_invalid_json(self):
        result = validate_agent_output('DisputeOrchestrator', 'not a dict')
        assert result['parse_failed'] is True
        assert result['failure_kind'] == 'invalid_json'
        assert result['validation_error_code'] == 'VAL_NOT_JSON_OBJECT'
        assert 'role' in result['missing_fields']

    def test_valid_output_has_no_diagnostics(self):
        out = {'role': 'DisputeOrchestrator', 'summary': 'ok', 'recommended_disposition': 'undetermined'}
        result = validate_agent_output('DisputeOrchestrator', out)
        assert not result.get('parse_failed')
        assert 'failure_kind' not in result
        assert 'missing_fields' not in result
        assert 'invalid_fields' not in result

    def test_judge_missing_amount_emits_invalid_fields(self):
        out = {'role': 'Judge', 'summary': 'ok', 'recommended_disposition': 'refund'}
        result = validate_agent_output('Judge', out)
        assert result['parse_failed'] is True
        assert 'recommended_amount' in result['invalid_fields']


# ── _sanitize_error structured diagnostics ───────────────────────────────

class TestSanitizeErrorDiagnostics:

    def test_exception_has_agent_exception_failure_kind(self):
        exc = RuntimeError('something broke')
        result = _sanitize_error(exc, 'DisputeOrchestrator')
        assert result['failure_kind'] == 'agent_exception'
        assert result['validation_error_code'] == 'ADK_RUNTIME_ERROR'
        assert result['missing_fields'] == []
        assert result['invalid_fields'] == []

    def test_no_raw_message_in_diagnostics(self):
        exc = RuntimeError('api_key=AIzaSySECRET in log')
        result = _sanitize_error(exc, 'PolicyPrecedent')
        serialized = json.dumps(result, default=str)
        assert 'AIzaSy' not in serialized
        assert 'SECRET' not in serialized


# ── Prompt contract for advisory agents ──────────────────────────────────

class TestAdvisoryAgentPromptContract:

    def test_dispute_orchestrator_prompt_includes_undetermined(self):
        prompt = agent_instructions('DisputeOrchestrator')
        assert 'undetermined' in prompt
        assert 'MUST set recommended_disposition' in prompt

    def test_policy_precedent_prompt_includes_undetermined(self):
        prompt = agent_instructions('PolicyPrecedent')
        assert 'undetermined' in prompt
        assert 'MUST set recommended_disposition' in prompt

    def test_rider_advocate_prompt_does_not_require_undetermined(self):
        """Advocates and Judge can set real dispositions; only advisory agents must use undetermined."""
        prompt = agent_instructions('RiderAdvocate')
        assert 'MUST set recommended_disposition' not in prompt

    def test_judge_prompt_does_not_require_undetermined(self):
        prompt = agent_instructions('Judge')
        assert 'MUST set recommended_disposition' not in prompt


# ── live_eval _safe_diagnostics captures per-agent validation ─────────────

class TestLiveEvalDiagnosticsCapture:

    def test_agent_validation_details_captured(self):
        from scripts.live_eval import _safe_diagnostics
        item = {
            'candidate': {'disposition': 'refund', 'amount': 4.5, 'rule_ids': ['FA-3.1']},
            'agent_outputs': {
                'DisputeOrchestrator': {
                    'agent_name': 'DisputeOrchestrator',
                    'role': 'DisputeOrchestrator',
                    'summary': 'classified',
                    'recommended_disposition': 'pending',
                    'parse_failed': True,
                    'failure_kind': 'invalid_fields',
                    'missing_fields': [],
                    'invalid_fields': ['recommended_disposition'],
                    'validation_error_code': 'VAL_FAIL',
                },
                'Judge': {
                    'agent_name': 'Judge',
                    'role': 'Judge',
                    'summary': 'refund 4.50',
                    'recommended_disposition': 'refund',
                    'recommended_amount': 4.50,
                },
            },
            'agent_trace': [{'agent': 'DisputeOrchestrator', 'tool_calls': ['get_rulebook_candidates']}],
            'gate': {'path': 'HUMAN_REVIEW', 'reasons': ['agent failure'], 'blocking_rules': []},
        }
        diag = _safe_diagnostics(item)
        assert 'DisputeOrchestrator' in diag['failed_agent_names']
        assert 'Judge' not in diag['failed_agent_names']
        # Per-agent details
        details = diag['agent_validation_details']
        assert len(details) == 1
        d = details[0]
        assert d['agent_name'] == 'DisputeOrchestrator'
        assert d['failure_kind'] == 'invalid_fields'
        assert d['missing_fields'] == []
        assert d['invalid_fields'] == ['recommended_disposition']
        assert d['validation_error_code'] == 'VAL_FAIL'
        assert d['agent_error'] is False

    def test_agent_validation_details_for_exception_errors(self):
        from scripts.live_eval import _safe_diagnostics
        item = {
            'candidate': {'disposition': 'refund', 'amount': 4.5, 'rule_ids': []},
            'agent_outputs': {
                'PolicyPrecedent': {
                    'agent_name': 'PolicyPrecedent',
                    'role': 'PolicyPrecedent',
                    'summary': 'Agent PolicyPrecedent failed: ADK_RUNTIME_ERROR',
                    'recommended_disposition': 'undetermined',
                    'parse_failed': True,
                    'agent_error': True,
                    'error_code': 'ADK_RUNTIME_ERROR',
                    'failure_kind': 'agent_exception',
                    'missing_fields': [],
                    'invalid_fields': [],
                    'validation_error_code': 'ADK_RUNTIME_ERROR',
                },
            },
            'agent_trace': [{'agent': 'PolicyPrecedent', 'error_code': 'ADK_RUNTIME_ERROR'}],
            'gate': {'path': 'HUMAN_REVIEW', 'reasons': ['agent failure'], 'blocking_rules': []},
        }
        diag = _safe_diagnostics(item)
        assert 'PolicyPrecedent' in diag['failed_agent_names']
        details = diag['agent_validation_details']
        assert details[0]['failure_kind'] == 'agent_exception'
        assert details[0]['agent_error'] is True
        assert details[0]['validation_error_code'] == 'ADK_RUNTIME_ERROR'

    def test_no_raw_evidence_in_validation_details(self):
        from scripts.live_eval import _safe_diagnostics
        item = {
            'candidate': {'disposition': 'refund', 'amount': 4.5, 'rule_ids': []},
            'agent_outputs': {
                'DisputeOrchestrator': {
                    'agent_name': 'DisputeOrchestrator',
                    'role': 'DisputeOrchestrator',
                    'summary': 'api_key=AIzaSySECRET and rider_name=Alice',
                    'recommended_disposition': 'n/a',
                    'parse_failed': True,
                    'failure_kind': 'invalid_fields',
                    'missing_fields': [],
                    'invalid_fields': ['recommended_disposition'],
                    'validation_error_code': 'VAL_FAIL',
                    'validation_error': 'Unrecognized disposition: n/a; evidence: raw chat transcript',
                },
            },
            'agent_trace': [],
            'gate': {'path': 'HUMAN_REVIEW', 'reasons': ['agent failure'], 'blocking_rules': []},
        }
        diag = _safe_diagnostics(item)
        serialized = json.dumps(diag, default=str)
        # Validation details should NOT contain raw evidence or credentials from the summary field
        assert 'AIzaSy' not in serialized
        assert 'Alice' not in serialized
        assert 'raw chat transcript' not in serialized


# ── End-to-end: advisory agents with undetermined pass validation ────────

class TestAdvisoryAgentsPassWithUndetermined:
    """Verify that advisory agents returning 'undetermined' pass validation."""

    def test_dispute_orchestrator_undetermined_passes(self):
        out = {'role': 'DisputeOrchestrator', 'summary': 'routed fare dispute',
               'recommended_disposition': 'undetermined'}
        result = validate_agent_output('DisputeOrchestrator', out)
        assert not result.get('parse_failed')

    def test_policy_precedent_undetermined_passes(self):
        out = {'role': 'PolicyPrecedent', 'summary': 'compared to v2.1 rules',
               'recommended_disposition': 'undetermined'}
        result = validate_agent_output('PolicyPrecedent', out)
        assert not result.get('parse_failed')


# ── Full pipeline: advisory agents with invalid disposition force review ─

class TestAdvisoryAgentInvalidDispositionForcesReview:
    """End-to-end: advisory agents with non-standard disposition → HUMAN_REVIEW."""

    def test_advisory_agent_invalid_disposition_forces_review(self, monkeypatch):
        seed_cases()
        monkeypatch.setenv('AI_MODE', 'adk')

        async def fake_call_adk(role, payload):
            if role == 'DisputeOrchestrator':
                return {
                    'result': validate_agent_output(role, {
                        'role': role, 'summary': 'classified',
                        'recommended_disposition': 'pending',  # invalid
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            if role == 'PolicyPrecedent':
                return {
                    'result': validate_agent_output(role, {
                        'role': role, 'summary': 'compared rules',
                        'recommended_disposition': 'n/a',  # invalid
                    }),
                    'trace': [{'agent': role, 'final': True}],
                }
            return {
                'result': validate_agent_output(role, {
                    'role': role, 'summary': f'{role} ok',
                    'recommended_disposition': 'refund' if role == 'Judge' else 'undetermined',
                    'recommended_amount': 4.50 if role == 'Judge' else None,
                }),
                'trace': [{'agent': role, 'final': True}],
            }

        monkeypatch.setattr('app.agents.call_adk', fake_call_adk)
        result = asyncio.run(process_case('DISP-003'))

        assert result['path'] == 'HUMAN_REVIEW'
        assert result['gate']['can_auto'] is False
        assert result['agent_outputs']['DisputeOrchestrator']['parse_failed'] is True
        assert result['agent_outputs']['PolicyPrecedent']['parse_failed'] is True
        assert has_agent_failures(result['agent_outputs']) is True
        # Verify structured diagnostics are present
        assert result['agent_outputs']['DisputeOrchestrator']['failure_kind'] == 'invalid_fields'
        assert 'recommended_disposition' in result['agent_outputs']['DisputeOrchestrator']['invalid_fields']

    def test_advisory_agents_with_undetermined_and_valid_judge_auto_resolves(self, monkeypatch):
        """When advisory agents return undetermined and Judge matches engine → AUTO_ELIGIBLE."""
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
