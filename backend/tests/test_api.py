from fastapi.testclient import TestClient
from app.main import app
from app.config import setting
from app.services import seed_cases,verify_event_chain
from app.repository import repo
from app.storage import store_blob
from app.services import evaluate_suite

client=TestClient(app)
REVIEW={'X-Demo-Key':setting('DEMO_REVIEWER_KEY','change-reviewer-key')}
RIDER={'X-Demo-Key':setting('DEMO_RIDER_KEY','change-rider-key')}
DRIVER={'X-Demo-Key':setting('DEMO_DRIVER_KEY','change-driver-key')}


def api(method,path,headers=REVIEW,**kwargs):
    return client.request(method,path,headers=headers,**kwargs)

def test_seed_and_12_case_regression_suite():
    assert api('POST','/cases/seed').json()['created']==12
    output=api('GET','/evaluation/reference').json()
    assert output['total']==12
    assert output['all_passed'],output

def test_auto_fare_action_and_retry_no_duplicate():
    seed_cases()
    first=api('POST','/cases/DISP-003/process')
    assert first.status_code==200,first.text
    r=first.json(); assert r['path']=='AUTO_ELIGIBLE';assert r['mock_action']['amount']==4.5
    again=api('POST','/cases/DISP-003/process').json()
    assert again['mock_action']['receipt']==r['mock_action']['receipt']
    assert len(repo().actions)==1
    assert api('GET','/cases/DISP-003/verify-audit').json()['valid']

def test_rider_driver_cannot_process():
    """Rider and Driver are forbidden from the process endpoint (reviewer-only)."""
    seed_cases()
    assert api('POST','/cases/DISP-003/process',headers=RIDER).status_code==403
    assert api('POST','/cases/DISP-003/process',headers=DRIVER).status_code==403

def test_route_and_flagged_noshow_escalation():
    seed_cases()
    assert api('POST','/cases/DISP-001/process').json()['path']=='HUMAN_REVIEW'
    assert api('POST','/cases/DISP-002/process').json()['path']=='HUMAN_REVIEW'

def test_safety_case_has_no_judge_no_mock_payment():
    seed_cases()
    p=api('POST','/cases/DEMO-SAFETY-IN-FARE/process').json()
    assert p['path']=='IMMEDIATE_HUMAN_REVIEW'
    assert 'Judge' not in p['agent_outputs']
    assert 'mock_action' not in p

def test_innovation_a_reply_is_not_evidence_and_reviewed_synthetic_source_changes_case():
    seed_cases()
    p=api('POST','/cases/DEMO-FARE-CLARIFY/process').json()
    assert p['path']=='CLARIFICATION'
    rid=p['clarifications'][-1]['request_id']
    p=api('POST',f'/cases/DEMO-FARE-CLARIFY/clarifications/{rid}/reply',headers=RIDER,json={'answer':'I did not receive any surge notification'}).json()
    assert p['clarifications'][-1]['answer_verification']=='UNVERIFIED_PARTY_ACCOUNT'
    p=api('POST','/cases/DEMO-FARE-CLARIFY/process').json()
    assert p['path']=='HUMAN_REVIEW'  # allegation alone cannot authorize anything
    for field,val in [('rider_notified',False),('notification_log_complete',True)]:
        x=api('POST','/cases/DEMO-FARE-CLARIFY/evidence',json={'field':field,'value':val,'provenance':'SYNTHETIC complete system notification event export'})
        assert x.status_code==200,x.text
    p=api('POST','/cases/DEMO-FARE-CLARIFY/process').json()
    assert p['candidate']['amount']==4.5
    assert p['path']=='AUTO_ELIGIBLE'

def test_reviewer_only_endpoints():
    seed_cases()
    assert api('POST','/cases/seed',headers=RIDER).status_code==403
    assert api('POST','/cases/DISP-001/evidence',headers=DRIVER,json={'field':'rider_notified','value':True,'provenance':'fake'}).status_code==403
    assert api('GET','/cases').status_code==200
    # Open access: any key is accepted, no 401
    assert api('GET','/cases',headers={'X-Demo-Key':'bad'}).status_code==200

