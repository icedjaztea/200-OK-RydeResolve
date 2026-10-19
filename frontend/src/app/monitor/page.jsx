'use client';
import {useState,useEffect,useRef} from 'react';
import Link from 'next/link';
import AppealPanel from '../../lib/AppealPanel';
import {useApi} from '../../lib/useApi';
import {
  STATUS_LABELS,PATH_LABELS,CATEGORY_LABELS,
  DISPOSITION_LABELS,statusLabel,pathLabel,categoryLabel,dispositionLabel,
} from '../../lib/labels';

/* ════════════════════════════════════════════════════════════════════════
   RydeResolve — Workflow Monitor (redesigned)
   ════════════════════════════════════════════════════════════════════════

   • Cases organised into collapsible sections: Resolved / In Review /
     Not Started. Sorted newest-first. Only expanded section shows cards.
   • Clicking a case opens a detail panel that immediately shows the
     current workflow state — no replay needed.
   • Each agent node can be expanded to show a human-readable breakdown
     of what the agent found, recommended, and which policy rules it used.
   ════════════════════════════════════════════════════════════════════════ */

const PIPELINE=[
  {id:'intake',     label:'Intake',          icon:'📥', roleKey:null,                  desc:'Safety screen & case intake'},
  {id:'orch',       label:'Orchestrator',    icon:'🔧', roleKey:'DisputeOrchestrator', desc:'Routes case, looks up trip & facts'},
  {id:'rider_adv',  label:'Rider Advocate',  icon:'🧑', roleKey:'RiderAdvocate',       desc:'Argues the rider\u2019s position'},
  {id:'driver_adv', label:'Driver Advocate', icon:'🚗', roleKey:'DriverAdvocate',      desc:'Argues the driver\u2019s position'},
  {id:'policy',     label:'Policy',          icon:'📋', roleKey:'PolicyPrecedent',     desc:'Matches facts to policy rules'},
  {id:'fraud',      label:'Fraud Check',     icon:'🛡', roleKey:'FraudBadFaith',      desc:'Checks for fraud or bad faith'},
  {id:'judge',      label:'Judge',           icon:'⚖️', roleKey:'Judge',               desc:'Weighs evidence, proposes outcome'},
  {id:'gate',       label:'Policy Gate',     icon:'🚦', roleKey:null,                  desc:'Independent validation checkpoint'},
  {id:'outcome',    label:'Outcome',         icon:'✅', roleKey:null,                  desc:'Final routing — review or remedy'},
];

const SECTIONS=[
  {id:'resolved',   label:'Resolved',        icon:'✅', color:'green'},
  {id:'in_review',  label:'In Review',       icon:'🔄', color:'amber'},
  {id:'not_started',label:'Not Started',     icon:'⏳', color:'grey'},
];

function _classifyCase(c){
  const s=c.status;
  if(s==='RESOLVED'||s==='REVIEWED_AND_RESOLVED') return 'resolved';
  if(s==='NEW') return 'not_started';
  return 'in_review'; // REVIEW_REQUIRED, AWAITING_CLARIFICATION
}

function progressTone(c){
  if(c.status==='RESOLVED'||c.status==='REVIEWED_AND_RESOLVED') return 'resolved';
  if(c.status==='REVIEW_REQUIRED'||c.path==='IMMEDIATE_HUMAN_REVIEW') return 'review';
  if(c.status==='AWAITING_CLARIFICATION') return 'clarification';
  return 'active';
}

function _isFailed(out){
  if(!out) return false;
  return out.parse_failed===true||out.agent_error===true||!!out.failure_kind;
}

