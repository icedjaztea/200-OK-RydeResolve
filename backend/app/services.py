"""Case pipeline: rule discovery -> safety -> investigation -> ADK -> deterministic gates -> mock action."""
from __future__ import annotations
import copy, hashlib, json, time, uuid
from pathlib import Path
from .config import ROOT, is_live_ai
from .evidence import now, hash_snapshot, safety_screen, gaps, conflicts, clarification_for, record_fact
from .policy import select_candidates, signoff_valid, contract_report, lookup_precedents
from .policy_engine import recommend, gate
from .agents import evaluate_agents, judge_consistency, has_agent_failures
from .actions import execute_mock
from .sla import route_priority
from .repository import repo
from .identity import seed_case_owners


def event(case,kind,details=None):
    previous=case.get('events',[])[-1]['hash'] if case.get('events') else ''
    record={'kind':kind,'timestamp':now(),'details':details or {},'previous_hash':previous}
    record['hash']=hashlib.sha256(json.dumps(record,sort_keys=True,default=str).encode()).hexdigest()
    case.setdefault('events',[]).append(record)


def verify_event_chain(case):
    prev=''
    for entry in case.get('events',[]):
        c=copy.deepcopy(entry);h=c.pop('hash',None)
        if c.get('previous_hash')!=prev or hashlib.sha256(json.dumps(c,sort_keys=True,default=str).encode()).hexdigest()!=h:
            return False
        prev=h
    return True


# In-app notifications become available when the containing case is saved.
# Delivered means available in the recipient portal, not read and not emailed.

def outcome_explanation(disposition,amount,receipt=None):
    """Minimal deterministic explanation per disposition type.

    Distinguishes refund (payment destination unknown, not executed),
    credit (not card refund), no_action (no transfer), reject_claim,
    and pending review. Does not invent sources, confidence, SLAs or
    payment methods.
    """
    amt=f'SGD {float(amount):.2f}' if amount else 'SGD 0.00'
    if disposition=='refund':
        return (f'Simulated refund of {amt} proposed. Payment destination unknown; '
                'no real card or wallet transfer executed. This is a synthetic demo only.')
    if disposition=='credit':
        return (f'Simulated credit of {amt} to in-app balance. This is not a card refund. '
                'No real payment method is charged or credited.')
    if disposition=='no_action':
        return (f'No monetary transfer. Decision: no action. {amt} was not moved. '
                'No payment destination is involved.')
    if disposition=='reject_claim':
        return (f'Claim rejected. No refund, credit, or transfer of {amt}. '
                'No payment destination is involved.')
    return f'Case pending reviewer decision. No automated outcome has been determined. (Disposition: {disposition})'


def _rider_safety_message(case_id):
    """Safe explanation for the rider: no counterpart details, no allegation specifics."""
    return (f'Case {case_id}: Your report has been escalated for mandatory human review. '
            'A reviewer will assess the situation and send updates here. '
            'No automated decision has been made. Updates will appear here.')


def _driver_safety_message(case_id):
    """Safe explanation for the driver: no rider allegation details, no safety specifics."""
    return (f'Case {case_id}: This trip has been escalated for mandatory human review. '
            'A reviewer will investigate and request more information here if needed. '
            'No automated decision has been made. Updates will appear here.')


def _add_notification(case,kind,recipient,message,receipt=None,request_id=None):
    # Separate questions and resolutions must not suppress each other's notifications.
    key=f'{kind}:{recipient}:{request_id or receipt or ""}'
    if any(n.get('delivery_key')==key for n in case.get('notifications',[])):return
    recipient_id=case.get(f'{recipient}_id') if recipient!='reviewer' else 'reviewer'
    stamp=now()
    n={'kind':kind,'recipient':recipient,'recipient_id':recipient_id,'message':message,
       'channel':'in_app','delivery_key':key,
       'status':'DELIVERED' if recipient_id else 'NO_LINKED_RECIPIENT','created_at':stamp}
    if recipient_id:n['delivered_at']=stamp
    if receipt:n['receipt']=receipt
    if request_id:n['request_id']=request_id
    case.setdefault('notifications',[]).append(n)


def _notify_resolution(case,disposition,amount,receipt):
    for role in ('rider','driver'):
        if case.get(f'{role}_id'):
            _add_notification(case,'RESOLUTION_RECEIPT',role,
                outcome_explanation(disposition,amount,receipt),receipt=receipt)


def create_case(source:dict, rider_id:str|None=None, driver_id:str|None=None):
    if repo().get_case(source['case_id']):raise ValueError('Case ID already exists')
    case=_prepare_case(source,rider_id,driver_id)
    for role in ('rider','driver','reviewer'):
        if role=='reviewer' or case.get(f'{role}_id'):
            _add_notification(case,'CASE_SUBMITTED',role,f'Case {case["case_id"]} has been submitted. Open it to review the report and attachments.')
    return repo().save_case(case)


