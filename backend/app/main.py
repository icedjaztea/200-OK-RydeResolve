"""FastAPI demo service. Only synthetic cases; role-specific demo keys, no production auth."""
from __future__ import annotations
import asyncio, hashlib, hmac, os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .config import setting
from .models import CaseCreate, AppealCreate, ClarificationReply, ClarificationRequest, EvidenceUpload, ReviewerDecision, LearningApproval, ReclassifyRequest
from .repository import repo
from .identity import DemoIdentity, authenticate, is_reviewer, is_party, seed_case_owners
from .safe_response import safe_case_for_rider, safe_case_for_driver, safe_case_list_item
from .services import (create_case,seed_cases,get_case,process_case,reply_to_clarification,request_more_info,
                       add_verified_demo_evidence,human_review,evaluate_suite,
                       evaluate_learning,approve_learning,rollback_learning,verify_event_chain,add_file_evidence,
                       build_review_packet,reclassify_case,create_appeal)
from .policy import contract_report, signoff_valid, load_policy, full_rules
from .storage import store_blob, get_blob
from .image_analysis import describe_damage_image
from .evidence import now

IMAGE_ANALYSIS_TIMEOUT_SECONDS = 235

@asynccontextmanager
async def lifespan(app:FastAPI):
    # Complete durable, create-only seeding before accepting portal requests.
    seed_cases()
    yield