// Derive per-step state from a full case detail object
function deriveSteps(detail){
  if(!detail) return {};
  const outputs=detail.agent_outputs||{};
  const gate=detail.gate||{};
  const status=detail.status;
  const path=detail.path;
  const isSafety=path==='IMMEDIATE_HUMAN_REVIEW';
  const isResolved=status==='RESOLVED'||status==='REVIEWED_AND_RESOLVED';
  const hasOutputs=Object.keys(outputs).length>0;

  const s={};

  s.intake=hasOutputs||path?'done':'pending';

  const orch=outputs['DisputeOrchestrator'];
  s.orch=orch?(_isFailed(orch)?'failed':'done'):(hasOutputs?'skipped':'pending');

  for(const nk of ['rider_adv','driver_adv','policy','fraud']){
    const node=PIPELINE.find(n=>n.id===nk);
    const out=outputs[node.roleKey];
    if(!out) s[nk]=hasOutputs?'skipped':'pending';
    else if(_isFailed(out)) s[nk]='failed';
    else s[nk]='done';
  }

  const judge=outputs['Judge'];
  if(isSafety) s.judge='skipped';
  else if(judge) s.judge=_isFailed(judge)?'failed':'done';
  else s.judge=hasOutputs?'failed':'pending';

  s.gate=(gate&&gate.path)?'done':'pending';

  if(isResolved) s.outcome='done';
  else if(status==='REVIEW_REQUIRED'||isSafety||status==='AWAITING_CLARIFICATION') s.outcome='done';
  else s.outcome='pending';

  return s;
}