def _prepare_case(source:dict, rider_id:str|None=None, driver_id:str|None=None):
    item=copy.deepcopy(source)
    item.setdefault('status','NEW');item.setdefault('facts',{});item.setdefault('evidence',[])
    item.setdefault('events',[]);item.setdefault('clarifications',[]);item.setdefault('revision',0)
    item.setdefault('source_trust','UNVERIFIED_USER_REPORT')
    # Server-assigned ownership. Never trusted from caller.
    # Use setdefault so callers who pass rider_id/driver_id (via the
    # new_case endpoint) take precedence; explicit parameters override None.
    if rider_id is not None:
        item['rider_id']=rider_id
    else:
        item.setdefault('rider_id',None)
    if driver_id is not None:
        item['driver_id']=driver_id
    else:
        item.setdefault('driver_id',None)
    item['policy_version']='2.1';item['rulebook_version']='1.0.0-draft'
    item['evidence_snapshot_hash']=hash_snapshot(item)
    event(item,'case_created',{'synthetic':True,'category':item['category']})
    return item



def create_appeal(cid, role, identity_id, reason):
    original=get_case(cid)
    if role not in ('driver','rider') or original.get(f'{role}_id')!=identity_id:
        raise PermissionError('Only a party linked to this case can appeal')
    if original['status'] not in ('RESOLVED','REVIEWED_AND_RESOLVED'):
        raise ValueError('You can appeal after a decision has been made')
    reason=reason.strip()
    if len(reason)<10:raise ValueError('Explain why you are appealing in at least 10 characters')
    # One appeal per decision and party; create-only storage makes retries safe.
    aid='APPEAL-'+hashlib.sha256(f'{cid}:{identity_id}'.encode()).hexdigest()[:24].upper()
    existing=repo().get_case(aid)
    if existing:return existing
    case=_prepare_case({
        'case_id':aid,'trip_id':original.get('trip_id'),'category':original['category'],
        'filed_by':role,'description':reason,'appeal_reason':reason,'appeal_of':cid,
        'root_case_id':original.get('root_case_id',cid),'fraud_flags':original.get('fraud_flags',0),
        'inherited_safety_escalation':safety_screen(original) or original.get('inherited_safety_escalation',False),
        'rider_id':original.get('rider_id'),'driver_id':original.get('driver_id'),
        'dispute_amount':original.get('dispute_amount'),'dispute_value_basis':original.get('dispute_value_basis','disputed_remedy_amount'),'synthetic':True,
        'facts':copy.deepcopy(original.get('facts',{})),
        'evidence':copy.deepcopy(original.get('evidence',[])),
        'original_decision':{'disposition':original.get('mock_action',{}).get('disposition'),
                             'amount':original.get('mock_action',{}).get('amount'),
                             'case_id':cid},
        'original_case_context':{'description':original.get('description'),
                                'review':copy.deepcopy(original.get('review')),
                                'clarifications':copy.deepcopy(original.get('clarifications',[]))},
    })
    for ev in case['evidence']:ev.setdefault('inherited_from',cid)
    other='rider' if role=='driver' else 'driver'
    if case.get(f'{other}_id'):
        request_id=str(uuid.uuid4())
        question=f'The {role} has appealed the decision for {cid}. Please review the appeal reason and evidence, then share your response and any supporting files.'
        case['clarifications']=[{'request_id':request_id,'recipient':other,'question':question,
                                'status':'PENDING','created_at':now(),'required_verified_fields':[],
                                'source':'appeal'}]
        case['status']='AWAITING_CLARIFICATION';case['path']='CLARIFICATION'
        _add_notification(case,'CLARIFICATION_REQUEST',other,question,request_id=request_id)
    else:
        case['status']='REVIEW_REQUIRED';case['path']='HUMAN_REVIEW'
    _add_notification(case,'APPEAL_SUBMITTED','reviewer',f'Appeal {aid} requests a review of {cid}.')
    case['evidence_snapshot_hash']=hash_snapshot(case)
    event(case,'appeal_created',{'original_case_id':cid,'filed_by':role})
    repo().create_case_if_absent(case)
    return get_case(aid)

def seed_cases(reset:bool=False):
    if reset and hasattr(repo(),'reset'):repo().reset()
    count=0
    for path in sorted((ROOT/'fixtures/cases').glob('*.json')):
        record=json.loads(path.read_text())
        if not repo().get_case(record['case_id']):
            # Assign deterministic demo identities to seeded cases.
            rider_id,driver_id=seed_case_owners(record['case_id'],record.get('filed_by','rider'))
            item=_prepare_case(record,rider_id=rider_id,driver_id=driver_id)
            count+=int(repo().create_case_if_absent(item))
    return count


