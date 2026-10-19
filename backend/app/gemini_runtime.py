"""Bounded, schema-validated ADK calls shared by text and image analysis."""
from __future__ import annotations
import asyncio
import json
import logging
import random
import time
import uuid
import weakref
from pydantic import ValidationError
from .config import setting

ATTEMPT_TIMEOUT_SECONDS = 25
REQUEST_BUDGET_SECONDS = 115
QUEUE_TIMEOUT_SECONDS = 115
MAX_ATTEMPTS = 2
_slots = weakref.WeakKeyDictionary()


def _limiter():
    loop = asyncio.get_running_loop()
    if loop not in _slots:
        _slots[loop] = asyncio.Semaphore(2)
    return _slots[loop]


def retryable(exc):
    return (isinstance(exc, (TimeoutError, ConnectionError, ValidationError, json.JSONDecodeError))
            or getattr(exc, 'code', None) in (408, 429, 499, 500, 502, 503, 504))


async def _run_once(name, instruction, schema, parts, model_name):
    from google.adk.agents import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.runners import Runner
    from google.adk.planners import BuiltInPlanner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    thinking = (types.ThinkingConfig(thinking_level='LOW') if model_name.startswith('gemini-3')
                else types.ThinkingConfig(thinking_budget=512))
    model = Gemini(model=model_name, retry_options=types.HttpRetryOptions(attempts=1))
    agent = LlmAgent(name=name, model=model, instruction=instruction,
        output_schema=schema, disallow_transfer_to_parent=True, disallow_transfer_to_peers=True, planner=BuiltInPlanner(thinking_config=thinking),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.1, max_output_tokens=2048,
            http_options=types.HttpOptions(timeout=38000)))
    svc = InMemorySessionService()
    sid = uuid.uuid4().hex
    await svc.create_session(app_name='ryderesolve', user_id='synthetic-demo', session_id=sid)
    runner = Runner(agent=agent, app_name='ryderesolve', session_service=svc)
    try:
        text = ''
        async for event in runner.run_async(user_id='synthetic-demo', session_id=sid,
                new_message=types.Content(role='user', parts=parts)):
            if event.is_final_response() and event.content:
                text = ''.join(p.text for p in event.content.parts or [] if getattr(p, 'text', None))
        return schema.model_validate_json(text).model_dump()
    finally:
        # Each attempt owns its client; release sockets even on cancellation.
        await model.api_client.aio.aclose()
        model.api_client.close()


async def generate_structured(name, instruction, schema, parts):
    slots = _limiter()
    await asyncio.wait_for(slots.acquire(), timeout=QUEUE_TIMEOUT_SECONDS)
    start = time.monotonic()
    retries = []
    correction = ""
    primary = setting('GEMINI_MODEL', 'gemini-2.5-flash')
    fallback = setting('GEMINI_FALLBACK_MODEL', '')
    models = [primary] + ([fallback] if fallback and fallback != primary else [])
    total_attempts = 0
    try:
        for model_name in models:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                total_attempts += 1
                try:
                    remaining = REQUEST_BUDGET_SECONDS - (time.monotonic() - start)
                    if remaining <= 0:
                        raise TimeoutError('Gemini request budget exhausted')
                    output = await asyncio.wait_for(
                        _run_once(name, instruction + correction, schema, parts, model_name),
                        timeout=min(ATTEMPT_TIMEOUT_SECONDS, remaining))
                    return output, {'agent': name, 'final': True, 'attempts': total_attempts,
                        'model': model_name, 'primary_model': primary,
                        'fallback_used': model_name != primary,
                        'latency_ms': round((time.monotonic()-start)*1000),
                        'structured_output': True, 'retry_reasons': retries}
                except Exception as exc:
                    if asyncio.current_task().cancelling():
                        raise asyncio.CancelledError from exc
                    logging.getLogger(__name__).warning(
                        'Gemini attempt failed: agent=%s model=%s attempt=%s type=%s code=%s',
                        name, model_name, attempt, type(exc).__name__, getattr(exc, 'code', None))
                    if not retryable(exc) or time.monotonic()-start >= REQUEST_BUDGET_SECONDS:
                        raise
                    retries.append(str(getattr(exc, 'code', type(exc).__name__)))
                    if isinstance(exc, ValidationError):
                        correction = '\nCorrect the previous output validation errors: ' + json.dumps(exc.errors(include_input=False, include_context=False, include_url=False))
                    if attempt == MAX_ATTEMPTS:
                        if model_name == models[-1]:
                            raise
                        break
                    await asyncio.sleep(min(2 ** (attempt-1), 4) + random.uniform(0, 0.5))
    finally:
        slots.release()
