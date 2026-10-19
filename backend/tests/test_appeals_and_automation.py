import asyncio
import copy
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repository import repo
from app import agents, services

client=TestClient(app)
def request(method,path,role='reviewer',**kwargs):
    return client.request(method,path,headers={'X-Demo-Key':role},**kwargs)

def resolved_case():
    services.create_case({'case_id':'ORIGINAL-1','category':'property_damage','trip_id':'TRIP-1',
        'description':'Seat stain after the trip','filed_by':'driver','driver_id':'driver_a','rider_id':'rider_a',
        'dispute_amount':30,'facts':{},'status':'REVIEW_REQUIRED'})
    services.add_file_evidence('ORIGINAL-1',{'sha256':'first','object_ref':'memory/original','content_type':'image/png'},
                               {'mode':'ADK_GEMINI_PIXELS_ONLY','pixel_observation':{'description':'Brown stain'}})
    c=repo().get_case('ORIGINAL-1');c['status']='REVIEW_REQUIRED';repo().save_case(c)
    return services.human_review('ORIGINAL-1',{'disposition':'reject_claim','amount':0,'reason':'No verified evidence links the stain to the trip.'})

def test_complete_appeal_lifecycle_preserves_original_and_isolates_roles():
    original=copy.deepcopy(resolved_case())
    response=request('POST','/cases/ORIGINAL-1/appeals','driver_a',json={'reason':'New photos show additional details of the stain.'})
    assert response.status_code==200,response.text
    appeal=response.json();aid=appeal['case_id']
    assert appeal['appeal_of']=='ORIGINAL-1'
    assert appeal['status']=='AWAITING_CLARIFICATION'
    assert len(appeal['evidence'])==1
    assert 'original_case_context' not in appeal
    assert repo().get_case('ORIGINAL-1')==original
    assert request('POST','/cases/ORIGINAL-1/appeals','driver_a',json={'reason':'Retry same appeal submission'}).json()['case_id']==aid
    assert len([c for c in repo().list_cases() if c.get('appeal_of')])==1
    assert request('POST','/cases/ORIGINAL-1/appeals','driver_b',json={'reason':'Not my original case'}).status_code==404
    assert request('GET',f'/cases/{aid}','rider_b').status_code==404
    rider=request('GET',f'/cases/{aid}','rider_a').json()
    q=rider['clarifications'][0]
    assert q['status']=='PENDING'
    assert rider['notifications'][0]['status']=='DELIVERED'
    assert request('POST',f'/cases/{aid}/process').json()['status']=='AWAITING_CLARIFICATION'
    services.add_file_evidence(aid,{'sha256':'second','object_ref':'memory/new','content_type':'image/png'}, {'mode':'MOCK_NOT_MODEL_OUTPUT'})
    assert repo().get_case(aid)['status']=='AWAITING_CLARIFICATION'
    assert request('POST',f'/cases/{aid}/clarifications/{q["request_id"]}/reply','driver_a',json={'answer':'Wrong party'}).status_code==403
    assert request('POST',f'/cases/{aid}/clarifications/{q["request_id"]}/reply','rider_a',json={'answer':'The stain was already there when I boarded.'}).status_code==200
    result=request('POST',f'/cases/{aid}/process').json()
    assert result['status']=='REVIEW_REQUIRED'
    final=request('POST',f'/cases/{aid}/review',json={'disposition':'reject_claim','amount':0,'reason':'Both accounts and the new photos were reviewed; timing remains unverified.'})
    assert final.status_code==200,final.text
    assert final.json()['status']=='REVIEWED_AND_RESOLVED'
    for role in ('rider_a','driver_a'):
        notes=request('GET',f'/cases/{aid}',role).json()['notifications']
        assert any(n['kind']=='RESOLUTION_RECEIPT' and n['status']=='DELIVERED' for n in notes)
    assert repo().get_case('ORIGINAL-1')==original
    assert request('GET','/cases/ORIGINAL-1','driver_a').json()['appeals'][0]['case_id']==aid
    rows=request('GET','/monitor').json()['cases']
    assert next(c for c in rows if c['case_id']==aid)['appeal_of']=='ORIGINAL-1'
    assert services.verify_event_chain(repo().get_case(aid))

def test_learning_auto_publishes_only_checked_example_and_excludes_appealed_source():
    original=resolved_case();pid=original['learning_proposal_id']
    assert original['learning']['status']=='PUBLISHED'
    assert repo().get_proposal(pid)['evaluation']['source_decision_verified']
    assert any(x['precedent_id']==pid for x in agents.get_relevant_precedents('property_damage')['reviewed_approved_new_precedents'])
    services.create_appeal('ORIGINAL-1','driver','driver_a','Please reconsider the decision with new evidence.')
    assert not agents.get_relevant_precedents('property_damage')['reviewed_approved_new_precedents']