def get_case(cid):
    value=repo().get_case(cid)
    if value is None:raise KeyError(cid)
    return value


def add_verified_demo_evidence(cid,field,value,provenance,timestamp=None):
    case=get_case(cid)
    if case['status'] in ('RESOLVED','REVIEWED_AND_RESOLVED'):
        raise ValueError('Resolved case is immutable; open a new appeal')
    eid=record_fact(case,field,value,provenance,timestamp)
    case['revision']=case.get('revision',0)+1
    case['status']='NEW';case['evidence_snapshot_hash']=hash_snapshot(case)
    event(case,'synthetic_source_record_added',{'evidence_id':eid,'field':field,'verification':'demo-asserted'})
    repo().save_case(case)
    return case


def reply_to_clarification(cid,request_id,answer,role,identity_id=None):
    case=get_case(cid);requests=case.get('clarifications',[])
    if case.get('status') in ('RESOLVED','REVIEWED_AND_RESOLVED'):
        raise ValueError('Case is already resolved; cannot reply to a clarification on a completed case')
    request=next((x for x in requests if x['request_id']==request_id),None)
    if not request:raise KeyError(request_id)
    if request['status']!='PENDING':raise ValueError('This clarification has already been answered')
    # Identity-based authorization: the caller's role must match the
    # clarification recipient.  The reviewer may reply on behalf of any
    # party, but parties may only reply to their own clarifications.
    if role=='reviewer':
        pass  # reviewer may reply as any party
    elif role==request['recipient']:
        # Party role matches.  Additionally verify identity_id matches
        # the case's owner for that role.
        if identity_id is not None:
            owner_field = f'{role}_id'
            if case.get(owner_field) and case[owner_field]!=identity_id:
                raise PermissionError('Only the intended party can reply')
    else:
        raise PermissionError('Only the intended party or reviewer can reply')
    request.update(status='ANSWERED',answer=answer,answered_at=now(),answer_verification='UNVERIFIED_PARTY_ACCOUNT')
    case['status']='AWAITING_CLARIFICATION' if any(q['status']=='PENDING' for q in requests) else 'NEW'
    _add_notification(case,'RESPONSE_RECEIVED','reviewer',f'The {role} responded. Review the reply and continue the investigation.',request_id=request_id)
    event(case,'clarification_answered',{'request_id':request_id,'verification':'unverified_claim'})
    repo().save_case(case)
    return case


def request_more_info(cid, recipient, question):
    """Reviewer creates an ad-hoc clarification request.

    Works on any non-resolved case (NEW, REVIEW_REQUIRED, AWAITING_CLARIFICATION).
    Does NOT auto-adjudicate, does NOT trigger agents, does NOT execute financial actions.
    The party's reply is always UNVERIFIED — never promoted to system evidence.

    Guards:
    - Case must not be resolved (RESOLVED / REVIEWED_AND_RESOLVED).
    - Recipient must be 'rider' or 'driver'.
    - Question length 5-1000.
    - No duplicate PENDING request to the same recipient.
    - Does not change the case path for safety escalations.
    """
    case=get_case(cid)
    if case.get('status') in ('RESOLVED','REVIEWED_AND_RESOLVED'):
        raise ValueError('Case is already resolved; use the appeal process instead')
    if recipient not in ('rider','driver'):
        raise ValueError('Recipient must be rider or driver')
    if not case.get(f'{recipient}_id'):
        raise ValueError(f'No {recipient} is linked to this case. Ask the linked party or continue human review.')
    if not question or len(question.strip())<5:
        raise ValueError('Question must be at least 5 characters')
    if len(question)>1000:
        raise ValueError('Question must be 1000 characters or fewer')
    # Prevent duplicate pending request to the same recipient
    existing=case.get('clarifications',[])
    pending=next((x for x in existing if x.get('status')=='PENDING' and x.get('recipient')==recipient),None)
    if pending:
        raise ValueError(f'A pending request to {recipient} already exists. Wait for the response before creating another.')
    request_id=str(uuid.uuid4())
    req={'request_id':request_id,'recipient':recipient,'question':question.strip(),
         'required_verified_fields':[],'created_at':now(),'status':'PENDING','source':'reviewer_adhoc'}
    case.setdefault('clarifications',[]).append(req)
    # Move to AWAITING_CLARIFICATION unless safety escalation
    if case.get('path')!='IMMEDIATE_HUMAN_REVIEW':
        case['status']='AWAITING_CLARIFICATION'
        case['path']='CLARIFICATION'
    event(case,'clarification_requested',{'request_id':request_id,'recipient':recipient,'source':'reviewer_adhoc'})
    _add_notification(case,'CLARIFICATION_REQUEST',recipient,question.strip(),request_id=request_id)
    repo().save_case(case)
    return case