// ── Human-readable agent output formatter ──────────────────────────────────
function AgentBreakdown({node,output,trace}){
  if(!output){
    return <div className="agent-card agent-card-pending">
      <div className="agent-card-header">
        <span className="agent-icon">{node.icon}</span>
        <div>
          <div className="agent-name">{node.label}</div>
          <div className="agent-desc">{node.desc}</div>
        </div>
        <span className="agent-status agent-status-pending">Not run</span>
      </div>
    </div>;
  }

  const failed=_isFailed(output);
  const isAgent=!!output.agent_name;

  return(
    <div className={'agent-card '+(failed?'agent-card-failed':'agent-card-done')}>
      <div className="agent-card-header">
        <span className="agent-icon">{node.icon}</span>
        <div className="agent-card-title">
          <div className="agent-name">{node.label}</div>
          <div className="agent-desc">{node.desc}</div>
        </div>
        <span className={'agent-status '+(failed?'agent-status-failed':'agent-status-done')}>
          {failed?'Failed':'Completed'}
        </span>
      </div>

      <div className="agent-card-body">
        {/* Summary */}
        {output.summary&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Summary</div>
            <div className="breakdown-value breakdown-summary">{output.summary}</div>
          </div>
        )}

        {/* Failure details */}
        {failed&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Failure details</div>
            <div className="breakdown-value breakdown-error">
              {output.failure_kind&&<div>Failure type: <b>{output.failure_kind}</b></div>}
              {output.validation_error&&<div>Validation: {output.validation_error}</div>}
              {output.error_code&&<div>Error code: {output.error_code}</div>}
            </div>
          </div>
        )}

        {/* Recommendation */}
        {isAgent&&output.recommended_disposition&&output.recommended_disposition!=='undetermined'&&(
          <div className="breakdown-field-row">
            <div className="breakdown-field">
              <div className="breakdown-label">Recommendation</div>
              <div className="breakdown-value">{dispositionLabel(output.recommended_disposition)}</div>
            </div>
            {output.recommended_amount!=null&&output.recommended_amount>0&&(
              <div className="breakdown-field">
                <div className="breakdown-label">Amount</div>
                <div className="breakdown-value">SGD {Number(output.recommended_amount).toFixed(2)}</div>
              </div>
            )}
          </div>
        )}

        {/* Evidence reviewed */}
        {isAgent&&output.supporting_evidence&&output.supporting_evidence.length>0&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Evidence reviewed</div>
            <div className="breakdown-value">
              <div className="ev-tags">
                {output.supporting_evidence.map((e,i)=><span key={i} className="ev-tag ev-supporting">{e}</span>)}
              </div>
            </div>
          </div>
        )}

        {/* Opposing evidence */}
        {isAgent&&output.opposing_evidence&&output.opposing_evidence.length>0&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Opposing evidence</div>
            <div className="breakdown-value">
              <div className="ev-tags">
                {output.opposing_evidence.map((e,i)=><span key={i} className="ev-tag ev-opposing">{e}</span>)}
              </div>
            </div>
          </div>
        )}

        {/* Uncertainties */}
        {isAgent&&output.uncertainties&&output.uncertainties.length>0&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Uncertainties</div>
            <div className="breakdown-value">
              <ul className="breakdown-list">{output.uncertainties.map((u,i)=><li key={i}>{u}</li>)}</ul>
            </div>
          </div>
        )}

        {/* Policy rules */}
        {isAgent&&output.policy_rule_ids&&output.policy_rule_ids.length>0&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Policy rules applied</div>
            <div className="breakdown-value">
              <div className="rule-chips">
                {output.policy_rule_ids.map(r=><span key={r} className="rule-chip">{r}</span>)}
              </div>
            </div>
          </div>
        )}

        {/* Mode */}
        {isAgent&&output.mode&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Mode</div>
            <div className="breakdown-value">
              <span className="mode-badge">{output.mode==='MOCK_NOT_MODEL_OUTPUT'?'Mock (demo)':output.mode}</span>
            </div>
          </div>
        )}

        {/* Trace */}
        {trace&&trace.length>0&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Operations performed</div>
            <div className="breakdown-value">
              <div className="trace-list">
                {trace.map((t,i)=><div key={i} className="trace-item">
                  <span className="trace-op">{t.operation||t.event_author||'—'}</span>
                  {t.mode&&<span className="trace-mode">{t.mode==='MOCK_NOT_MODEL_OUTPUT'?'mock':t.mode}</span>}
                </div>)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Gate breakdown ──────────────────────────────────────────────────────────
function GateBreakdown({gate}){
  if(!gate||!gate.path){
    return <div className="agent-card agent-card-pending">
      <div className="agent-card-header">
        <span className="agent-icon">🚦</span>
        <div className="agent-card-title">
          <div className="agent-name">Policy Gate</div>
          <div className="agent-desc">Independent validation checkpoint</div>
        </div>
        <span className="agent-status agent-status-pending">Not run</span>
      </div>
    </div>;
  }
  return(
    <div className="agent-card agent-card-done">
      <div className="agent-card-header">
        <span className="agent-icon">🚦</span>
        <div className="agent-card-title">
          <div className="agent-name">Policy Gate</div>
          <div className="agent-desc">Independent validation checkpoint</div>
        </div>
        <span className="agent-status agent-status-done">Completed</span>
      </div>
      <div className="agent-card-body">
        <div className="breakdown-field-row">
          <div className="breakdown-field">
            <div className="breakdown-label">Decision</div>
            <div className="breakdown-value">{pathLabel(gate.path)}</div>
          </div>
          <div className="breakdown-field">
            <div className="breakdown-label">Auto-eligible?</div>
            <div className="breakdown-value">{gate.can_auto?'Yes':'No — human review'}</div>
          </div>
        </div>
        {gate.blocking_rules&&gate.blocking_rules.length>0&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Blocking rules</div>
            <div className="breakdown-value">
              <div className="rule-chips">
                {gate.blocking_rules.map(r=><span key={r} className="rule-chip rule-chip-block">{r}</span>)}
              </div>
            </div>
          </div>
        )}
        {gate.reasons&&gate.reasons.length>0&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Reasons</div>
            <div className="breakdown-value">
              <ul className="breakdown-list breakdown-reasons">
                {gate.reasons.map((r,i)=><li key={i}>{r}</li>)}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Outcome breakdown ───────────────────────────────────────────────────────
function OutcomeBreakdown({detail,stepState}){
  const isResolved=detail.status==='RESOLVED'||detail.status==='REVIEWED_AND_RESOLVED';
  const path=detail.path;
  const mockAction=detail.mock_action;
  const candidate=detail.candidate;

  return(
    <div className={'agent-card '+(isResolved?'agent-card-done':'agent-card-review')}>
      <div className="agent-card-header">
        <span className="agent-icon">✅</span>
        <div className="agent-card-title">
          <div className="agent-name">Outcome</div>
          <div className="agent-desc">Final routing — review or remedy</div>
        </div>
        <span className={'agent-status '+(isResolved?'agent-status-done':'agent-status-review')}>
          {isResolved?'Resolved':path==='IMMEDIATE_HUMAN_REVIEW'?'Safety review':'Human review'}
        </span>
      </div>
      <div className="agent-card-body">
        <div className="breakdown-field-row">
          <div className="breakdown-field">
            <div className="breakdown-label">Routing path</div>
            <div className="breakdown-value">{pathLabel(path)}</div>
          </div>
          <div className="breakdown-field">
            <div className="breakdown-label">Case status</div>
            <div className="breakdown-value">{statusLabel(detail.status)}</div>
          </div>
        </div>

        {candidate&&candidate.disposition&&candidate.disposition!=='undetermined'&&(
          <div className="breakdown-field-row">
            <div className="breakdown-field">
              <div className="breakdown-label">AI recommendation</div>
              <div className="breakdown-value">{dispositionLabel(candidate.disposition)}</div>
            </div>
            {candidate.amount>0&&(
              <div className="breakdown-field">
                <div className="breakdown-label">Recommended amount</div>
                <div className="breakdown-value">SGD {Number(candidate.amount).toFixed(2)}</div>
              </div>
            )}
          </div>
        )}

        {candidate&&candidate.reason&&(
          <div className="breakdown-field">
            <div className="breakdown-label">Reasoning</div>
            <div className="breakdown-value breakdown-summary">{candidate.reason}</div>
          </div>
        )}

        {mockAction&&mockAction.disposition&&(
          <div className="breakdown-field-row">
            <div className="breakdown-field">
              <div className="breakdown-label">Recorded action</div>
              <div className="breakdown-value">{dispositionLabel(mockAction.disposition)}</div>
            </div>
            <div className="breakdown-field">
              <div className="breakdown-label">Amount</div>
              <div className="breakdown-value">SGD {Number(mockAction.amount||0).toFixed(2)}</div>
            </div>
          </div>
        )}

        {path==='IMMEDIATE_HUMAN_REVIEW'&&(
          <div className="breakdown-note breakdown-note-safety">
            ⚠️ Safety incident — mandatory human review. No AI outcome, no automated financial action.
          </div>
        )}
        {path==='HUMAN_REVIEW'&&mockAction&&!mockAction.disposition&&(
          <div className="breakdown-note">
            Case routed to human review. The AI proposed a recommendation but a reviewer must approve before any action is taken.
          </div>
        )}
      </div>
    </div>
  );
}


export default function MonitorPage(){
  const api=useApi('reviewer');
  const [cases,setCases]=useState([]);
  const [monitorData,setMonitorData]=useState(null);
  const [connected,setConnected]=useState(false);
  const [detail,setDetail]=useState(null);
  const [stepStates,setStepStates]=useState({});
  const [expandedSection,setExpandedSection]=useState('in_review');
  const [expandedAgents,setExpandedAgents]=useState({});
  const [showAllAgents,setShowAllAgents]=useState(false);
  const refreshRef=useRef(null);

  async function connect(){
    const data=await api.call('monitor');
    setMonitorData(data);
    setCases(data.cases||[]);
    setConnected(true);
  }

  useEffect(()=>{
    api.run(connect);
    refreshRef.current=setInterval(()=>{
      api.run(async()=>{
        try{
          const data=await api.call('monitor');
          setMonitorData(data);
          setCases(data.cases||[]);
          setConnected(true);
        }catch{/* keep cached */}
      });
    },5000);
    return()=>{if(refreshRef.current)clearInterval(refreshRef.current)};
  },[]);

  async function loadCase(id){
    const c=await api.call('cases/'+id);
    setDetail(c);
    setStepStates(deriveSteps(c));
    setExpandedAgents({});
    setShowAllAgents(false);
  }

  function closeDetail(){
    setDetail(null);
    setStepStates({});
    setExpandedAgents({});
  }

  function toggleAgent(nodeId){
    setExpandedAgents(prev=>({...prev,[nodeId]:!prev[nodeId]}));
  }

  // Group cases by section, sort newest-first (by case_id as proxy)
  const grouped={};
  for(const sec of SECTIONS) grouped[sec.id]=[];
  // Sort newest first — use case_id string comparison (DEMO/DISP prefixed)
  const sorted=[...cases].sort((a,b)=>b.case_id.localeCompare(a.case_id));
  for(const c of sorted){
    const sec=_classifyCase(c);
    grouped[sec].push(c);
  }

  // Count done steps for detail view
  const doneCount=detail?Object.values(stepStates).filter(s=>s==='done').length:0;
  const totalCount=PIPELINE.length;

  if(!connected){
    return(
      <main className="monitor-page">
        <div className="monitor-loading">
          {!api.error&&<div className="monitor-spinner"/>}
          <p>{api.error?'Unable to load workflow monitor.':'Loading workflow monitor…'}</p>
          {api.error&&<button disabled={api.busy} onClick={()=>api.run(connect)}>Retry</button>}
          {api.error&&<div className="alert alert-error">{api.error}</div>}
          <Link href="/" className="monitor-back-small">← Back to home</Link>
        </div>
      </main>
    );
  }

  return(
    <main className="monitor-page monitor-page-v2">
      {/* Header */}
      <header className="mon-header">
        <div className="mon-header-left">
          <h1>Workflow Monitor</h1>
          <div className="mon-header-meta">
            <span className="mon-live-dot"/>
            <span>Live · auto-refresh 5s</span>
            <span className="mon-sep">·</span>
            <span>{monitorData?.ai_mode==='adk'?'Live ADK':'Mock mode'}</span>
            <span className="mon-sep">·</span>
            <span>{cases.length} cases</span>
          </div>
        </div>
        <div className="mon-header-right">
          <Link href="/reviewer" className="mon-link-btn">Reviewer workbench →</Link>
        </div>
      </header>

      {api.error&&<div className="alert alert-error">{api.error}</div>}

      <div className="mon-progress-legend" aria-label="Workflow progress legend">
        <span><i className="mon-tone-resolved"/>Resolved</span>
        <span><i className="mon-tone-review"/>Human review / failed step</span>
        <span><i className="mon-tone-clarification"/>Awaiting clarification</span>
        <span><i className="mon-tone-active"/>In progress</span>
        <span><i className="mon-legend-pending"/>Pending</span>
        <span><i className="mon-legend-skipped"/>Skipped</span>
        <p>Each segment is a workflow step. Filled segments show completed steps; their color reflects the case status. Resolved cases may have skipped or unrun steps.</p>
      </div>

      {/* Case sections */}
      <div className="mon-sections">
        {SECTIONS.map(sec=>{
          const list=grouped[sec.id]||[];
          const isOpen=expandedSection===sec.id;
          return(
            <div key={sec.id} className={'mon-section mon-section-'+sec.color}>
              <button className="mon-section-header" onClick={()=>setExpandedSection(isOpen?null:sec.id)}>
                <div className="mon-section-title">
                  <span className="mon-section-icon">{sec.icon}</span>
                  <span>{sec.label}</span>
                  <span className="mon-section-count">{list.length}</span>
                </div>
                <span className={'mon-chevron '+(isOpen?'mon-chevron-open':'')}>▾</span>
              </button>
              {isOpen&&(
                <div className="mon-section-body">
                  {list.length===0?
                    <div className="mon-section-empty">No cases in this category.</div>
                  :<div className="mon-case-list">
                      {list.map(c=>{
                        const wf=c.workflow||{steps:{},done:0,total:9};
                        const isActive=detail&&detail.case_id===c.case_id;
                        return(
                          <div key={c.case_id}
                            className={'mon-case-row '+(isActive?'mon-case-active':'')}
                            onClick={()=>api.run(()=>loadCase(c.case_id))}
                            role="button" tabIndex={0}
                            onKeyDown={e=>{if(e.key==='Enter'||e.key===' ')api.run(()=>loadCase(c.case_id))}}
                          >
                            <div className="mon-case-id">{c.appeal_of&&<small className="appeal-badge">Appeal</small>}{c.case_id}</div>
                            <div className="mon-case-info">
                              <span className="mon-case-cat">{categoryLabel(c.category)}</span>
                              <span className="mon-case-status">{statusLabel(c.status)}</span>
                            </div>
                            {/* Progress bar */}
                            <div className={'mon-case-progress mon-tone-'+progressTone(c)}>
                              <div className="mon-progress-track" role="progressbar"
                                aria-label={`${c.case_id} workflow progress`}
                                aria-valuemin={0} aria-valuemax={wf.total} aria-valuenow={wf.done}
                                aria-valuetext={`${wf.done} of ${wf.total} steps completed; ${statusLabel(c.status)}`}
                                title={`${wf.done} of ${wf.total} steps completed · ${statusLabel(c.status)}`}>
                                {PIPELINE.map(n=>{
                                  const raw=wf.steps?.[n.id]||'pending';
                                  const st=raw==='completed'?'done':raw;
                                  return <div key={n.id} aria-hidden="true" className={'mon-progress-seg '+st} title={`${n.label}: ${st}`}/>;
                                })}
                              </div>
                              <span className="mon-progress-count">{wf.done}/{wf.total}</span>
                            </div>
                            {c.candidate&&c.candidate.disposition&&c.candidate.disposition!=='undetermined'&&
                              <div className="mon-case-candidate">
                                {dispositionLabel(c.candidate.disposition)}
                                {c.candidate.amount>0&&` · $${Number(c.candidate.amount).toFixed(0)}`}
                              </div>
                            }
                          </div>
                        );
                      })}
                    </div>
                  }
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Case detail panel */}
      {detail&&(
        <div className="mon-detail-overlay" onClick={closeDetail}>
          <div className="mon-detail-panel" onClick={e=>e.stopPropagation()}>
            {/* Detail header */}
            <div className="mon-detail-topbar">
              <div className="mon-detail-topbar-left">
                <h2>{detail.case_id}</h2>
                <span className="mon-detail-badge">{statusLabel(detail.status)}</span>
                <span className="mon-detail-badge mon-detail-badge-path">{pathLabel(detail.path)}</span>
              </div>
              <button className="mon-detail-close" onClick={closeDetail}>✕</button>
            </div>

            {/* Case summary strip */}
            <div className="mon-detail-summary">
              <div className="mon-summary-item">
                <span className="mon-summary-label">Category</span>
                <span className="mon-summary-value">{categoryLabel(detail.category)}</span>
              </div>
              <div className="mon-summary-item">
                <span className="mon-summary-label">Filed by</span>
                <span className="mon-summary-value">{detail.filed_by}</span>
              </div>
              {detail.dispute_amount!=null&&
                <div className="mon-summary-item">
                  <span className="mon-summary-label">Dispute amount</span>
                  <span className="mon-summary-value">SGD {Number(detail.dispute_amount).toFixed(2)}</span>
                </div>
              }
              {detail.processing_ms!=null&&
                <div className="mon-summary-item">
                  <span className="mon-summary-label">Processing time</span>
                  <span className="mon-summary-value">{detail.processing_ms}ms</span>
                </div>
              }
              <div className="mon-summary-item">
                <span className="mon-summary-label">Progress</span>
                <span className="mon-summary-value">{doneCount}/{totalCount} steps</span>
              </div>
            </div>

            {/* Description */}
            <AppealPanel key={detail.case_id} detail={detail} api={api} role="reviewer" onOpen={loadCase}/>
            {detail.description&&
              <div className="mon-detail-desc">{detail.description}</div>
            }

            {/* Workflow stepper */}
            <div className="mon-workflow-section">
              <div className="mon-workflow-title">Agent Workflow</div>
              <div className="mon-stepper">
                {PIPELINE.map((node,idx)=>{
                  const st=stepStates[node.id]||'pending';
                  const hasOutput=st==='done'||st==='failed';
                  const isExpanded=expandedAgents[node.id];
                  const isSkipped=st==='skipped';
                  return(
                    <div key={node.id} className="mon-step-wrap">
                      <div className={'mon-step mon-step-'+st+(hasOutput?' mon-step-clickable':'')+(isExpanded?' mon-step-expanded':'')}
                        onClick={()=>hasOutput&&toggleAgent(node.id)}
                        role={hasOutput?'button':'img'}
                        tabIndex={hasOutput?0:-1}
                        onKeyDown={e=>{if(hasOutput&&(e.key==='Enter'||e.key===' ')){e.preventDefault();toggleAgent(node.id)}}}
                      >
                        <div className="mon-step-circle">
                          {st==='done'?'✓':st==='failed'?'✗':st==='skipped'?'—':node.icon}
                        </div>
                        <div className="mon-step-info">
                          <div className="mon-step-name">{node.label}</div>
                          <div className="mon-step-state">
                            {st==='done'?'Completed':st==='failed'?'Failed':st==='skipped'?'Skipped':'Pending'}
                          </div>
                        </div>
                        {hasOutput&&!isExpanded&&<span className="mon-step-expand">▼ details</span>}
                        {hasOutput&&isExpanded&&<span className="mon-step-expand">▲ hide</span>}
                      </div>

                      {/* Connector */}
                      {idx<PIPELINE.length-1&&(
                        <div className={'mon-step-connector mon-step-connector-'+st}/>
                      )}

                      {/* Expanded breakdown */}
                      {isExpanded&&(
                        <div className="mon-step-breakdown">
                          {node.id==='gate'?(
                            <GateBreakdown gate={detail.gate}/>
                          ):node.id==='outcome'?(
                            <OutcomeBreakdown detail={detail} stepState={st}/>
                          ):(
                            <AgentBreakdown
                              node={node}
                              output={detail.agent_outputs?.[node.roleKey]}
                              trace={(detail.agent_trace||[]).filter(t=>t.agent===node.roleKey)}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Facts */}
            {detail.facts&&Object.keys(detail.facts).length>0&&(
              <div className="mon-facts-section">
                <div className="mon-facts-title">Case Facts</div>
                <div className="mon-facts-grid">
                  {Object.entries(detail.facts).map(([k,v])=>(
                    <div key={k} className="mon-fact-item">
                      <span className="mon-fact-key">{k.replace(/_/g,' ')}</span>
                      <span className="mon-fact-val">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Gaps & contradictions */}
            {(detail.gaps&&detail.gaps.length>0)||(detail.contradictions&&detail.contradictions.length>0)?(
              <div className="mon-issues-section">
                {detail.gaps&&detail.gaps.length>0&&(
                  <div className="mon-issues-block">
                    <div className="mon-issues-title">Information Gaps</div>
                    <ul className="mon-issues-list">
                      {detail.gaps.map((g,i)=><li key={i}>{g}</li>)}
                    </ul>
                  </div>
                )}
                {detail.contradictions&&detail.contradictions.length>0&&(
                  <div className="mon-issues-block mon-issues-contradictions">
                    <div className="mon-issues-title">Contradictions</div>
                    <ul className="mon-issues-list">
                      {detail.contradictions.map((c,i)=><li key={i}>{c}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ):null}
          </div>
        </div>
      )}

      <div className="mon-footer">
        <Link href="/">← Back to home</Link>
        <span>States derived from actual stored agent data · Auto-refreshing every 5s</span>
      </div>
    </main>
  );
}
