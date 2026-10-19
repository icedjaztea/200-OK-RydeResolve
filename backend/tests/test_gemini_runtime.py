import asyncio
import pytest
from pydantic import ValidationError
from app import gemini_runtime as runtime
from app.agents import output_schema
from app.image_analysis import ImageObservation

class ProviderError(Exception):
    def __init__(self,code): self.code=code

@pytest.mark.parametrize('error',[ProviderError(429),ProviderError(499),ProviderError(503),TimeoutError()])
def test_transient_error_retries_once_and_records_attempt(monkeypatch,error):
    attempts=[]
    async def run(*args):
        attempts.append(1)
        if len(attempts)==1: raise error
        return {'caption':'A grey seat.'}
    async def sleep(*args): pass
    monkeypatch.setattr(runtime,'_run_once',run)
    monkeypatch.setattr(runtime.asyncio,'sleep',sleep)
    result,trace=asyncio.run(runtime.generate_structured('Image','',ImageObservation,[]))
    assert result['caption']=='A grey seat.'
    assert trace['attempts']==2

@pytest.mark.parametrize('code',[400,401,403,404])
def test_permanent_errors_are_not_retried(monkeypatch,code):
    monkeypatch.setattr(runtime,'setting',lambda key,default='': {'GEMINI_MODEL':'gemini-3.8-flash','GEMINI_FALLBACK_MODEL':'gemini-3.6-flash'}.get(key,default))
    calls=[]
    async def run(*args): calls.append(1);raise ProviderError(code)
    monkeypatch.setattr(runtime,'_run_once',run)
    with pytest.raises(ProviderError):
        asyncio.run(runtime.generate_structured('Image','',ImageObservation,[]))
    assert len(calls)==1


def test_deadline_cancels_attempts_and_releases_slot(monkeypatch):
    cancelled=[]
    async def run(*args):
        try: await asyncio.Event().wait()
        finally: cancelled.append(True)
    monkeypatch.setattr(runtime,'_run_once',run)
    monkeypatch.setattr(runtime,'ATTEMPT_TIMEOUT_SECONDS',0.01)
    monkeypatch.setattr(runtime,'MAX_ATTEMPTS',1)
    async def check():
        with pytest.raises(TimeoutError):
            await runtime.generate_structured('Image','',ImageObservation,[])
        assert runtime._limiter()._value==2
    asyncio.run(check())
    assert cancelled==[True]


def test_concurrency_is_limited_across_requests(monkeypatch):
    active=0;peak=0
    async def run(*args):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        await asyncio.sleep(.01)
        active-=1
        return {}
    monkeypatch.setattr(runtime,'_run_once',run)
    async def check():
        await asyncio.gather(*(runtime.generate_structured('Image','',ImageObservation,[]) for _ in range(6)))
    asyncio.run(check());assert peak==2


def test_schema_enforces_role_and_financial_boundaries():
    data={'role':'PolicyPrecedent','summary':'Checked policy.', 'supporting_evidence':[],
          'opposing_evidence':[],'uncertainties':[],'policy_rule_ids':[],
          'recommended_disposition':'refund','recommended_amount':3}
    with pytest.raises(ValidationError):output_schema('PolicyPrecedent').model_validate(data)
    data.update(role='Judge',recommended_amount=None)
    with pytest.raises(ValidationError):output_schema('Judge').model_validate(data)
    data.update(recommended_amount=3)
    assert output_schema('Judge').model_validate(data).recommended_amount==3
    with pytest.raises(ValidationError):output_schema('Judge',safety=True).model_validate(data)


def test_invalid_structured_response_gets_one_retry(monkeypatch):
    calls=[]
    async def run(*args):
        calls.append(1)
        if len(calls)==1:ImageObservation.model_validate({'caption':''})
        return {'caption':'A seat.'}
    async def sleep(*args): pass
    monkeypatch.setattr(runtime,'_run_once',run)
    monkeypatch.setattr(runtime.asyncio,'sleep',sleep)
    _,trace=asyncio.run(runtime.generate_structured('Image','',ImageObservation,[]))
    assert trace['attempts']==2


def test_fallback_only_after_primary_retries_and_records_model(monkeypatch):
    calls=[]
    monkeypatch.setattr(runtime,'setting',lambda key,default='': {'GEMINI_MODEL':'gemini-3.8-flash','GEMINI_FALLBACK_MODEL':'gemini-3.6-flash'}.get(key,default))
    async def run(*args):
        calls.append(args[-1])
        if args[-1]=='gemini-3.8-flash': raise ProviderError(429)
        return {'caption':'A seat.'}
    async def sleep(*args): pass
    monkeypatch.setattr(runtime,'_run_once',run)
    monkeypatch.setattr(runtime.asyncio,'sleep',sleep)
    _,trace=asyncio.run(runtime.generate_structured('Image','',ImageObservation,[]))
    assert calls==['gemini-3.8-flash','gemini-3.8-flash','gemini-3.6-flash']
    assert trace['fallback_used'] is True
    assert trace['model']=='gemini-3.6-flash'
    assert trace['primary_model']=='gemini-3.8-flash'


def test_external_cancellation_is_not_retried(monkeypatch):
    calls=[]
    async def run(*args):
        calls.append(1)
        try: await asyncio.Event().wait()
        except asyncio.CancelledError: raise ProviderError(499)
    monkeypatch.setattr(runtime,'_run_once',run)
    async def check():
        task=asyncio.create_task(runtime.generate_structured('Image','',ImageObservation,[]))
        await asyncio.sleep(.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        assert runtime._limiter()._value==2
    asyncio.run(check())
    assert calls==[1]