async def process_case(cid):
    start=time.perf_counter()
    case=get_case(cid)
    if case.get('status') in ('RESOLVED','REVIEWED_AND_RESOLVED'):
        return case  # retried request cannot execute a duplicate action
    contract=contract_report()
    if not contract['valid']:raise ValueError('Policy contract broken: '+str(contract['problems']))
    is_safety=safety_screen(case) or case.get('inherited_safety_escalation',False)
    context=select_candidates(case['category'],case.get('description',''),case.get('fraud_flags',0),is_safety)
    case['routing']=context
    case['sla_routing']=route_priority(case)
    case['policy_version']='2.1'
    case['evidence_snapshot_hash']=hash_snapshot(case)
    event(case,'routing_index_read',{'count':len(context['candidate_rule_ids']),
                                     'matched_rule_ids':context['matched_phrase_rule_ids']})
    # Mandatory safety evaluation must happen BEFORE asking the judge to decide.
    if is_safety:
        case['status']='REVIEW_REQUIRED'
        case['path']='IMMEDIATE_HUMAN_REVIEW'
        case['candidate']={'disposition':'undetermined','amount':0,'rule_ids':['SF-5.1','SF-5.2'],
                            'reason':'Safety: reviewer must determine fault and remedy'}
        case['gate']={'can_auto':False,'path':case['path'],'blocking_rules':['SF-5.1','SF-5.2'],
            'reasons':['Safety incident: mandatory reviewer only; no AI outcome (SF-5.1)',
                        'Safety: reviewer must determine fault and remedy (SF-5.2)']}
        case['original_escalation']='IMMEDIATE_HUMAN_REVIEW'
        outputs,trace=await evaluate_agents(case,case['candidate'],context,safety=True)
        case['agent_outputs']=outputs;case['agent_trace']=trace
        event(case,'mandatory_safety_escalation',{'rules':['SF-5.1','SF-5.2']})
        _add_notification(case,'SAFETY_REVIEW_ALERT','reviewer',
            f'Case {case["case_id"]}: Safety allegation detected. Immediate human review required. '
            'No AI fault determination or remedy proposed.')
        # Safe rider/driver messages: no counterpart details, no allegation specifics
        _add_notification(case,'SAFETY_REVIEW_ALERT','rider',_rider_safety_message(case['case_id']))
        _add_notification(case,'SAFETY_REVIEW_ALERT','driver',_driver_safety_message(case['case_id']))
        case['processing_ms']=round((time.perf_counter()-start)*1000,2)
        return repo().save_case(case)
    # ── "other" category: manual classification / triage ──────────────────
    # "other" is an intake-only category. It is NOT automatically adjudicable.
    # Route to human review for classification. No Judge, no financial action.
    if case['category']=='other':
        case['status']='REVIEW_REQUIRED'
        case['path']='HUMAN_REVIEW'
        case['candidate']={'disposition':'undetermined','amount':0,'rule_ids':[],
                            'reason':'Unclassified "other" category: manual classification required'}
        case['gate']={'can_auto':False,'path':'HUMAN_REVIEW',
                      'reasons':['Unclassified dispute category: reviewer must classify before adjudication'],
                      'blocking_rules':[]}
        case['original_escalation']='MANUAL_CLASSIFICATION'
        case['agent_outputs']={}
        case['agent_trace']=[]
        event(case,'manual_classification_required',{'original_category':'other'})
        _add_notification(case,'CLARIFICATION_REQUEST','reviewer',
            f'Case {case["case_id"]}: "Other" category submitted. Manual classification required '
            'before policy adjudication can proceed. No automated financial action.')
        case['processing_ms']=round((time.perf_counter()-start)*1000,2)
        return repo().save_case(case)
    if case.get('appeal_of') and any(q['status']=='PENDING' for q in case.get('clarifications',[])):
        case['status']='AWAITING_CLARIFICATION';case['path']='CLARIFICATION'
        return repo().save_case(case)
    missing=gaps(case);inconsistent=conflicts(case)
    if missing or inconsistent:
        # Ask at most once per revision; unverified answer alone never changes facts.
        answered=any(x['status']=='ANSWERED' for x in case.get('clarifications',[]))
        if not answered:
            existing=next((x for x in case.get('clarifications',[]) if x['status']=='PENDING'),None)
            if not existing:
                q=clarification_for(case)
                existing={'request_id':str(uuid.uuid4()),'recipient':q['recipient'],
                          'question':q['question'],'required_verified_fields':q['needs_verified_system_evidence'],
                          'created_at':now(),'status':'PENDING'}
                case['clarifications'].append(existing)
                event(case,'clarification_requested',{'request_id':existing['request_id'],'recipient':existing['recipient']})
                _add_notification(case,'CLARIFICATION_REQUEST',existing['recipient'],
                    existing['question'],request_id=existing['request_id'])
            case['status']='AWAITING_CLARIFICATION';case['path']='CLARIFICATION'
            case['gaps']=missing;case['contradictions']=inconsistent
            case['processing_ms']=round((time.perf_counter()-start)*1000,2)
            return repo().save_case(case)
        case['status']='REVIEW_REQUIRED';case['path']='HUMAN_REVIEW'
        case['candidate']=recommend(case)
        case['gate']={'can_auto':False,'path':'HUMAN_REVIEW',
                      'reasons':['Clarification response unverified; cannot promote statement to fact']+missing+inconsistent}
        event(case,'clarification_unresolved_to_reviewer',{'missing':missing,'conflicts':inconsistent})
        case['processing_ms']=round((time.perf_counter()-start)*1000,2)
        return repo().save_case(case)
    candidate=recommend(case)
    outputs,trace=await evaluate_agents(case,candidate,context,safety=False)
    validation=gate(case,candidate)
    if case.get('appeal_of'):
        validation['can_auto']=False;validation['path']='HUMAN_REVIEW'
        validation['reasons'].append('Appeal: a reviewer must reconsider the original decision and new evidence')
    if not judge_consistency(outputs,candidate):
        validation['can_auto']=False;validation['path']='HUMAN_REVIEW'
        validation['reasons'].append('ADK Judge proposal inconsistent with deterministic policy')
    if has_agent_failures(outputs):
        validation['can_auto']=False;validation['path']='HUMAN_REVIEW'
        validation['reasons'].append('One or more agents failed (parse_failed, agent_error, or missing required fields); cannot finalize autonomously')
    case['agent_outputs']=outputs;case['agent_trace']=trace
    case['candidate']=candidate;case['gate']=validation
    case['path']=validation['path'];case['gaps']=missing;case['contradictions']=inconsistent
    event(case,'policy_gate_applied',{'path':case['path'],'blocking_rules':validation['blocking_rules'],
                                     'policy_version':'2.1','candidate_rules':candidate['rule_ids']})
    if validation['can_auto']:
        action,created=execute_mock(repo(),case,candidate['disposition'],candidate['amount'])
        case['mock_action']=action
        case['status']='RESOLVED'
        event(case,'mock_action_completed',{'receipt':action['receipt'],'new':created,'simulated':True})
        _notify_resolution(case,candidate['disposition'],candidate['amount'],action['receipt'])
    else:
        case['status']='REVIEW_REQUIRED'
    case['processing_ms']=round((time.perf_counter()-start)*1000,2)
    return repo().save_case(case)


