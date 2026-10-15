"""Targeted live probe for DisputeOrchestrator and PolicyPrecedent only.

Runs ONLY these two advisory agents against DISP-003 with live ADK/Gemini.
Reports sanitized validation status, error codes, and tool names.
Does NOT run the full six-agent evaluation or process_case.

Usage:
  AI_MODE=adk APP_MODE=memory .venv/bin/python -m scripts.probe_advisory_agents

NEVER run automatically. Requires explicit human invocation with valid credentials.
"""
import asyncio, json, os, sys, time
from pathlib import Path

# Ensure backend/ is on sys.path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import ROOT, setting, is_live_ai
from app.repository import set_repo, MemoryRepository
from app.services import seed_cases
from app.agents import call_adk, validate_agent_output, has_agent_failures
from app.policy import select_candidates


async def probe_advisory_agents():
    if not is_live_ai():
        raise SystemExit('Set AI_MODE=adk; this probe requires live Gemini calls')
    if setting('APP_MODE', 'memory') != 'memory':
        raise SystemExit('Run with APP_MODE=memory')

    # Seed and get DISP-003
    set_repo(MemoryRepository())
    seed_cases()
    from app.services import get_case
    case = get_case('DISP-003')

    # Build the same payload that evaluate_agents sends
    from app.policy_engine import recommend
    candidate = recommend(case)
    context = select_candidates(case['category'], case.get('description', ''),
                               case.get('fraud_flags', 0), False)
    payload = {
        'case': {k: v for k, v in case.items()
                 if k in ('case_id', 'category', 'description', 'facts', 'evidence', 'dispute_amount')},
        'routing_index_candidates': context,
        'policy_version': '2.1',
        'safety_only_summarize': False,
    }

    results = []
    for role in ('DisputeOrchestrator', 'PolicyPrecedent'):
        start = time.perf_counter()
        try:
            raw = await call_adk(role, payload)
            elapsed = time.perf_counter() - start
            result = raw['result']
            results.append({
                'agent_name': role,
                'latency_seconds': round(elapsed, 3),
                'parse_failed': result.get('parse_failed', False),
                'failure_kind': result.get('failure_kind'),
                'missing_fields': result.get('missing_fields', []),
                'invalid_fields': result.get('invalid_fields', []),
                'validation_error_code': result.get('validation_error_code'),
                'recommended_disposition': result.get('recommended_disposition'),
                'tool_calls': sorted({tc for evt in raw.get('trace', [])
                                      for tc in evt.get('tool_calls', []) if isinstance(tc, str)}),
                'agent_error': result.get('agent_error', False),
                'error_code': result.get('error_code'),
            })
        except Exception as exc:
            elapsed = time.perf_counter() - start
            # Use the same _safe_error categorization
            from scripts.live_eval import _safe_error
            results.append({
                'agent_name': role,
                'latency_seconds': round(elapsed, 3),
                'parse_failed': True,
                'failure_kind': 'agent_exception',
                'missing_fields': [],
                'invalid_fields': [],
                'validation_error_code': _safe_error(exc),
                'agent_error': True,
                'error_code': _safe_error(exc),
                'recommended_disposition': 'undetermined',
                'tool_calls': [],
            })

    report = {
        'timestamp_utc': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'model': setting('GEMINI_MODEL', 'gemini-2.5-flash'),
        'case_id': 'DISP-003',
        'probe_scope': 'DisputeOrchestrator and PolicyPrecedent only',
        'det_candidate': {'disposition': candidate['disposition'], 'amount': candidate['amount']},
        'results': results,
        'any_failures': has_agent_failures({r['agent_name']: r for r in results}),
    }

    # Save report
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    suffix = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y%m%d-%H%M%S')
    path = reports / f'probe-advisory-{suffix}.json'
    path.write_text(json.dumps(report, indent=2) + '\n')

    print(json.dumps(report, indent=2, default=str))
    print(f'\nProbe report saved to {path}')
    return report


if __name__ == '__main__':
    asyncio.run(probe_advisory_agents())
