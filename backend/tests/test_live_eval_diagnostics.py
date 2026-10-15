"""Offline tests for _safe_diagnostics in live_eval.

Verifies that safe diagnostic fields are correctly extracted from a
processed case dict, and that no raw evidence, credentials, prompts,
or full agent responses leak into the diagnostics output.
"""
import asyncio, json, os, sys
from pathlib import Path

# Ensure backend/ is on sys.path so 'app' and 'scripts' resolve
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault('AI_MODE', 'mock')
os.environ.setdefault('APP_MODE', 'memory')

from scripts.live_eval import _safe_diagnostics, _safe_error


def _make_case_item():
    """Build a synthetic processed case item mimicking process_case output."""
    return {
        'case_id': 'DISP-003',
        'path': 'HUMAN_REVIEW',
        'candidate': {
            'disposition': 'refund',
            'amount': 4.5,
            'currency': 'SGD',
            'rule_ids': ['FA-3.1', 'FA-3.2', 'FA-3.3-B', 'FA-3.4', 'FA-3.5'],
            'reason': 'Unnotified surge increase; refund only the verified differential',
        },
        'agent_outputs': {
            'DisputeOrchestrator': {
                'agent_name': 'DisputeOrchestrator',
                'role': 'DisputeOrchestrator',
                'summary': 'Routed fare dispute to candidate rules',
                'recommended_disposition': 'undetermined',
            },
            'RiderAdvocate': {
                'agent_name': 'RiderAdvocate',
                'role': 'RiderAdvocate',
                'summary': 'Rider suffered unnotified surge increase',
                'recommended_disposition': 'undetermined',
            },
            'DriverAdvocate': {
                'agent_name': 'DriverAdvocate',
                'role': 'DriverAdvocate',
                'summary': 'Driver position summarized',
                'recommended_disposition': 'undetermined',
            },
            'Judge': {
                'agent_name': 'Judge',
                'role': 'Judge',
                'summary': 'Judge proposed a different disposition',
                'recommended_disposition': 'no_action',
                'recommended_amount': None,
            },
        },
        'agent_trace': [
            {'agent': 'DisputeOrchestrator', 'final': False, 'tool_calls': ['get_rulebook_candidates']},
            {'agent': 'DisputeOrchestrator', 'final': True},
            {'agent': 'Judge', 'final': False, 'tool_calls': ['get_full_policy_rules', 'get_relevant_precedents']},
            {'agent': 'Judge', 'final': True},
        ],
        'gate': {
            'can_auto': False,
            'path': 'HUMAN_REVIEW',
            'reasons': ['ADK Judge proposal inconsistent with deterministic policy'],
            'blocking_rules': [],
        },
    }


class TestSafeDiagnosticsExtraction:
    """Verify _safe_diagnostics extracts the 7 required fields correctly."""

    def setUp(self):
        self.item = _make_case_item()

    def test_det_candidate_disposition_and_amount(self):
        diag = _safe_diagnostics(self.setUp() or _make_case_item())
        assert diag['det_candidate_disposition'] == 'refund'
        assert diag['det_candidate_amount'] == 4.5

    def test_judge_disposition_and_amount(self):
        item = _make_case_item()
        diag = _safe_diagnostics(item)
        assert diag['judge_disposition'] == 'no_action'
        assert diag['judge_amount'] is None

    def test_gate_path_blocking_rules_and_reasons(self):
        item = _make_case_item()
        diag = _safe_diagnostics(item)
        assert diag['gate_path'] == 'HUMAN_REVIEW'
        assert diag['gate_blocking_rules'] == []
        assert 'ADK Judge proposal inconsistent with deterministic policy' in diag['gate_reasons']

    def test_failed_agent_names_empty_when_no_failures(self):
        item = _make_case_item()
        diag = _safe_diagnostics(item)
        assert diag['failed_agent_names'] == []

    def test_failed_agent_names_populated_on_parse_failed(self):
        item = _make_case_item()
        item['agent_outputs']['RiderAdvocate']['parse_failed'] = True
        diag = _safe_diagnostics(item)
        assert 'RiderAdvocate' in diag['failed_agent_names']

    def test_judge_consistency_passed_false_when_judge_disagrees(self):
        item = _make_case_item()
        # Judge said no_action, candidate says refund — should be False
        # judge_consistency only runs its strict check in live AI mode
        old = os.environ.get('AI_MODE')
        os.environ['AI_MODE'] = 'adk'
        try:
            from app.agents import judge_consistency
            diag = _safe_diagnostics(item)
            assert diag['judge_consistency_passed'] is False
        finally:
            if old is not None:
                os.environ['AI_MODE'] = old
            else:
                os.environ.pop('AI_MODE', None)

    def test_judge_consistency_passed_true_when_judge_agrees(self):
        item = _make_case_item()
        item['agent_outputs']['Judge']['recommended_disposition'] = 'refund'
        item['agent_outputs']['Judge']['recommended_amount'] = 4.5
        diag = _safe_diagnostics(item)
        assert diag['judge_consistency_passed'] is True

    def test_adk_tools_invoked_collected_from_trace(self):
        item = _make_case_item()
        diag = _safe_diagnostics(item)
        assert 'get_rulebook_candidates' in diag['adk_tools_invoked']
        assert 'get_full_policy_rules' in diag['adk_tools_invoked']
        assert 'get_relevant_precedents' in diag['adk_tools_invoked']

    def test_sanitized_failure_codes_empty_when_no_errors(self):
        item = _make_case_item()
        diag = _safe_diagnostics(item)
        assert diag['sanitized_failure_codes'] == []

    def test_sanitized_failure_codes_populated_on_agent_error(self):
        item = _make_case_item()
        item['agent_outputs']['Judge']['agent_error'] = True
        item['agent_outputs']['Judge']['error_code'] = 'ADK_RUNTIME_ERROR'
        diag = _safe_diagnostics(item)
        codes = {fc['agent']: fc['error_code'] for fc in diag['sanitized_failure_codes']}
        assert codes.get('Judge') == 'ADK_RUNTIME_ERROR'

    def test_no_raw_evidence_in_diagnostics(self):
        item = _make_case_item()
        # Inject raw evidence-like content that should never appear in diagnostics
        item['agent_outputs']['Judge']['summary'] = (
            'Secret API key: AKIAIOSFODNN7EXAMPLE, '
            'Bearer ya29.secret-token, evidence: raw chat transcript with personal data'
        )
        diag = _safe_diagnostics(item)
        serialized = json.dumps(diag, default=str)
        assert 'AKIAIOSFODNN7EXAMPLE' not in serialized
        assert 'ya29.secret-token' not in serialized
        assert 'raw chat transcript' not in serialized

    def test_missing_candidate_returns_none_values(self):
        item = {'path': 'HUMAN_REVIEW', 'agent_outputs': {}, 'agent_trace': [], 'gate': {}}
        diag = _safe_diagnostics(item)
        assert diag['det_candidate_disposition'] is None
        assert diag['det_candidate_amount'] is None
        assert diag['judge_disposition'] is None
        assert diag['judge_amount'] is None
        assert diag['judge_consistency_passed'] is None

    def test_empty_case_returns_safe_defaults(self):
        item = {}
        diag = _safe_diagnostics(item)
        assert diag['det_candidate_disposition'] is None
        assert diag['failed_agent_names'] == []
        assert diag['adk_tools_invoked'] == []
        assert diag['sanitized_failure_codes'] == []
        assert diag['gate_blocking_rules'] == []
        assert diag['gate_reasons'] == []