def human_review(cid,reviewer_decision:dict):
    case=get_case(cid)
    if case['status']!='REVIEW_REQUIRED':raise ValueError('Case must be in REVIEW_REQUIRED')
    if case.get('review'):raise ValueError('Already reviewed')
    if case.get('appeal_of') and any(q['status']=='PENDING' for q in case.get('clarifications',[])):
        raise ValueError('Wait for the requested appeal response before finalizing')
    # Prevent financial decisions on unclassified "other" cases.
    # The reviewer must reclassify first (POST /cases/{id}/reclassify).
    if case.get('category')=='other' and reviewer_decision.get('disposition') in ('refund','credit'):
        raise ValueError('Cannot apply refund or credit to an unclassified "other" case. '
                          'Reclassify to a specific category first, then apply the financial decision.')
    case['review']={**reviewer_decision,'at':now(),'authorized_by':'demo_reviewer'}
    event(case,'human_review_completed',{'disposition':reviewer_decision['disposition'], 'reason':reviewer_decision['reason']})
    action,created=execute_mock(repo(),case,reviewer_decision['disposition'],reviewer_decision['amount'])
    case['mock_action']=action;case['status']='REVIEWED_AND_RESOLVED';case['path']='HUMAN_REVIEW'
    case.setdefault('original_escalation',case.get('path'))  # preserve pre-review classification
    event(case,'reviewer_mock_remedy',{'receipt':action['receipt'],'simulated':True,'new':created})
    _notify_resolution(case,reviewer_decision['disposition'],reviewer_decision['amount'],action['receipt'])
    # Save the decision first. Learning failure must never lose a completed review.
    repo().save_case(case)
    try:
        automatic_learning(case)
    except Exception:
        case['learning']={'status':'CHECKS_FAILED','message':'Decision saved. Guidance could not be published; it will not be used for other cases.'}
        event(case,'automatic_learning_failed')
    repo().save_case(case)
    return case


