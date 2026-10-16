"""FastAPI demo service. Only synthetic cases; role-specific demo keys, no production auth."""
from __future__ import annotations
import hmac, os
from fastapi import FastAPI, HTTPException, Header, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .config import setting
from .models import CaseCreate, ClarificationReply, EvidenceUpload, ReviewerDecision, LearningApproval
from .repository import repo
from .identity import DemoIdentity, authenticate, is_reviewer, is_party, seed_case_owners
from .safe_response import safe_case_for_rider, safe_case_for_driver, safe_case_list_item
from .services import (create_case,seed_cases,get_case,process_case,reply_to_clarification,
                       add_verified_demo_evidence,human_review,evaluate_suite,
                       evaluate_learning,approve_learning,rollback_learning,verify_event_chain,add_file_evidence,
                       build_review_packet)
from .policy import contract_report, signoff_valid, load_policy
from .storage import store_blob
from .image_analysis import describe_damage_image
from .evidence import now

app=FastAPI(title='RydeResolve - SYNTHETIC demo',version='0.3.0')
origins=[s.strip() for s in setting('ALLOWED_ORIGINS','http://localhost:3000').split(',') if s.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,
    allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Demo-Key'])


def demo_auth(x_demo_key:str|None=Header(default=None)) -> DemoIdentity:
    """Authenticate X-Demo-Key and return a DemoIdentity.

    These are demo passcodes, not production authentication.
    The browser never supplies an identity; the server resolves it.
    """
    try:
        return authenticate(x_demo_key)
    except ValueError:
        raise HTTPException(status_code=401,detail='Invalid synthetic-demo key')


def reviewer_only(identity:DemoIdentity=Depends(demo_auth)):
    if not is_reviewer(identity):
        raise HTTPException(status_code=403,detail='Reviewer key required')
    return identity


def any_actor(identity:DemoIdentity=Depends(demo_auth)):
    return identity


def fail(exc):
    if isinstance(exc,KeyError):raise HTTPException(status_code=404,detail=str(exc)) from exc
    if isinstance(exc,PermissionError):raise HTTPException(status_code=403,detail=str(exc)) from exc
    if isinstance(exc,ValueError):raise HTTPException(status_code=400,detail=str(exc)) from exc
    raise exc


# ---------------------------------------------------------------------------
# Case access control — the core isolation layer.
#
# A reviewer can access any case.
# A rider can access only cases where rider_id matches their identity_id.
# A driver can access only cases where driver_id matches their identity_id.
# Inaccessible cases raise KeyError (→ 404) so unauthorized IDs cannot be
# distinguished from non-existent IDs.
#
# Cases missing owner IDs (legacy Firestore docs) are denied to parties
# until a reviewer-authorized migration assigns ownership.
# ---------------------------------------------------------------------------

def _get_case_or_404(case_id:str):
    case=repo().get_case(case_id)
    if case is None:raise KeyError(case_id)
    return case


def _authorize_case_access(case:dict, identity:DemoIdentity):
    """Raise KeyError(→404) if the identity cannot access this case."""
    if is_reviewer(identity):
        return  # reviewer sees all
    if is_party(identity):
        owner_field = f'{identity.role}_id'
        owner_id = case.get(owner_field)
        if owner_id is None:
            # Legacy case without owner assignment — deny party access.
            raise KeyError(case['case_id'])
        if owner_id != identity.identity_id:
            raise KeyError(case['case_id'])
        return
    raise KeyError(case.get('case_id','unknown'))


def _get_authorized_case(case_id:str, identity:DemoIdentity):
    case=_get_case_or_404(case_id)
    _authorize_case_access(case, identity)
    return case


def _safe_case_response(case:dict, identity:DemoIdentity):
    """Return a response filtered through the safe schema for parties."""
    if is_reviewer(identity):
        return case
    if identity.role=='rider':
        return safe_case_for_rider(case)
    if identity.role=='driver':
        return safe_case_for_driver(case)
    return case


@app.get('/health')
def health():
    return {'ok':True,'synthetic_only':True,'storage_mode':setting('APP_MODE','memory'),
            'ai_mode':setting('AI_MODE','mock'),'policy_contract':contract_report(),
            'team_signoff_valid':signoff_valid(),'timestamp':now()}

@app.get('/cases')
def cases(identity:DemoIdentity=Depends(any_actor)):
    all_cases=repo().list_cases()
    if is_reviewer(identity):
        return [safe_case_list_item(c,'reviewer') for c in all_cases]
    # Parties see only their own cases.
    owner_field=f'{identity.role}_id'
    visible=[c for c in all_cases
             if c.get(owner_field) is not None
             and c.get(owner_field)==identity.identity_id]
    return [safe_case_list_item(c,identity.role) for c in visible]

@app.post('/cases/seed')
def seed(_=Depends(reviewer_only)):
    return {'created':seed_cases()}

@app.post('/cases')
def new_case(item:CaseCreate, identity:DemoIdentity=Depends(any_actor)):
    if not item.synthetic:raise HTTPException(400,'Only synthetic cases are permitted')
    new=item.model_dump()
    new['source_trust']='UNVERIFIED_USER_REPORT'
    # Server-assigned ownership. Never trust caller-supplied ownership IDs.
    if identity.role=='rider':
        new.setdefault('rider_id',identity.identity_id)
    elif identity.role=='driver':
        new.setdefault('driver_id',identity.identity_id)
    try:return _safe_case_response(create_case(new),identity)
    except Exception as e:fail(e)

@app.get('/cases/{case_id}')
def case_detail(case_id:str, identity:DemoIdentity=Depends(any_actor)):
    try:
        case=_get_authorized_case(case_id,identity)
        return _safe_case_response(case,identity)
    except Exception as e:fail(e)

@app.get('/cases/{case_id}/review-packet')
def review_packet(case_id:str,_=Depends(reviewer_only)):
    try:return build_review_packet(case_id)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/process')
async def process(case_id:str, identity:DemoIdentity=Depends(reviewer_only)):
    """Process/re-evaluate a case.

    REVIEWER ONLY — process_case() can invoke AI agents, update case
    state, generate clarification requests, and record simulated
    remedies.  Rider/Driver must use GET /cases/{case_id} for a
    read-only status check.
    """
    try:
        result=await process_case(case_id)
        return result
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/clarifications/{request_id}/reply')
def reply(case_id:str,request_id:str,item:ClarificationReply, identity:DemoIdentity=Depends(any_actor)):
    try:
        case=_get_authorized_case(case_id,identity)
        result=reply_to_clarification(case_id,request_id,item.answer,identity.role,identity.identity_id)
        return _safe_case_response(result,identity)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/evidence')
def evidence(case_id:str,item:EvidenceUpload,_=Depends(reviewer_only)):
    try:return add_verified_demo_evidence(case_id,item.field,item.value,item.provenance,item.evidence_timestamp)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/files')
async def upload(case_id:str,file:UploadFile=File(...),identity:DemoIdentity=Depends(reviewer_only)):
    try:
        get_case(case_id)
        data=await file.read(5*1024*1024+1)
        stored=store_blob(case_id,file.filename or 'document',file.content_type or '',data)
        analysis=await describe_damage_image(data,file.content_type or '',case_id)
        add_file_evidence(case_id,stored,analysis)
        return {'file':stored,'image_analysis':analysis}
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/review')
def decide(case_id:str,body:ReviewerDecision,_=Depends(reviewer_only)):
    try:return human_review(case_id,body.model_dump())
    except Exception as e:fail(e)

@app.get('/cases/{case_id}/verify-audit')
def verify_audit(case_id:str, identity:DemoIdentity=Depends(any_actor)):
    try:
        case=_get_authorized_case(case_id,identity)
        return {'valid':verify_event_chain(case)}
    except Exception as e:fail(e)

@app.get('/learning')
def learning(_=Depends(reviewer_only)):
    return {'proposals':repo().list_proposals(),'released_precedents':repo().list_precedents()}

@app.post('/learning/{proposal_id}/evaluate')
def test_learning(proposal_id:str,_=Depends(reviewer_only)):
    try:return evaluate_learning(proposal_id)
    except Exception as e:fail(e)

@app.post('/learning/{proposal_id}/approve')
def approve(proposal_id:str,body:LearningApproval,_=Depends(reviewer_only)):
    try:return approve_learning(proposal_id,body.rationale)
    except Exception as e:fail(e)

@app.get('/evaluation/reference')
def evaluate(_=Depends(reviewer_only)):
    return evaluate_suite(approved=True)

@app.post('/learning/{proposal_id}/rollback')
def rollback(proposal_id:str,body:LearningApproval,_=Depends(reviewer_only)):
    try:return rollback_learning(proposal_id,body.rationale)
    except Exception as e:fail(e)