app=FastAPI(title='RydeResolve - SYNTHETIC demo',version='0.3.0',lifespan=lifespan)
origins=[s.strip() for s in setting('ALLOWED_ORIGINS','http://localhost:3000').split(',') if s.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,
    allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Demo-Key'])


def demo_auth(x_demo_key:str|None=Header(default=None)) -> DemoIdentity:
    """Open access — any caller is accepted. Role is inferred from the key."""
    return authenticate(x_demo_key)


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
    case={**case,'appeals':[{'case_id':c['case_id'],'status':c['status'],'filed_by':c['filed_by']}
        for c in repo().list_cases() if c.get('appeal_of')==case['case_id']]}
    if is_reviewer(identity):
        if case.get('appeals') and case.get('learning',{}).get('status')=='PUBLISHED':
            case['learning']={'status':'EXCLUDED_AFTER_APPEAL','message':'This decision has a linked appeal. Its example is excluded from future guidance; review the latest appeal instead.'}
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

@app.get('/policy/rules')
def policy_rules(ids:str='',_=Depends(reviewer_only)):
    """Return full policy rule snippets for the given rule IDs.

    Query param `ids` is a comma-separated list of rule IDs.
    Returns each rule's condition, effect, evidence requirements, and source section.
    """
    rule_ids=[r.strip() for r in ids.split(',') if r.strip()] if ids else []
    return {'rules':full_rules(rule_ids)}

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
    counterparty=new.pop('counterparty_id')
    # The caller owns their side; only an explicit opposite-role demo identity
    # can be linked. Custom/legacy trips remain unassigned on the other side.
    if is_party(identity):
        other_role='driver' if identity.role=='rider' else 'rider'
        if counterparty is not None and counterparty not in (f'{other_role}_a',f'{other_role}_b'):
            raise HTTPException(400,'Counterparty must be an opposite-role demo identity')
        new['filed_by']=identity.role
        new[f'{identity.role}_id']=identity.identity_id
        new[f'{other_role}_id']=counterparty
    elif counterparty is not None:
        raise HTTPException(400,'Create linked reports from the rider or driver portal')
    try:return _safe_case_response(create_case(new),identity)
    except Exception as e:fail(e)

@app.get('/cases/{case_id}')
def case_detail(case_id:str, identity:DemoIdentity=Depends(any_actor)):
    try:
        case=_get_authorized_case(case_id,identity)
        return _safe_case_response(case,identity)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/appeals')
def appeal(case_id:str, body:AppealCreate, identity:DemoIdentity=Depends(any_actor)):
    try:
        _get_authorized_case(case_id,identity)
        return _safe_case_response(create_appeal(case_id,identity.role,identity.identity_id,body.reason),identity)
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

@app.post('/cases/{case_id}/clarifications')
def create_clarification(case_id:str,body:ClarificationRequest,_=Depends(reviewer_only)):
    """REVIEWER ONLY — Create an ad-hoc clarification request.

    Works on any non-resolved case (NEW, REVIEW_REQUIRED, AWAITING_CLARIFICATION).
    Does NOT auto-adjudicate or execute financial actions.
    The party's reply is always UNVERIFIED — never promoted to system evidence.
    """
    try:return request_more_info(case_id,body.recipient,body.question)
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
async def upload(case_id:str,file:UploadFile=File(...),identity:DemoIdentity=Depends(any_actor)):
    try:
        case=_get_authorized_case(case_id,identity)
        if case['status'] in ('RESOLVED','REVIEWED_AND_RESOLVED'):
            raise ValueError('This case is resolved. Submit an appeal to add new evidence.')
        data=await file.read(5*1024*1024+1)
        # A completed upload retry must not invoke Gemini or duplicate evidence.
        digest=hashlib.sha256(data).hexdigest()
        existing=next((e for e in case.get('evidence',[]) if e.get('content',{}).get('sha256')==digest),None)
        if existing:
            return {'file':existing['content'],'image_analysis':existing.get('analysis',{})}
        stored=store_blob(case_id,file.filename or 'document',file.content_type or '',data)
        try:
            analysis=await asyncio.wait_for(
                describe_damage_image(data,file.content_type or '',case_id),
                timeout=IMAGE_ANALYSIS_TIMEOUT_SECONDS)
        except Exception as exc:
            # Do not claim the attachment was analysed or add incomplete evidence.
            # A retry is safe: file evidence is deduplicated by its content hash.
            raise HTTPException(status_code=503,detail=(
                'Image analysis is temporarily unavailable. Your case is saved, '
                'but this attachment has not been added. Please retry the attachment.')) from exc
        add_file_evidence(case_id,stored,analysis)
        return {'file':stored,'image_analysis':analysis}
    except Exception as e:fail(e)

@app.get('/cases/{case_id}/files/{ref}')
def download(case_id:str,ref:str,identity:DemoIdentity=Depends(any_actor)):
    """Download/view a file attachment by its object_ref path segment."""
    from fastapi import Response
    try:
        case=_get_authorized_case(case_id,identity)
        # Find the evidence item with matching object_ref
        for ev in case.get('evidence',[]):
            content=ev.get('content',{}) or {}
            obj_ref=content.get('object_ref','')
            if ref in obj_ref:
                data,ct=get_blob(obj_ref)
                return Response(content=data,media_type=ct,
                    headers={'Content-Disposition':f'inline; filename="{ev.get("id","file")}"',
                             'Cache-Control':'no-store'})
        raise KeyError(ref)
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/review')
def decide(case_id:str,body:ReviewerDecision,_=Depends(reviewer_only)):
    try:return human_review(case_id,body.model_dump())
    except Exception as e:fail(e)

@app.post('/cases/{case_id}/reclassify')
def reclassify(case_id:str,body:ReclassifyRequest,_=Depends(reviewer_only)):
    """Reclassify an 'other' case to a specific dispute category.

    Only reviewer identity can reclassify. The original reported category
    is preserved for audit. After reclassification the case returns to NEW
    status and can be processed under the new category's policy rules.
    """
    try:return reclassify_case(case_id,body.category,body.reason)
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


# ---------------------------------------------------------------------------
# /monitor — aggregated workflow progress for all cases
# ---------------------------------------------------------------------------

def _workflow_steps(case:dict)->dict:
    """Derive per-step completion state from a case document."""
    outputs=case.get('agent_outputs') or {}
    gate=case.get('gate') or {}
    candidate=case.get('candidate') or {}
    status=case.get('status','NEW')
    path=case.get('path')
    is_safety=path=='IMMEDIATE_HUMAN_REVIEW'
    is_resolved=status in ('RESOLVED','REVIEWED_AND_RESOLVED')
    has_outputs=len(outputs)>0
    has_trace=bool(case.get('agent_trace'))

    def _agent_state(out):
        if not out: return 'pending'
        if out.get('parse_failed') or out.get('agent_error') or out.get('failure_kind'): return 'failed'
        return 'completed'

    steps={
        'intake':     'completed' if (has_outputs or path) else 'pending',
        'orch':       'completed' if 'DisputeOrchestrator' in outputs else ('skipped' if has_outputs else 'pending'),
        'rider_adv':  _agent_state(outputs.get('RiderAdvocate')) if 'RiderAdvocate' in outputs else ('skipped' if has_outputs and not is_safety else 'pending'),
        'driver_adv': _agent_state(outputs.get('DriverAdvocate')) if 'DriverAdvocate' in outputs else ('skipped' if has_outputs and not is_safety else 'pending'),
        'policy':     _agent_state(outputs.get('PolicyPrecedent')) if 'PolicyPrecedent' in outputs else ('skipped' if has_outputs and not is_safety else 'pending'),
        'fraud':      _agent_state(outputs.get('FraudBadFaith')) if 'FraudBadFaith' in outputs else ('skipped' if has_outputs and not is_safety else 'pending'),
        'judge':      'skipped' if is_safety else (_agent_state(outputs.get('Judge')) if 'Judge' in outputs else ('pending' if has_outputs else 'pending')),
        'gate':       'completed' if gate and gate.get('path') else 'pending',
        'outcome':    'completed' if (is_resolved or status=='REVIEW_REQUIRED' or is_safety or status=='AWAITING_CLARIFICATION') else 'pending',
    }
    # Count completed steps
    done=sum(1 for v in steps.values() if v=='completed')
    total=len(steps)
    return {'steps':steps,'done':done,'total':total,
            'is_done':is_resolved or status=='REVIEW_REQUIRED',
            'has_outputs':has_outputs,'has_trace':has_trace}


@app.get('/monitor')
def monitor(_=Depends(reviewer_only)):
    """Return all cases with their workflow progress for the monitor dashboard."""
    all_cases=repo().list_cases()
    rows=[]
    for c in all_cases:
        wf=_workflow_steps(c)
        rows.append({
            'case_id':c.get('case_id'),
            'category':c.get('category'),
            'status':c.get('status','NEW'),
            'path':c.get('path'),
            'filed_by':c.get('filed_by'),
            'dispute_amount':c.get('dispute_amount'),
            'candidate':c.get('candidate'),
            'gate':c.get('gate'),
            'mock_action':c.get('mock_action'),
            'processing_ms':c.get('processing_ms'),
            'appeal_of':c.get('appeal_of'),
            'workflow':wf,
        })
    return {'cases':rows,'ai_mode':setting('AI_MODE','mock'),'policy_version':'2.1'}