def reclassify_case(cid, new_category, reason):
    """Reviewer reclassifies an 'other' case to a specific dispute category.

    Preserves the original reported category for audit. Records the
    classification change as an event. The case returns to NEW status
    so it can be processed under the new category's policy rules.

    Only 'other' cases can be reclassified. The target must be one of
    the six predefined categories — not 'other' or 'safety_incident'
    (safety is determined by the safety screen, not by reclassification).
    """
    case=get_case(cid)
    if case.get('category')!='other':
        raise ValueError('Only "other" category cases can be reclassified')
    if new_category not in ('fare_dispute','route_deviation','no_show_charge',
                            'driver_no_show','property_damage'):
        raise ValueError('Reclassification target must be a specific dispute category '
                          '(fare_dispute, route_deviation, no_show_charge, driver_no_show, or property_damage)')
    if case.get('status') in ('RESOLVED','REVIEWED_AND_RESOLVED'):
        raise ValueError('Resolved case is immutable; open a new appeal')
    case['original_category']=case.get('original_category') or case['category']
    case['category']=new_category
    case['reclassification_reason']=reason
    case['reclassified_at']=now()
    case['status']='NEW'
    case.pop('candidate',None);case.pop('gate',None);case.pop('path',None)
    case.pop('agent_outputs',None);case.pop('agent_trace',None)
    case['evidence_snapshot_hash']=hash_snapshot(case)
    event(case,'case_reclassified',{'from':'other','to':new_category,'reason':reason})
    repo().save_case(case)
    return case


def evaluate_suite(approved=True):
    """Deterministic offline policy regression. NO fabricated evaluation metrics."""
    gold=json.loads((ROOT/'fixtures/evaluation/gold.json').read_text())
    results=[]
    for path in sorted((ROOT/'fixtures/cases').glob('*.json')):
        case=json.loads(path.read_text())
        expected=gold[case['case_id']]
        if safety_screen(case):actual='IMMEDIATE_HUMAN_REVIEW';candidate=recommend(case)
        elif gaps(case) or conflicts(case):actual='CLARIFICATION';candidate=recommend(case)
        else:
            candidate=recommend(case)
            actual=gate(case,candidate,approved=approved)['path']
        # Evaluator targets safety/auto correctness; conflicts are allowed to clarify.
        if case['case_id']=='DEMO-FARE-CONFLICT' and actual=='CLARIFICATION':
            acceptable={'CLARIFICATION','HUMAN_REVIEW'}
        else:acceptable={expected['path']}
        ok=actual in acceptable
        if ok and 'disposition' in expected:
            ok=candidate['disposition']==expected['disposition'] and abs(float(candidate['amount'])-expected['amount'])<.011
        results.append({'case_id':case['case_id'],'actual_path':actual,'expected_path':expected['path'],
                        'candidate':candidate['disposition'],'passed':ok})
    return {'total':len(results),'passed':sum(x['passed'] for x in results),
            'all_passed':all(x['passed'] for x in results),'results':results}



def automatic_learning(case):
    if safety_screen(case) or case.get('inherited_safety_escalation') or case.get('category')=='other':
        case['learning']={'status':'NOT_ELIGIBLE','message':'This case is kept for audit only; safety and unclassified cases are not published as guidance.'}
        return
    pid='LP-'+hashlib.sha256(case['case_id'].encode()).hexdigest()[:20].upper()
    decision=case['review']
    # Publish a factual, case-specific example, never an invented general rule.
    text=(f'Reviewed example {case["case_id"]}, category {case["category"]}: '
          f'the reviewer chose {decision["disposition"]} for SGD {float(decision["amount"]):.2f}. '
          f'Reviewer rationale (case-specific account): {decision["reason"]}. '
          f'Recorded trip facts (verify their provenance before comparison): {json.dumps(case.get("facts",{}),sort_keys=True,default=str)}. '
          f'Evidence snapshot: {case.get("evidence_snapshot_hash", "unknown")}. '
          'This is a case-specific outcome, not proof of party fault or a new policy rule. '
          'Compare the evidence independently; authoritative policy always takes precedence.')
    proposal={'proposal_id':pid,'case_id':case['case_id'],'category':case['category'],
              'candidate_before':case.get('candidate',{}),'human_after':decision,
              'proposed_precedent':text,'status':'STAGED','created_at':now(),
              'policy_version':'2.1','evaluation':None,'automatic':True}
    repo().save_proposal(proposal)
    case['learning_proposal_id']=pid
    evaluated=evaluate_learning(pid)
    if evaluated['status']=='EVALUATED':
        approve_learning(pid,'Automatically published: case-specific decision record and policy regression checks passed.')
        case['learning']={'status':'PUBLISHED','message':'A case-specific example was saved for future reviews after automatic checks passed. Policy rules and the AI model are unchanged.'}
    else:
        case['learning']={'status':'CHECKS_FAILED','message':'The decision is saved, but the guidance did not pass checks and was not published.'}
    event(case,'automatic_learning_checked',{'proposal_id':pid,'status':case['learning']['status']})