def test_innovation_b_requires_regression_and_approval():
    seed_cases()
    api('POST','/cases/DISP-001/process')
    reviewed=api('POST','/cases/DISP-001/review',json={'disposition':'refund','amount':3.44,'reason':'Human approved excess distance refund after review','proposed_precedent':'If reroute 4.3 km with verified traffic and no notice, escalate for reviewer signoff.'})
    assert reviewed.status_code==200,reviewed.text
    pid=reviewed.json()['learning_proposal_id']
    pre=api('POST',f'/learning/{pid}/approve',json={'rationale':'Reviewed policy and regression suite passed'})
    assert pre.status_code==400
    evaluated=api('POST',f'/learning/{pid}/evaluate')
    assert evaluated.status_code==200,evaluated.text
    assert evaluated.json()['evaluation']['regression']['all_passed']
    published=api('POST',f'/learning/{pid}/approve',json={'rationale':'Reviewer verified provenance and regression passed'})
    assert published.status_code==200,published.text
    assert published.json()['precedent']['release_status']=='ACTIVE_APPROVED_PRECEDENT'

def test_audit_event_mutation_detected():
    seed_cases();case=repo().get_case('DISP-003')
    case['events'][0]['details']={'forged':True}
    assert verify_event_chain(case) is False

def test_gcs_local_simulated_store(tmp_path,monkeypatch):
    monkeypatch.setenv('APP_MODE','memory')
    obj=store_blob('UNITTEST','demo.png','image/png',b'\x89PNG\r\n\x1a\n' + b'not_a_real_image')
    assert obj['object_ref'].startswith('local://')
    assert obj['authenticity_verified'] is False


def test_user_submitted_facts_never_auto_authorize():
    new={'case_id':'USER-INPUT-123','trip_id':'T1','category':'fare_dispute','filed_by':'rider',
      'description':'The surge increased with no notice and I want a refund',
      'dispute_amount':4.5,'facts':{'upfront_quote':12,'actual_fare':16.5,'surge_before':1,
      'surge_after':1.5,'rider_notified':False,'notification_log_complete':True,
      'difference_solely_surge':True}}
    created=api('POST','/cases',headers=RIDER,json=new)
    assert created.status_code==200,created.text
    out=api('POST','/cases/USER-INPUT-123/process').json()
    assert out['path']=='HUMAN_REVIEW'
    assert 'mock_action' not in out


def test_damage_image_upload_branch_marks_origin_unknown():
    seed_cases()
    data=b'\x89PNG\r\n\x1a\n'+b'not_a_real_image'
    res=api('POST','/cases/DEMO-DAMAGE-DISPUTED/files',
            files={'file':('demo.png',data,'image/png')})
    assert res.status_code==200,res.text
    payload=res.json()
    assert payload['image_analysis']['authenticity_verdict']=='UNKNOWN'
    assert payload['file']['origin_verified'] is False
    bad=api('POST','/cases/DEMO-DAMAGE-DISPUTED/files',
            files={'file':('bad.png',b'hello','image/png')})
    assert bad.status_code==400


def test_sla_safety_priority():
    seed_cases()
    r=api('POST','/cases/DEMO-SAFETY-IN-FARE/process')
    assert r.status_code==200,r.text
    p=r.json()
    assert p['sla_routing']['priority']=='P0_SAFETY'
    assert p['sla_routing']['target_minutes'] is None


def test_rollback_removes_active_precedent_from_agent_retrieval():
    from app.repository import repo
    from app.services import rollback_learning
    from app.agents import get_relevant_precedents
    case=repo().get_case('DISP-001')
    if not case:
        from app.services import seed_cases
        seed_cases()
    from app.services import human_review, process_case
    import asyncio
    asyncio.run(process_case('DISP-001'))
    case=human_review('DISP-001', {'disposition':'refund','amount':3.44,
        'reason':'Reviewer approved documented excess fare with policy review',
        'proposed_precedent':'Traffic justified and unannounced route above two kilometers requires reviewer authorization.'})
    pid=case['learning_proposal_id']
    from app.services import evaluate_learning, approve_learning
    evaluate_learning(pid)
    approve_learning(pid, 'Approved after checking rule references and evidence.')
    assert any(x.get('precedent_id')==pid for x in get_relevant_precedents('route_deviation')['reviewed_approved_new_precedents'])
    rollback_learning(pid, 'Incorrect learning statement, rollback required.')
    assert all(x.get('precedent_id')!=pid for x in get_relevant_precedents('route_deviation')['reviewed_approved_new_precedents'])
    assert repo().get_precedent(pid)['release_status']=='ROLLED_BACK'
