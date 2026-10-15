"""Deterministic independent policy gates and remedy validation.
DO NOT let LLMs, the routing index, or self-reported confidence authorize actions.
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from .policy import signoff_valid
from .evidence import gaps, safety_screen, conflicts


def money(x):
    try:return float(Decimal(str(x)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
    except (InvalidOperation,TypeError):return None

def minutes_between(start,end):
    try:
        a=datetime.fromisoformat(start);b=datetime.fromisoformat(end)
        if a.tzinfo is None or b.tzinfo is None:return None
        return (b-a).total_seconds()/60
    except (TypeError,ValueError):return None

def recommend(case):
    """Produce a policy-grounded *candidate* outcome from evidence facts.
    Incomplete records yield undecided rather than fabricated false.
    """
    category=case['category'];f=case.get('facts',{})
    decision={'disposition':'undetermined','amount':0.0,'currency':'SGD','rule_ids':[], 'reason':'Evidence insufficient'}
    if safety_screen(case):
        decision.update(reason='Safety: no AI ruling permitted by SF-5.2',rule_ids=['SF-5.1','SF-5.2'])
        return decision
    if gaps(case):
        decision['reason']='Missing verified inputs: '+', '.join(gaps(case))
        return decision
    if category=='fare_dispute':
        before=float(f['surge_before']);after=float(f['surge_after'])
        notified=f['rider_notified'];complete=f['notification_log_complete']
        if not complete:
            decision['reason']='Notification-event source incomplete; cannot establish notice status'
        elif after>before and notified is False and f['difference_solely_surge'] is True:
            amount=money(float(f['actual_fare'])-float(f['upfront_quote']))
            if amount is None or amount<0:
                decision['reason']='Invalid fare breakdown'
            else:
                decision.update(disposition='refund',amount=amount,
                    reason='Unnotified surge increase; refund only the verified differential',
                    rule_ids=['FA-3.1','FA-3.2','FA-3.3-B','FA-3.4','FA-3.5'])
        elif after>before and notified is True:
            decision.update(disposition='no_action',amount=0,
                reason='Verified notice of revised fare; requires documented rider continuation',
                rule_ids=['FA-3.2','FA-3.3-A'])
            if f.get('rider_proceeded') is not True:
                decision.update(disposition='undetermined',reason='Cannot verify rider proceeded after notification')
        elif after<=before:
            decision.update(disposition='no_action',amount=0,
                            reason='No unnotified surge increase established',
                            rule_ids=['FA-3.3-C' if after<before else 'FA-3.3-D'])
        else:
            decision['reason']='Fare difference not solely attributed to surge; requires review'
    elif category=='no_show_charge':
        wait=minutes_between(f['scheduled_pickup_at'],f['cancellation_at'])
        if wait is None:
            return decision
        if f['driver_arrived'] is not True:
            decision.update(disposition='refund',amount=5.0,reason='Driver did not arrive; no-show fee voided',rule_ids=['NS-2.4'])
        elif wait<5:
            decision.update(disposition='refund',amount=5.0,reason='Cancelled before five minutes from scheduled pickup',rule_ids=['NS-2.1'])
        elif f['driver_message_count']<1 or f['driver_call_count']<1:
            decision.update(disposition='refund',amount=5.0,reason='Driver did not complete required chat AND call',rule_ids=['NS-2.3-VOID'])
        elif f['rider_absent'] is True:
            decision.update(disposition='no_action',amount=0,reason='Documented driver arrival, five-minute wait, chat and call',rule_ids=['NS-2.1','NS-2.2','NS-2.3'])
        else:
            decision['reason']='Rider presence disputed; insufficient evidence for no-show'
    elif category=='route_deviation':
        deviation=float(f['actual_distance_km'])-float(f['recommended_distance_km'])
        if abs(deviation)>0.001 and deviation>1.0 and f['traffic_justified'] is True and f['rider_notified'] is False:
            decision.update(disposition='refund',amount=money(f['excess_distance_fare']),reason='Traffic detour justified but unannounced: excess distance component only',rule_ids=['RD-1.2','RD-1.3-B','RD-1.4'])
        elif deviation<=1:
            decision.update(disposition='no_action',amount=0,reason='Deviation within 1 km tolerance',rule_ids=['RD-1.3-C'])
        elif f['rider_notified'] is True and f.get('rider_agreed') is True:
            decision.update(disposition='no_action',amount=0,reason='Notified and rider agreed',rule_ids=['RD-1.3-A'])
        elif f['traffic_justified'] is False:
            decision.update(disposition='refund',amount=money(f['excess_distance_fare']),reason='Excess distance fare for unjustified detour',rule_ids=['RD-1.3-D'])
    elif category=='property_damage':
        if f.get('rider_disputes_claim') is True:
            decision['reason']='Disputed damage must be handled by human review (4.4)'
            decision['rule_ids']=['DM-4.4-REVIEW']
        elif f.get('photo_verifiable') is False:
            decision.update(disposition='reject_claim',reason='Photo evidence not verifiable',rule_ids=['DM-4.4-REJECT'])
        elif f.get('damage_kind')=='cleaning' and f.get('photo_verifiable') and f.get('trip_link_verified') and f.get('photo_submitted_within_24h'):
            decision.update(disposition='credit',amount=money(case['dispute_amount']),reason='Cleaning claim supported by verified evidence (synthetic)',rule_ids=['DM-4.2','DM-4.3-CLEAN'])
    return decision

def gate(case, candidate, *, approved=None):
    reasons=[]; rules=[]; cat=case['category'];value=case.get('dispute_amount');f=case.get('facts',{})
    if approved is None: approved=signoff_valid()
    safety=safety_screen(case)
    if safety:
        return {'can_auto':False,'path':'IMMEDIATE_HUMAN_REVIEW','reasons':['Safety incident: mandatory reviewer only; no AI outcome'], 'blocking_rules':['SF-5.1','SF-5.2']}
    if not approved:reasons.append('Policy-index team contract signoff is missing')
    if case.get('source_trust')!='SIMULATED_VERIFIED_SYSTEM_FIXTURE':
        reasons.append('No trusted synthetic system fixture for source facts; direct user input is allegations only')
    if value is None:reasons.append('Unknown dispute value: human review required')
    elif value>50:reasons.append('Value above SGD 50: mandatory human review');rules.append('TH-6.1-HIGH')
    elif value>=10:reasons.append('SGD 10-50: confidence is not empirically calibrated; mandatory review for prototype');rules.append('TH-6.1-MID')
    if case.get('fraud_flags',0)>=1:
        reasons.append('Historical fraud flag invokes 95% threshold; no calibrated confidence available');rules.append('TH-6.3')
    if gaps(case):reasons.append('Missing required evidence: '+', '.join(gaps(case)))
    if conflicts(case):reasons.append('Contradictory/incomplete evidence requires investigation or review')
    if cat=='route_deviation':
        actual=f.get('actual_distance_km');recommended=f.get('recommended_distance_km')
        if actual is None or recommended is None or float(actual)-float(recommended)>2:
            reasons.append('Route is over 2 km or distance unknown: mandatory reviewer');rules.append('TH-6.2-ROUTE')
        else:
            reasons.append('Route cases require >=80% validated confidence; uncalibrated in prototype');rules.append('TH-6.2-ROUTE')
    if cat=='property_damage':
        if f.get('rider_disputes_claim') is True:
            reasons.append('Rider disputed property damage: mandatory review');rules.append('DM-4.4-REVIEW')
        if f.get('damage_kind')=='repair' or not f.get('photo_verifiable'):
            reasons.append('Repair/unverifiable photo requires reviewer in demo');rules.append('DM-4.2')
    if candidate['disposition']=='undetermined':reasons.append('No fully supported remedy candidate')
    if candidate['disposition'] in ('refund','credit') and (candidate['amount'] is None or candidate['amount']<0):
        reasons.append('Invalid remedy amount')
    if candidate['disposition']=='credit' and cat=='property_damage' and candidate['amount']>50:
        reasons.append('Cleaning exceeds $50 cap')
    return {'can_auto':not reasons,'path':'AUTO_ELIGIBLE' if not reasons else 'HUMAN_REVIEW',
            'reasons':reasons,'blocking_rules':list(dict.fromkeys(rules))}