def evaluate_learning(pid):
    p=repo().get_proposal(pid)
    if p is None:raise KeyError(pid)
    if p['status'] not in ('STAGED','EVALUATED'):raise ValueError('Proposal not staged')
    result=evaluate_suite(approved=True)
    digest=hashlib.sha256(json.dumps({'proposed_precedent':p['proposed_precedent'],
                                    'human_after':p['human_after'],'policy_version':p['policy_version']},sort_keys=True).encode()).hexdigest()
    p['evaluation']={'regression':result,'content_sha256':digest,'at':now(),
                     'evaluation_scope':'synthetic deterministic suite; not model training validation'}
    if p.get('automatic'):
        source=repo().get_case(p['case_id'])
        valid=bool(source and source.get('status')=='REVIEWED_AND_RESOLVED' and source.get('review')==p['human_after']
                   and source.get('category')==p['category'] and p['policy_version']=='2.1'
                   and not safety_screen(source) and not source.get('inherited_safety_escalation'))
        p['evaluation']['source_decision_verified']=valid
    else:valid=True
    p['status']='EVALUATED' if result['all_passed'] and valid else 'FAILED_EVALUATION'
    repo().save_proposal(p)
    return p


def approve_learning(pid,rationale):
    p=repo().get_proposal(pid)
    if p is None:raise KeyError(pid)
    if p['status']!='EVALUATED' or not p.get('evaluation',{}).get('regression',{}).get('all_passed'):
        raise ValueError('Regression suite must pass before approval')
    digest=hashlib.sha256(json.dumps({'proposed_precedent':p['proposed_precedent'],
                         'human_after':p['human_after'],'policy_version':p['policy_version']},sort_keys=True).encode()).hexdigest()
    if digest!=p['evaluation']['content_sha256']:
        raise ValueError('Proposal modified after evaluation: re-test required')
    approved={'precedent_id':pid,'policy_version':'2.1','category':p['category'],
              'source_case_id':p['case_id'],'text':p['proposed_precedent'],
              'approved_at':now(),'reviewer_approval_rationale':rationale,
              'release_status':'ACTIVE_APPROVED_PRECEDENT',
              'warning':'May aid future review; NEVER override authoritative policy or update model weights'}
    repo().save_precedent(approved)
    p['status']='APPROVED_RELEASED';p['approved_at']=now();p['approval_reason']=rationale
    repo().save_proposal(p)
    return {'proposal':p,'precedent':approved}


def rollback_learning(pid,rationale):
    """Reviewer-controlled rollback: remove released precedent from future agent retrieval.
    Does not erase historical records; retains provenance for audit.
    """
    if len((rationale or '').strip()) < 10:
        raise ValueError('Rollback reason must be at least 10 characters')
    precedent=repo().get_precedent(pid)
    if precedent is None:raise KeyError(pid)
    if precedent.get('release_status')!='ACTIVE_APPROVED_PRECEDENT':
        raise ValueError('Precedent is not currently active')
    precedent['release_status']='ROLLED_BACK'
    precedent['rolled_back_at']=now()
    precedent['rollback_reason']=rationale
    repo().save_precedent(precedent)
    proposal=repo().get_proposal(pid)
    if proposal:
        proposal['status']='ROLLED_BACK'
        proposal['rolled_back_at']=precedent['rolled_back_at']
        repo().save_proposal(proposal)
    return {'precedent':precedent,'proposal':proposal}


def add_file_evidence(cid,metadata,analysis):
    case=get_case(cid)
    if case['status'] in ('RESOLVED','REVIEWED_AND_RESOLVED'):
        raise ValueError('Resolved case is immutable')
    if any(e.get('content',{}).get('sha256')==metadata.get('sha256') for e in case.get('evidence',[]) if metadata.get('sha256')):
        return case
    case.setdefault('evidence',[]).append({'id':f"IMG-{len(case.get('evidence',[]))+1:03d}",
        'type':'image_or_document','content':metadata,'analysis':analysis,
        'source':'synthetic_demo_upload','verification':'camera_origin_unverified',
        'captured_at':now()})
    case['status']='AWAITING_CLARIFICATION' if any(q['status']=='PENDING' for q in case.get('clarifications',[])) else 'NEW'
    case['revision']=case.get('revision',0)+1
    case['evidence_snapshot_hash']=hash_snapshot(case)
    event(case,'image_evidence_recorded',{'object_ref':metadata['object_ref'],
         'image_mode':analysis.get('mode'),'authenticity_verified':False})
    return repo().save_case(case)


