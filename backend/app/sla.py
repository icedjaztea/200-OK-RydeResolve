"""Rule-based urgency routing. Targets are NOT assumed Ryde SLAs."""
from .evidence import safety_screen

def route_priority(case):
    if safety_screen(case):
        return {'priority':'P0_SAFETY','queue':'SAFETY_REVIEW','requires_immediate_attention':True,
                'target_minutes':None,'source':'policy_v2.1_5.1'}
    if case.get('dispute_amount') is not None and case['dispute_amount']>50:
        return {'priority':'P1_HIGH_VALUE','queue':'FINANCIAL_REVIEW','requires_immediate_attention':False,
                'target_minutes':None,'source':'policy_v2.1_6.1'}
    if case.get('fraud_flags',0)>0:
        return {'priority':'P1_RISK_REVIEW','queue':'HUMAN_REVIEW','requires_immediate_attention':False,
                'target_minutes':None,'source':'policy_v2.1_6.3'}
    return {'priority':'P2_STANDARD','queue':'STANDARD_DISPUTES','requires_immediate_attention':False,
            'target_minutes':None,'source':'demo_priority_proposal_not_Ryde_SLA'}
