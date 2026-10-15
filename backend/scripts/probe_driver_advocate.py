"""Targeted live probe for DriverAdvocate only.

Runs ONLY the DriverAdvocate agent against DISP-003 with live ADK/Gemini.
Reports sanitized validation status, model name, latency, and tool-call names.
Does NOT run the full six-agent evaluation or process_case.

Usage:
  AI_MODE=adk APP_MODE=memory .venv/bin/python -m scripts.probe_driver_advocate

NEVER run automatically. Requires explicit human invocation with valid credentials.
"""
import asyncio, json, sys, time
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on sys.path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import ROOT, setting, is_live_ai
from app.repository import set_repo, MemoryRepository
from app.services import seed_cases, get_case
from app.agents import call_adk, validate_agent_output, has_agent_failures, VALID_DISPOSITIONS
from app.policy import select_candidates
from app.policy_engine import recommend


async def probe_driver_advocate():
    if not is_live_ai():
        raise SystemExit('Set AI_MODE=adk; this probe requires live Gemini calls')
    if setting('APP_MODE', 'memory') != 'memory':
        raise SystemExit('Run with APP_MODE=memory')

    # Seed and get DISP-003
    set_repo(MemoryRepository())
    seed_cases()
    case = get_case('DISP-003')

    # Build the same payload that evaluate_agents sends to DriverAdvocate
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

    role = 'DriverAdvocate'
    start = time.perf_counter()
    try:
        raw = await call_adk(role, payload)
        elapsed = time.perf_counter() - start
        result = raw['result']
        entry = {
            'agent_name': role,
            'latency_seconds': round(elapsed, 3),
            'parse_failed': result.get('parse_failed', False),
            'failure_kind': result.get('failure_kind'),
            'missing_fields': result.get('missing_fields', []),
            'invalid_fields': result.get('invalid_fields', []),
            'validation_error_code': result.get('validation_error_code'),
            'recommended_disposition': result.get('recommended_disposition'),
            'is_valid_disposition': result.get('recommended_disposition') in VALID_DISPOSITIONS,
            'tool_calls': sorted({tc for evt in raw.get('trace', [])
                                  for tc in evt.get('tool_calls', []) if isinstance(tc, str)}),
            'agent_error': result.get('agent_error', False),
            'error_code': result.get('error_code'),
        }
    except Exception as exc:
        elapsed = time.perf_counter() - start
        from scripts.live_eval import _safe_error
        entry = {
            'agent_name': role,
            'latency_seconds': round(elapsed, 3),
            'parse_failed': True,
            'failure_kind': 'agent_exception',
            'missing_fields': [],
            'invalid_fields': [],
            'validation_error_code': _safe_error(exc),
            'recommended_disposition': 'undetermined',
            'is_valid_disposition': False,
            'agent_error': True,
            'error_code': _safe_error(exc),
            'tool_calls': [],
        }

    report = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'model': setting('GEMINI_MODEL', 'gemini-2.5-flash'),
        'case_id': 'DISP-003',
        'probe_scope': 'DriverAdvocate only',
        'det_candidate': {'disposition': candidate['disposition'], 'amount': candidate['amount']},
        'accepted_dispositions': sorted(VALID_DISPOSITIONS),
        'result': entry,
        'any_failures': has_agent_failures({entry['agent_name']: entry}),
    }

    # Save report
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    suffix = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    path = reports / f'probe-driver-advocate-{suffix}.json'
    path.write_text(json.dumps(report, indent=2) + '\n')

    print(json.dumps(report, indent=2, default=str))
    print(f'\nProbe report saved to {path}')
    return report


if __name__ == '__main__':
    asyncio.run(probe_driver_advocate())