def test_learning_failed_checks_do_not_undo_decision(monkeypatch):
    monkeypatch.setattr(services,'evaluate_suite',lambda **kw:{'all_passed':False,'total':1,'passed':0})
    c=resolved_case()
    assert c['status']=='REVIEWED_AND_RESOLVED'
    assert c['learning']['status']=='CHECKS_FAILED'
    assert repo().list_precedents()==[]

def test_appeal_cannot_auto_resolve_even_with_complete_evidence():
    services.seed_cases()
    asyncio.run(services.process_case('DISP-003'))
    c=repo().get_case('DISP-003')
    appeal=services.create_appeal('DISP-003','rider',c['rider_id'],'Please reconsider the amount that was approved.')
    q=appeal['clarifications'][0]
    services.reply_to_clarification(appeal['case_id'],q['request_id'],'I agree with the original record.','driver',c['driver_id'])
    result=asyncio.run(services.process_case(appeal['case_id']))
    assert result['status']=='REVIEW_REQUIRED'
    assert result['gate']['can_auto'] is False
    assert 'mock_action' not in result

def test_agent_timeout_routes_to_human_review(monkeypatch):
    services.seed_cases()
    async def stalled(*args,**kwargs):await asyncio.sleep(1)
    monkeypatch.setenv('AI_MODE','adk')
    monkeypatch.setattr(agents,'call_adk',stalled)
    monkeypatch.setattr(agents,'AGENT_TIMEOUT_SECONDS',0.001)
    result=asyncio.run(services.process_case('DEMO-FARE-OVER50'))
    assert result['status']=='REVIEW_REQUIRED'
    assert result['gate']['can_auto'] is False
    assert result['agent_outputs']['Judge']['error_code']=='ADK_TIMEOUT_ERROR'
    assert 'mock_action' not in result

def test_notifications_keep_separate_questions_and_skip_unlinked_recipient():
    services.create_case({'case_id':'CUSTOM-1','category':'property_damage','description':'Seat stain report',
                          'filed_by':'driver','driver_id':'driver_a','rider_id':None})
    first=services.request_more_info('CUSTOM-1','driver','When did you notice the stain?')
    q=first['clarifications'][0]
    services.reply_to_clarification('CUSTOM-1',q['request_id'],'After the trip','driver','driver_a')
    second=services.request_more_info('CUSTOM-1','driver','Do you have another photograph?')
    assert len([n for n in second['notifications'] if n['kind']=='CLARIFICATION_REQUEST'])==2
    with pytest.raises(ValueError,match='No rider is linked'):
        services.request_more_info('CUSTOM-1','rider','Please respond to the report.')
    assert all(n.get('recipient')!='rider' for n in repo().get_case('CUSTOM-1')['notifications'])

def test_appeal_inherits_value_basis_and_file_privacy():
    original=resolved_case()
    response=request('POST','/cases/ORIGINAL-1/appeals','driver_a',json={'reason':'Please review my additional evidence.'}).json()
    assert response['dispute_value_basis']=='disputed_remedy_amount'
    assert all('analysis' not in e for e in response['evidence'])
    rider_cases=request('GET','/cases','rider_a').json()
    driver_cases=request('GET','/cases','driver_a').json()
    aid=response['case_id']
    assert next(c for c in rider_cases if c['case_id']==aid)['needs_response']
    assert not next(c for c in driver_cases if c['case_id']==aid)['needs_response']
    view=request('GET','/cases/ORIGINAL-1').json()
    assert view['learning']['status']=='EXCLUDED_AFTER_APPEAL'
    assert repo().get_case('ORIGINAL-1')==original


def test_appeal_safety_restriction_and_pending_response_are_preserved():
    services.seed_cases()
    c=asyncio.run(services.process_case('DEMO-SAFETY-IN-FARE'))
    original=services.human_review(c['case_id'],{'disposition':'no_action','amount':0,'reason':'Reviewer recorded the outcome after investigation.'})
    appeal=services.create_appeal(c['case_id'],'rider',c['rider_id'],'I want this decision to be reviewed again.')
    reviewed=asyncio.run(services.process_case(appeal['case_id']))
    assert reviewed['path']=='IMMEDIATE_HUMAN_REVIEW'
    assert 'Judge' not in reviewed['agent_outputs']
    with pytest.raises(ValueError,match='Wait for'):
        services.human_review(appeal['case_id'],{'disposition':'no_action','amount':0,'reason':'Cannot decide while a response is pending.'})
    assert original['learning']['status']=='NOT_ELIGIBLE'
