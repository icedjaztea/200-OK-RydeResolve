"""FastAPI demo service. Only synthetic cases; role-specific demo keys, no production auth."""
from __future__ import annotations
import hmac, os
from fastapi import FastAPI, HTTPException, Header, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .config import setting
from .models import CaseCreate, ClarificationReply, EvidenceUpload, ReviewerDecision, LearningApproval
from .repository import repo
from .services import (create_case,seed_cases,get_case,process_case,reply_to_clarification,
                       add_verified_demo_evidence,human_review,evaluate_suite,
                       evaluate_learning,approve_learning,rollback_learning,verify_event_chain,add_file_evidence,
                       build_review_packet)
from .policy import contract_report, signoff_valid, load_policy
from .storage import store_blob
from .image_analysis import describe_damage_image
from .evidence import now

app=FastAPI(title='RydeResolve - SYNTHETIC demo',version='0.2.0')
origins=[s.strip() for s in setting('ALLOWED_ORIGINS','http://localhost:3000').split(',') if s.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,
    allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Demo-Key'])


def demo_role(x_demo_key:str|None=Header(default=None)):
    # These are demo passcodes, not production authentication. No caller-supplied role headers.
    for role,var in [('reviewer','DEMO_REVIEWER_KEY'),('rider','DEMO_RIDER_KEY'),('driver','DEMO_DRIVER_KEY')]:
        expected=setting(var,f'change-{role}-key')
        if setting('APP_MODE','memory')=='firestore' and expected.startswith('change-'):
            raise HTTPException(status_code=503,detail='Replace default demo keys before hosted deployment')
        if x_demo_key and hmac.compare_digest(x_demo_key,expected):return role
    raise HTTPException(status_code=401,detail='Invalid synthetic-demo key')

def reviewer(role=Depends(demo_role)):
    if role!='reviewer':raise HTTPException(status_code=403,detail='Reviewer key required')
    return role

def actor(role=Depends(demo_role)):
    return role

def fail(exc):
    if isinstance(exc,KeyError):raise HTTPException(status_code=404,detail=str(exc)) from exc
    if isinstance(exc,PermissionError):raise HTTPException(status_code=403,detail=str(exc)) from exc
    if isinstance(exc,ValueError):raise HTTPException(status_code=400,detail=str(exc)) from exc
    raise exc

@app.get('/health')
def health():
    return {'ok':True,'synthetic_only':True,'storage_mode':setting('APP_MODE','memory'),
            'ai_mode':setting('AI_MODE','mock'),'policy_contract':contract_report(),
            'team_signoff_valid':signoff_valid(),'timestamp':now()}

@app.get('/cases')
def cases(_=Depends(actor)):
    return [{'case_id':x['case_id'],'category':x['category'],'status':x['status'],
             'path':x.get('path'),'dispute_amount':x.get('dispute_amount')} for x in repo().list_cases()]

@app.post('/cases/seed')
def seed(_=Depends(reviewer)):
    return {'created':seed_cases()}

@app.post('/cases')
def new_case(item:CaseCreate,_=Depends(actor)):
    if not item.synthetic:raise HTTPException(400,'Only synthetic cases are permitted')
    new=item.model_dump()
    new['source_trust']='UNVERIFIED_USER_REPORT'
    try:return create_case(new)
    except Exception as e:fail(e)

@app.get('/cases/{case_id}')
def case_detail(case_id:str,_=Depends(actor)):
    try:return get_case(case_id)
    except Exception as e:fail(e)

@app.get('/cases/{case_id}/review-packet')
def review_packet(case_id:str,_=Depends(reviewer)):
    try:return build_review_packet(case_id)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/process')
async def process(case_id:str,_=Depends(actor)):
    try:return await process_case(case_id)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/clarifications/{request_id}/reply')
def reply(case_id:str,request_id:str,item:ClarificationReply,role=Depends(actor)):
    try:return reply_to_clarification(case_id,request_id,item.answer,role)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/evidence')
def evidence(case_id:str,item:EvidenceUpload,_=Depends(reviewer)):
    try:return add_verified_demo_evidence(case_id,item.field,item.value,item.provenance,item.evidence_timestamp)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/files')
async def upload(case_id:str,file:UploadFile=File(...),_=Depends(reviewer)):
    try:
        get_case(case_id)
        data=await file.read(5*1024*1024+1)
        stored=store_blob(case_id,file.filename or 'document',file.content_type or '',data)
        analysis=await describe_damage_image(data,file.content_type or '',case_id)
        add_file_evidence(case_id,stored,analysis)
        return {'file':stored,'image_analysis':analysis}
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/review')
def decide(case_id:str,body:ReviewerDecision,_=Depends(reviewer)):
    try:return human_review(case_id,body.model_dump())
    except Exception as e:fail(e)

@app.get('/cases/{case_id}/verify-audit')
def verify_audit(case_id:str,_=Depends(reviewer)):
    try:return {'valid':verify_event_chain(get_case(case_id))}
    except Exception as e:fail(e)

@app.get('/learning')
def learning(_=Depends(reviewer)):
    return {'proposals':repo().list_proposals(),'released_precedents':repo().list_precedents()}

@app.post('/learning/{proposal_id}/evaluate')
def test_learning(proposal_id:str,_=Depends(reviewer)):
    try:return evaluate_learning(proposal_id)
    except Exception as e:fail(e)

@app.post('/learning/{proposal_id}/approve')
def approve(proposal_id:str,body:LearningApproval,_=Depends(reviewer)):
    try:return approve_learning(proposal_id,body.rationale)
    except Exception as e:fail(e)

@app.get('/evaluation/reference')
def evaluate(_=Depends(reviewer)):
    return evaluate_suite(approved=True)

@app.post('/learning/{proposal_id}/rollback')
def rollback(proposal_id:str,body:LearningApproval,_=Depends(reviewer)):
    try:return rollback_learning(proposal_id,body.rationale)
    except Exception as e:fail(e)
