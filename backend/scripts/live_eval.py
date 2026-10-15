"""Actual ADK run evaluation. Requires Vertex AI credentials/model quota.
NEVER import gold labels into the agent prompts; used only after process_case returns.
"""
import argparse,asyncio,csv,json,time
from datetime import datetime,timezone
from pathlib import Path
from app.config import ROOT,setting
from app.repository import set_repo,MemoryRepository
from app.services import seed_cases,process_case
from app.agents import judge_consistency,has_agent_failures

def _safe_error(exc)->str:
    """Return a safe, credential-free error category instead of raw str(e)."""
    if isinstance(exc,(KeyError,)):return 'key_error'
    if isinstance(exc,(json.JSONDecodeError,)):return 'json_decode_error'
    if isinstance(exc,(ValueError,)):return 'value_error'
    if isinstance(exc,(TypeError,)):return 'type_error'
    if isinstance(exc,(TimeoutError,asyncio.TimeoutError)):return 'timeout'
    if isinstance(exc,(ConnectionError,)):return 'connection_error'
    if isinstance(exc,(PermissionError,)):return 'permission_error'
    if isinstance(exc,(SystemExit,)):return 'system_exit'
    return exc.__class__.__name__

def _safe_diagnostics(item)->dict:
    """Extract SAFE, credential-free diagnostic fields from a processed case.

    Never includes raw evidence, prompts, full agent responses, credentials,
    or raw exception messages.
    """
    diag={}
    # 1. Deterministic candidate disposition and amount
    cand=item.get('candidate',{})
    diag['det_candidate_disposition']=cand.get('disposition')
    diag['det_candidate_amount']=cand.get('amount')
    # 2. Judge recommended disposition and amount
    outputs=item.get('agent_outputs',{})
    judge=outputs.get('Judge',{})
    diag['judge_disposition']=judge.get('recommended_disposition') if isinstance(judge,dict) else None
    diag['judge_amount']=judge.get('recommended_amount') if isinstance(judge,dict) else None
    # 3. Policy gate path, blocking_rules and reasons
    gate=item.get('gate',{})
    diag['gate_path']=gate.get('path')
    diag['gate_blocking_rules']=gate.get('blocking_rules',[])
    diag['gate_reasons']=gate.get('reasons',[])
    # 4. Agent names with parse_failed or agent_error + per-agent validation details
    failed_agents=[]
    agent_validation_details=[]
    if isinstance(outputs,dict):
        for name,out in outputs.items():
            if isinstance(out,dict) and (out.get('parse_failed') or out.get('agent_error')):
                failed_agents.append(name)
                detail={'agent_name':name,
                        'failure_kind':out.get('failure_kind'),
                        'missing_fields':out.get('missing_fields',[]),
                        'invalid_fields':out.get('invalid_fields',[]),
                        'validation_error_code':out.get('validation_error_code') or out.get('error_code'),
                        'agent_error':out.get('agent_error',False)}
                agent_validation_details.append(detail)
    diag['failed_agent_names']=failed_agents
    diag['agent_validation_details']=agent_validation_details
    # 5. Whether judge_consistency passed
    diag['judge_consistency_passed']=judge_consistency(outputs,cand) if cand else None
    # 6. Names of ADK tools invoked (from trace)
    tool_names=set()
    for evt in item.get('agent_trace',[]):
        for tc in evt.get('tool_calls',[]):
            if isinstance(tc,str):
                tool_names.add(tc)
    diag['adk_tools_invoked']=sorted(tool_names)
    # 7. Sanitized failure codes
    failure_codes=[]
    if isinstance(outputs,dict):
        for name,out in outputs.items():
            if isinstance(out,dict) and out.get('agent_error'):
                failure_codes.append({'agent':name,'error_code':out.get('error_code')})
    diag['sanitized_failure_codes']=failure_codes
    return diag

async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cases',default='DISP-003,DISP-002,DISP-001,DEMO-NOSHOW-VALID,DEMO-NOSHOW-VOID,DEMO-SAFETY-IN-FARE,DEMO-DAMAGE-DISPUTED')
    opts=parser.parse_args()
    if setting('AI_MODE','mock')!='adk':
        raise SystemExit('Set AI_MODE=adk; refusing to mislabel mock outputs as a live ADK evaluation')
    if setting('APP_MODE','memory')!='memory':
        raise SystemExit('Run live evaluation with APP_MODE=memory in a separate ephemeral evaluation process')
    gold=json.loads((ROOT/'fixtures/evaluation/gold.json').read_text())
    set_repo(MemoryRepository());seed_cases()
    results=[]
    for cid in opts.cases.split(','):
        cid=cid.strip();start=time.perf_counter()
        try:
            item=await process_case(cid)
            elapsed=time.perf_counter()-start
            expected=gold[cid]
            path_ok=(item['path']==expected['path'] or (cid=='DEMO-FARE-CONFLICT' and item['path'] in ('CLARIFICATION','HUMAN_REVIEW')))
            rule_ids=set(item.get('routing',{}).get('candidate_rule_ids',[]))
            checked=set(item.get('candidate',{}).get('rule_ids',[]))
            policy_citations_valid=checked.issubset(rule_ids)
            out={'case_id':cid,'path':item.get('path'),'expected_path':expected['path'],
                 'path_correct':path_ok,'policy_citations_valid':policy_citations_valid,
                 'adk_trace_events':len(item.get('agent_trace',[])),
                 'latency_seconds':round(elapsed,3),'ai_mode':'adk','error':None,
                 'diagnostics':_safe_diagnostics(item),
                 'diagnostics_json':json.dumps(_safe_diagnostics(item),default=str)}
        except Exception as e:
            out={'case_id':cid,'path':None,'expected_path':gold[cid]['path'],
                 'path_correct':False,'policy_citations_valid':False,
                 'adk_trace_events':0,'latency_seconds':round(time.perf_counter()-start,3),
                 'ai_mode':'adk','error':_safe_error(e),
                 'diagnostics':None,'diagnostics_json':None}
        print(out);results.append(out)
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'model':setting('GEMINI_MODEL','gemini-2.5-flash'),
            'case_count':len(results),'paths_correct':sum(x['path_correct'] for x in results),
            'live_execution_verified':all(x['error'] is None for x in results),
            'notes':'Synthetic cases; not Ryde production or calibrated confidence. Inspect supporting-evidence citations manually.',
            'results':results}
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    suffix=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    (reports/f'live-{suffix}.json').write_text(json.dumps(report,indent=2)+'\n')
    with (reports/f'live-{suffix}.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=results[0].keys());writer.writeheader();writer.writerows(results)
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
    print('Raw report saved under backend/reports/')
    return all(x['path_correct'] and x['policy_citations_valid'] and x['error'] is None for x in results)

if __name__=='__main__':
    raise SystemExit(0 if asyncio.run(main()) else 1)
