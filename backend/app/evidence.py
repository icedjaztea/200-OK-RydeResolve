"""Safety pre-screen, high-value gaps and contradictions.
Absence of evidence is NOT evidence of absence: use tri-state None.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, re

SAFETY_TERMS=('unsafe','assault','threat','harass','reckless','dangerous driving',
              'accident','sexual','hit me','hurt me','weapon','drunk driving',
              'felt scared','physical abuse',
              'intimidated','intimidating','stalking','stalked',
              'felt threatened','threatened me')

# Regex patterns for safety phrases that simple substring matching would miss
# or that need context to avoid false positives.
# Patterns are matched case-insensitively against the combined text.
SAFETY_PATTERNS=(
    # Intimidation — "The driver intimidated me", "I was intimidated", "intimidating behavior"
    re.compile(r'\bintimidat\w*\b'),
    # Stalking — "He was stalking me", "the driver stalked me"
    re.compile(r'\bstalk(?:ed|ing)\b'),
    # Following home — "The driver followed me home", "followed me to my home/address"
    # Requires "follow" + a destination/home word to avoid false positives like
    # "I followed the GPS route home" (where "followed" is the rider's action, not the driver's).
    re.compile(r'(?:driver|he|she|they)\s+(?:followed|chased)\s+(?:me|us)\s+(?:home|to\s+(?:my|our)\s+(?:home|house|address|apartment|residence|building))'),
    re.compile(r'\bchased?\s+(?:me|us)\b'),
    # "felt threatened" — distinct from "threat" substring; catches "I felt threatened"
    re.compile(r'\bfelt\s+threatened\b'),
    # "threatened me" — catches "The driver threatened me" even without standalone "threat"
    re.compile(r'\bthreatened?\s+(?:me|us|the\s+rider)\b'),
)

def now():
    return datetime.now(timezone.utc).isoformat()

def hash_snapshot(case):
    canonical=json.dumps({'facts':case.get('facts',{}),'evidence':case.get('evidence',[])},sort_keys=True,default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def safety_screen(case):
    fragments=[case.get('description','')]
    for item in case.get('evidence',[]):
        if item.get('type') in ('chat','claim','transcript'):
            fragments.append(str(item.get('content','')))
    text=' '.join(fragments).lower()
    if case.get('category')=='safety_incident':
        return True
    # Substring match for direct safety terms.
    if any(term in text for term in SAFETY_TERMS):
        return True
    # Regex patterns for phrases requiring context or word boundaries.
    if any(p.search(text) for p in SAFETY_PATTERNS):
        return True
    return False

def gaps(case):
    f=case.get('facts',{}); category=case['category']; result=[]
    must=[]
    if category=='fare_dispute':
        must=['upfront_quote','actual_fare','surge_before','surge_after','rider_notified','notification_log_complete','difference_solely_surge']
    elif category=='route_deviation':
        must=['actual_distance_km','recommended_distance_km','traffic_justified','rider_notified','excess_distance_fare']
    elif category in ('no_show_charge','driver_no_show'):
        must=['scheduled_pickup_at','cancellation_at','driver_arrived','rider_absent','driver_message_count','driver_call_count']
    elif category=='property_damage':
        must=['rider_disputes_claim','damage_kind','photo_verifiable','trip_link_verified','photo_submitted_within_24h']
    for name in must:
        if name not in f or f[name] is None:
            result.append(name)
    if case.get('dispute_amount') is None:
        result.append('dispute_amount')
    if not case.get('dispute_value_basis'):
        result.append('dispute_value_basis')
    return result

def conflicts(case):
    f=case.get('facts',{}); out=[]
    if f.get('driver_claims_notified') is True and f.get('rider_claims_unnotified') is True:
        out.append('Both parties disagree on whether notice was given')
    if f.get('driver_arrived') is True and f.get('rider_claims_driver_absent') is True:
        out.append('Recorded arrival conflicts with rider account; physical pickup zone may differ')
    if f.get('notification_log_complete') is False and f.get('rider_notified') is False:
        out.append('Incomplete notification log cannot prove absence of notification')
    return out

def clarification_for(case):
    missing=gaps(case); contradict=conflicts(case)
    if not missing and not contradict:return None
    if case['category']=='fare_dispute' and any(x in missing for x in ('rider_notified','notification_log_complete')):
        return {'recipient':'rider','question':'Did you receive an in-app notification of the revised surge multiplier and fare before pickup? If possible, attach the notification or screenshot.','needs_verified_system_evidence':['notification_log_complete','rider_notified']}
    if case['category']=='route_deviation' and 'rider_notified' in missing:
        return {'recipient':'driver','question':'Did you inform the rider of the route change before or at the deviation? Please provide a timestamped in-app message or trip-call reference.','needs_verified_system_evidence':['rider_notified']}
    if case['category']=='no_show_charge' and any(x in missing for x in ('driver_message_count','driver_call_count')):
        return {'recipient':'driver','question':'Please identify the in-app message and call you attempted before cancellation, including approximate times.','needs_verified_system_evidence':['driver_message_count','driver_call_count']}
    return {'recipient':case.get('filed_by','rider'),'question':'Please clarify the missing or conflicting trip details and attach any supporting evidence.','needs_verified_system_evidence':missing}

def record_fact(case,field,value,provenance,timestamp=None):
    allowed=set(gaps(case)) | {'rider_notified','notification_log_complete','driver_message_count','driver_call_count','driver_arrived','rider_absent','traffic_justified','excess_distance_fare','difference_solely_surge','photo_verifiable','trip_link_verified','photo_submitted_within_24h','rider_disputes_claim','driver_claims_notified','rider_claims_unnotified'}
    if field not in allowed:
        raise ValueError(f'Field {field!r} is not in approved demo evidence whitelist')
    _validate_evidence_type(field,value)
    case.setdefault('facts',{})[field]=value
    ident=f'EV-{len(case.setdefault("evidence",[]))+1:03d}'
    case['evidence'].append({'id':ident,'type':'structured_fact','field':field,'content':value,
       'source':'reviewer-imported-synthetic-source','provenance':provenance,
       'captured_at':timestamp or now(), 'verification':'demo-asserted-not-production'})
    return ident


# --- Strict field-specific evidence type validation (Step 37) ---
BOOLEAN_FIELDS=frozenset({'rider_notified','notification_log_complete','driver_arrived',
    'rider_absent','traffic_justified','difference_solely_surge','photo_verifiable',
    'trip_link_verified','photo_submitted_within_24h','rider_disputes_claim',
    'driver_claims_notified','rider_claims_unnotified'})

NONNEGATIVE_INT_FIELDS=frozenset({'driver_message_count','driver_call_count'})

NONNEGATIVE_NUMBER_FIELDS=frozenset({'excess_distance_fare'})


def _validate_evidence_type(field,value):
    """Reject wrong-typed values for field-specific evidence (Step 37).

    - Boolean fields accept only True/False (Python bool).
    - Count fields accept only non-negative integers (int, not bool, not float).
    - Amount fields accept only non-negative numbers (int or float, not bool).
    """
    if field in BOOLEAN_FIELDS:
        if not isinstance(value,bool):
            raise ValueError(f'Field {field!r} requires a boolean (True/False), got {type(value).__name__}')
    elif field in NONNEGATIVE_INT_FIELDS:
        # bool is a subclass of int in Python; reject it explicitly
        if isinstance(value,bool) or not isinstance(value,int):
            raise ValueError(f'Field {field!r} requires a non-negative integer, got {type(value).__name__}')
        if value<0:
            raise ValueError(f'Field {field!r} requires a non-negative integer, got {value}')
    elif field in NONNEGATIVE_NUMBER_FIELDS:
        if isinstance(value,bool) or not isinstance(value,(int,float)):
            raise ValueError(f'Field {field!r} requires a non-negative number, got {type(value).__name__}')
        if value<0:
            raise ValueError(f'Field {field!r} requires a non-negative number, got {value}')