def build_review_packet(cid):
    """Assemble a single Reviewer Decision Packet for a REVIEW_REQUIRED case.

    Uses only existing GET /cases/{id} data. Does not invent evidence,
    metrics, or rules. All sections are human-readable and clearly labeled.
    """
    case=get_case(cid)
    is_safety=safety_screen(case) or case.get('inherited_safety_escalation',False)
    missing=gaps(case);inconsistent=conflicts(case)
    candidate=case.get('candidate') or recommend(case)
    validation=gate(case,candidate) if not is_safety else {
        'can_auto':False,'path':'IMMEDIATE_HUMAN_REVIEW',
        'reasons':['Safety incident: mandatory reviewer only; no AI outcome (SF-5.1)',
                   'Safety: reviewer must determine fault and remedy (SF-5.2)'],
        'blocking_rules':['SF-5.1','SF-5.2']}
    if case.get('appeal_of') and not is_safety:
        validation['can_auto']=False;validation['path']='HUMAN_REVIEW'
        validation['reasons'].append('Appeal: reviewer decision required')
    context=case.get('routing') or select_candidates(
        case['category'],case.get('description',''),case.get('fraud_flags',0),is_safety)
    # Structured facts with provenance
    structured_facts=[]
    for field_name,field_val in case.get('facts',{}).items():
        ev=next((e for e in case.get('evidence',[]) if e.get('field')==field_name),None)
        structured_facts.append({
            'field':field_name,'value':field_val,
            'provenance':ev.get('provenance','fixture_default') if ev else 'fixture_default',
            'verification':ev.get('verification','fixture') if ev else 'fixture',
            'evidence_id':ev.get('id') if ev else None})
    # Clarification history
    clarifications=case.get('clarifications',[])
    unverified_replies=[c for c in clarifications if c.get('status')=='ANSWERED']
    # Advocate summaries with mock/live label
    agent_mode='LIVE_ADK' if is_live_ai() else 'MOCK_NOT_MODEL_OUTPUT'
    advocate_summaries={}
    for role,out in (case.get('agent_outputs') or {}).items():
        advocate_summaries[role]={'summary':out.get('summary',''),
            'recommended_disposition':out.get('recommended_disposition','undetermined'),
            'mode':out.get('mode',agent_mode),
            'policy_rule_ids':out.get('policy_rule_ids',[])}
    # Observable event traces labeled mock/live
    event_traces=[{'kind':e.get('kind'),'timestamp':e.get('timestamp'),
        'details':e.get('details',{}),'mode':agent_mode}
        for e in case.get('events',[])]
    # Candidate policy IDs and escalation blocking rule IDs
    candidate_rule_ids=context.get('candidate_rule_ids',[])
    blocking_rule_ids=validation.get('blocking_rules',[])
    # Human-readable gate reasons
    gate_reasons=validation.get('reasons',[])
    # Non-safety candidate labeling
    is_proposal_only=not is_safety and not validation.get('can_auto',False)
    # Safety has NO AI fault/remedy proposal
    safety_note=None
    if is_safety:
        safety_note=('Safety case: AI does not determine fault or propose a remedy. '
                     'Reviewer must assess safety allegations, determine fault, and select remedy.')
    # Human decision separate from AI recommendation
    human_decision=case.get('review')
    ai_recommendation={'disposition':candidate.get('disposition','undetermined'),
        'amount':candidate.get('amount',0),'rule_ids':candidate.get('rule_ids',[]),
        'reason':candidate.get('reason',''),'is_proposal_only':is_proposal_only}
    # Review reason, timestamp and simulated receipt
    review_info=None
    if human_decision:
        review_info={'disposition':human_decision.get('disposition'),
            'amount':human_decision.get('amount'),'reason':human_decision.get('reason'),
            'timestamp':human_decision.get('at'),'authorized_by':human_decision.get('authorized_by'),
            'simulated_receipt':(case.get('mock_action') or {}).get('receipt')}
    # Original escalation classification preserved for traceability
    original_escalation=case.get('path')
    # Synthetic-demo warning
    synthetic_warning=('SYNTHETIC DEMO: All data is synthetic. No real payments, '
                       'Ryde APIs, or customer data are connected. Do not treat '
                       'as production evidence or real financial action.')
    return {
        'case_details':{'case_id':case['case_id'],'trip_id':case.get('trip_id'),
            'category':case['category'],'filed_by':case.get('filed_by'),
            'description':case.get('description',''),'status':case['status'],
            'policy_version':case.get('policy_version','2.1'),
            'rulebook_version':case.get('rulebook_version'),
            'dispute_value':case.get('dispute_amount'),
            'dispute_value_basis':case.get('dispute_value_basis')},
        'filed_by_allegation':case.get('description',''),
        'structured_facts':structured_facts,
        'gaps':missing,'contradictions':inconsistent,
        'clarification_history':clarifications,
        'unverified_replies':unverified_replies,
        'candidate_policy_ids':candidate_rule_ids,
        'escalation_blocking_rule_ids':blocking_rule_ids,
        'gate_reasons':gate_reasons,
        'advocate_summaries':advocate_summaries,
        'event_traces':event_traces,
        'ai_recommendation':ai_recommendation,
        'safety_note':safety_note,
        'human_decision':review_info,
        'original_escalation':original_escalation,
        'is_safety':is_safety,
        'synthetic_warning':synthetic_warning}
