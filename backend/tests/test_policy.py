import copy,json
from app.policy import contract_report,select_candidates,full_rules,signoff_valid
from app.policy_engine import gate,recommend,minutes_between
from app.config import ROOT


def case(name):return json.loads((ROOT/'fixtures/cases'/f'{name}.json').read_text())

def test_uploaded_policy_and_index_have_same_41_ids():
    assert contract_report()['valid'] is True
    assert contract_report()['rule_count']==41
    assert contract_report()['index_count']==41
    assert signoff_valid() is True

def test_routing_index_is_not_decision_engine():
    picked=select_candidates('fare_dispute','surge change without notice')
    assert 'FA-3.3-B' in picked['candidate_rule_ids']
    assert 'TH-6.1-LOW' in picked['candidate_rule_ids']
    assert 'SF-5.1' in picked['candidate_rule_ids']
    assert full_rules(['FA-3.3-B'])[0]['source_section']=='3.3'

def test_fare_dispute_003_refund_450():
    item=case('DISP-003')
    decision=recommend(item);g=gate(item,decision)
    assert decision['disposition']=='refund'
    assert decision['amount']==4.50
    assert g['can_auto']

def test_route_over_2km_review_even_small_refund():
    item=case('DISP-001')
    assert recommend(item)['amount']==3.44
    assert gate(item,recommend(item))['path']=='HUMAN_REVIEW'

def test_noshow_fixed_fee_and_call_requirement():
    item=case('DEMO-NOSHOW-VOID')
    assert recommend(item)['disposition']=='refund'
    assert recommend(item)['amount']==5.0
    assert gate(item,recommend(item))['can_auto']

def test_noshow_5_minutes_from_scheduled_not_driver_early_arrival():
    assert minutes_between('2026-09-13T08:45:00+08:00','2026-09-13T08:51:00+08:00')==6

def test_fraud_flag_no_calibrated_confidence_requires_review():
    item=case('DISP-002')
    assert 'TH-6.3' in gate(item,recommend(item))['blocking_rules']

def test_thresholds_exact_10_50_and_above_50():
    item=case('DISP-003');d=recommend(item)
    for value in (10,50,50.01):
        item['dispute_amount']=value
        assert gate(item,d)['path']=='HUMAN_REVIEW'

def test_safety_spoofed_category_always_human():
    item=case('DEMO-SAFETY-IN-FARE')
    assert gate(item,recommend(item))['path']=='IMMEDIATE_HUMAN_REVIEW'

def test_no_silent_truth_for_absent_notification_log():
    item=case('DEMO-FARE-CLARIFY')
    assert recommend(item)['disposition']=='undetermined'

def test_damage_rider_dispute_mandatory_review():
    item=case('DEMO-DAMAGE-DISPUTED')
    assert gate(item,recommend(item))['path']=='HUMAN_REVIEW'
