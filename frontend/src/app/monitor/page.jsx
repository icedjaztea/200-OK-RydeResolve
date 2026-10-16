'use client';
import {useState,useEffect,useRef,useCallback} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {
  STATUS_LABELS,PATH_LABELS,CATEGORY_LABELS,
  DISPOSITION_LABELS,statusLabel,pathLabel,categoryLabel,dispositionLabel,
} from '../../lib/labels';

/* ════════════════════════════════════════════════════════════════════════
   RydeResolve — ADK Visual Execution Monitor (Stage 1: Recorded Replay)
   ════════════════════════════════════════════════════════════════════════

   This page visualizes the actual stored agent_trace, agent_outputs,
   candidate, and gate from a processed case. It does NOT execute live
   processing. The backend returns these fields only to Reviewer identity
   (safe_response.py strips them from Rider/Driver).

   No tool calls, durations, or timestamps are invented. Node states are
   derived from the actual stored records.
   ════════════════════════════════════════════════════════════════════════ */

// ── Workflow node definitions ──────────────────────────────────────────────
// The order reflects the actual process_case() flow in services.py:
// 1. Safety screen  2. Orchestrator  3. Four concurrent agents
// 4. Judge (skipped on safety)  5. Policy gate  6. Final routing
const NODES=[
  {id:'intake',    label:'Dispute Intake',        sub:'Safety Screen',  roleKey:null},
  {id:'orch',      label:'Dispute Orchestrator', sub:'Routing & lookup',roleKey:'DisputeOrchestrator'},
  {id:'rider_adv', label:'Rider Advocate',        sub:'Advocacy',       roleKey:'RiderAdvocate'},
  {id:'driver_adv',label:'Driver Advocate',       sub:'Advocacy',       roleKey:'DriverAdvocate'},
  {id:'policy',    label:'Policy & Precedent',    sub:'Rule analysis',  roleKey:'PolicyPrecedent'},
  {id:'fraud',     label:'Fraud & Bad-Faith',     sub:'Risk assessment', roleKey:'FraudBadFaith'},
  {id:'judge',     label:'Judge',                 sub:'Final proposal', roleKey:'Judge'},
  {id:'gate',      label:'Independent Policy Gate',sub:'Validation',    roleKey:null},
  {id:'outcome',   label:'Final Routing',         sub:'Review or remedy',roleKey:null},
];

// ── Node state derivation ───────────────────────────────────────────────────
// Derives node state from actual stored data. Never uses timers.
function deriveNodeStates(detail){
  if(!detail) return {};
  const outputs=detail.agent_outputs||{};
  const trace=detail.agent_trace||[];
  const gate=detail.gate||{};
  const candidate=detail.candidate||{};
  const status=detail.status;
  const path=detail.path;
  const isSafety=path==='IMMEDIATE_HUMAN_REVIEW';
  const isResolved=status==='RESOLVED'||status==='REVIEWED_AND_RESOLVED';
  const hasOutputs=Object.keys(outputs).length>0;

  const states={};

  // 1. Intake / Safety screen — always completed if we have outputs or a path
  states.intake={state:hasOutputs||path?'completed':'pending',skipped:false};

  // 2. Orchestrator — completed if present in outputs
  const orch=outputs['DisputeOrchestrator'];
  states.orch={
    state:orch?(_isFailed(orch)?'failed':'completed'):(hasOutputs?'skipped':'pending'),
    skipped:!orch&&hasOutputs,
    output:orch,
  };

  // 3-6. Concurrent agents
  for(const nk of ['rider_adv','driver_adv','policy','fraud']){
    const node=NODES.find(n=>n.id===nk);
    const out=outputs[node.roleKey];
    if(!out){
      // If we have outputs but this agent is missing, it was skipped
      states[nk]={state:hasOutputs?'skipped':'pending',skipped:hasOutputs,output:null};
    }else if(_isFailed(out)){
      states[nk]={state:'failed',skipped:false,output:out};
    }else{
      states[nk]={state:'completed',skipped:false,output:out};
    }
  }

  // 7. Judge — skipped on safety cases
  const judge=outputs['Judge'];
  if(isSafety){
    states.judge={state:'skipped',skipped:true,output:null};
  }else if(judge){
    states.judge={state:_isFailed(judge)?'failed':'completed',skipped:false,output:judge};
  }else{
    states.judge={state:hasOutputs&&!isSafety?'failed':'pending',skipped:false,output:null};
  }

  // 8. Policy gate — completed if gate has a path
  states.gate={
    state:gate&&gate.path?'completed':'pending',
    skipped:false,
    output:gate,
  };

  // 9. Final routing — completed if resolved or review required
  if(isResolved){
    states.outcome={state:'completed',skipped:false,output:{path,mock_action:detail.mock_action}};
  }else if(status==='REVIEW_REQUIRED'||isSafety){
    states.outcome={state:'completed',skipped:false,output:{path,mock_action:null}};
  }else if(status==='AWAITING_CLARIFICATION'){
    states.outcome={state:'completed',skipped:false,output:{path}};
  }else{
    states.outcome={state:'pending',skipped:false,output:null};
  }

  return states;
}

function _isFailed(out){
  if(!out) return false;
  return out.parse_failed===true||out.agent_error===true||!!out.failure_kind;
}

// ── Trace lookup: map trace entries to agent role ──────────────────────────
function traceForRole(trace,roleKey){
  if(!trace) return [];
  return trace.filter(t=>t.agent===roleKey);
}

// ── Node color classes ─────────────────────────────────────────────────────
const STATE_CLASS={
  pending:'node-pending',
  running:'node-running',
  completed:'node-completed',
  failed:'node-failed',
  skipped:'node-skipped',
};
const STATE_LABEL={
  pending:'Pending',
  running:'Running',
  completed:'Completed',
  failed:'Failed',
  skipped:'Skipped',
};

// ── Replay controller ───────────────────────────────────────────────────────
// Steps through nodes in order, marking each as "running" then "completed"
// using the actual derived final state. No timers create fake progress —
// the replay simply reveals the stored states in sequence.
const REPLAY_STEPS=NODES.map(n=>n.id);

export default function MonitorPage(){
  const api=useApi();
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [selected,setSelected]=useState('');
  const [nodeStates,setNodeStates]=useState({});
  const [activeNode,setActiveNode]=useState(null);
  const [replayStep,setReplayStep]=useState(0); // 0 = not started, REPLAY_STEPS.length = done
  const [playing,setPlaying]=useState(false);
  const [health,setHealth]=useState(null);
  const playRef=useRef(null);

  // ── Connect: verify reviewer auth and load case list ─────────────────────
  async function connect(){
    setHealth(await api.call('health'));
    const list=await api.call('cases');
    setCases(list);
  }

  // ── Load a case for replay ───────────────────────────────────────────────
  async function loadCase(id){
    const c=await api.call('cases/'+id);
    setDetail(c);
    setSelected(id);
    setNodeStates(deriveNodeStates(c));
    setReplayStep(0);
    setPlaying(false);
    setActiveNode(null);
  }

  // ── Replay controls ───────────────────────────────────────────────────────
  // Derive the visible state for a node during replay.
  // Before its step: show pending (or skipped if final state is skipped).
  // At its step: show running briefly, then the actual final state.
  // After its step: show the actual derived state.
  function visibleState(nodeId){
    const actual=nodeStates[nodeId];
    if(!actual) return 'pending';
    if(replayStep===0) return actual.skipped?'skipped':'pending';
    const stepIdx=REPLAY_STEPS.indexOf(nodeId);
    if(stepIdx>=replayStep) return actual.skipped?'skipped':'pending';
    return actual.state;
  }

  function visibleStateLabel(nodeId){
    const actual=nodeStates[nodeId];
    if(!actual) return 'Pending';
    if(replayStep===0) return actual.skipped?'Skipped':'Pending';
    const stepIdx=REPLAY_STEPS.indexOf(nodeId);
    if(stepIdx>=replayStep) return actual.skipped?'Skipped':'Pending';
    return STATE_LABEL[actual.state]||actual.state;
  }

  function stepForward(){
    if(replayStep<REPLAY_STEPS.length){
      setReplayStep(r=>r+1);
    }
  }

  function restart(){
    setReplayStep(0);
    setPlaying(false);
    setActiveNode(null);
    if(playRef.current){clearTimeout(playRef.current);playRef.current=null}
  }

  function togglePlay(){
    if(playing){
      setPlaying(false);
      if(playRef.current){clearTimeout(playRef.current);playRef.current=null}
      return;
    }
    if(replayStep>=REPLAY_STEPS.length) restart();
    setPlaying(true);
  }

  // Auto-advance during play — each step reveals the next node's actual state
  useEffect(()=>{
    if(!playing) return;
    if(replayStep>=REPLAY_STEPS.length){
      setPlaying(false);
      return;
    }
    playRef.current=setTimeout(()=>{
      setReplayStep(r=>r+1);
    },600); // brief delay to show progression — states are from actual data
    return()=>{if(playRef.current){clearTimeout(playRef.current);playRef.current=null}};
  },[playing,replayStep]);

  // ── Node click: show actual output ───────────────────────────────────────
  function onNodeClick(nodeId){
    const actual=nodeStates[nodeId];
    if(!actual||!actual.output) return;
    setActiveNode(nodeId);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  if(!api.key){
    return(
      <main className="monitor-page">
        <div className="monitor-auth-card">
          <h1>ADK Execution Monitor</h1>
          <p className="monitor-subtitle">Recorded run replay — reviewer access required</p>
          <p className="monitor-hint">Technical agent traces are visible only to authorized Reviewer identity.</p>
          <input
            className="passcode-input"
            placeholder="Enter reviewer demo passcode"
            type="password"
            value={api.key}
            onChange={e=>api.setKey(e.target.value)}
            onKeyDown={e=>e.key==='Enter'&&api.run(connect)}
            aria-label="Reviewer demo passcode"
          />
          <button disabled={api.busy} onClick={()=>api.run(connect)}>Connect</button>
          {api.error&&<div className="alert alert-error">{api.error}</div>}
          <div className="monitor-back-link"><Link href="/">← Back to home</Link></div>
        </div>
      </main>
    );
  }

  return(
    <main className="monitor-page">
      <header className="monitor-header">
        <div>
          <h1>ADK Execution Monitor</h1>
          <p className="monitor-subtitle">
            <span className="badge badge-info">Recorded Run Replay</span>
            {' '}· Not live execution
          </p>
        </div>
        <div className="monitor-header-actions">
          <Link href="/reviewer" className="small">← Reviewer workbench</Link>
          <button className="small secondary" disabled={api.busy} onClick={()=>api.run(connect)}>
            Refresh cases
          </button>
        </div>
      </header>

      {api.error&&<div className="alert alert-error">{api.error}</div>}
      {api.notice&&<div className="alert alert-info">{api.notice}</div>}

      {/* Case selector */}
      <section className="monitor-case-bar">
        <label className="sr-only" htmlFor="case-select">Select case</label>
        <select
          id="case-select"
          value={selected}
          onChange={e=>api.run(()=>loadCase(e.target.value))}
          aria-label="Select case to replay"
        >
          <option value="">— Select a case to replay —</option>
          {cases.map(c=>(
            <option key={c.case_id} value={c.case_id}>
              {c.case_id} · {categoryLabel(c.category)} · {statusLabel(c.status)}
            </option>
          ))}
        </select>
        {health&&<span className="monitor-health">Policy v{health.policy_version} · {health.ai_mode?'AI: '+health.ai_mode:'Mock mode'}</span>}
      </section>

      {!detail?(
        <div className="monitor-empty">
          <p>Select a processed case above to view its recorded agent workflow.</p>
          <p className="monitor-hint">Only cases that have been processed will have agent traces.</p>
        </div>
      ):!detail.agent_outputs||Object.keys(detail.agent_outputs).length===0?(
        <div className="monitor-empty">
          <p>This case has not been processed yet, or no agent traces are stored.</p>
          <p className="monitor-hint">Process the case from the Reviewer workbench first.</p>
        </div>
      ):(
        <>
          {/* Case summary */}
          <section className="monitor-case-summary">
            <div className="summary-grid">
              <div><span className="summary-label">Case</span><b>{detail.case_id}</b></div>
              <div><span className="summary-label">Category</span>{categoryLabel(detail.category)}</div>
              <div><span className="summary-label">Status</span>{statusLabel(detail.status)}</div>
              <div><span className="summary-label">Path</span>{pathLabel(detail.path)}</div>
              {detail.candidate&&<>
                <div><span className="summary-label">Candidate</span>{dispositionLabel(detail.candidate.disposition)}</div>
                {detail.candidate.amount!=null&&detail.candidate.amount>0&&
                  <div><span className="summary-label">Amount</span>SGD {Number(detail.candidate.amount).toFixed(2)}</div>
                }
              </>}
              {detail.mock_action&&
                <div><span className="summary-label">Recorded action</span>
                  {dispositionLabel(detail.mock_action.disposition)} · SGD {Number(detail.mock_action.amount||0).toFixed(2)}
                </div>
              }
            </div>
          </section>

          {/* Replay controls */}
          <section className="replay-controls">
            <button
              className="replay-btn"
              onClick={togglePlay}
              disabled={replayStep>=REPLAY_STEPS.length&&!playing}
              aria-label={playing?'Pause replay':'Play replay'}
            >
              {playing?'❚❚ Pause':'▶ Play'}
            </button>
            <button
              className="replay-btn"
              onClick={stepForward}
              disabled={replayStep>=REPLAY_STEPS.length}
              aria-label="Step forward"
            >
              ⏭ Step
            </button>
            <button
              className="replay-btn secondary"
              onClick={restart}
              aria-label="Restart replay"
            >
              ↺ Restart
            </button>
            <span className="replay-progress">
              Step {replayStep} / {REPLAY_STEPS.length}
              {replayStep>=REPLAY_STEPS.length&&' · Replay complete'}
            </span>
          </section>

          {/* Node graph */}
          <section className="monitor-graph" role="region" aria-label="Agent workflow graph">
            {/* Intake → Orchestrator */}
            <div className="graph-column">
              <MonitorNode
                node={NODES[0]}
                state={visibleState('intake')}
                stateLabel={visibleStateLabel('intake')}
                onClick={()=>onNodeClick('intake')}
                active={activeNode==='intake'}
              />
            </div>
            <Connector />

            {/* Orchestrator */}
            <div className="graph-column">
              <MonitorNode
                node={NODES[1]}
                state={visibleState('orch')}
                stateLabel={visibleStateLabel('orch')}
                onClick={()=>onNodeClick('orch')}
                active={activeNode==='orch'}
              />
            </div>
            <Connector />

            {/* Four concurrent agents */}
            <div className="graph-column graph-concurrent">
              <p className="concurrent-label">Concurrent agents</p>
              <div className="concurrent-row">
                {['rider_adv','driver_adv','policy','fraud'].map(id=>{
                  const n=NODES.find(x=>x.id===id);
                  return <MonitorNode key={id} node={n}
                    state={visibleState(id)} stateLabel={visibleStateLabel(id)}
                    onClick={()=>onNodeClick(id)} active={activeNode===id}
                    compact
                  />;
                })}
              </div>
            </div>
            <Connector />

            {/* Judge */}
            <div className="graph-column">
              <MonitorNode
                node={NODES[6]}
                state={visibleState('judge')}
                stateLabel={visibleStateLabel('judge')}
                onClick={()=>onNodeClick('judge')}
                active={activeNode==='judge'}
              />
            </div>
            <Connector />

            {/* Policy gate */}
            <div className="graph-column">
              <MonitorNode
                node={NODES[7]}
                state={visibleState('gate')}
                stateLabel={visibleStateLabel('gate')}
                onClick={()=>onNodeClick('gate')}
                active={activeNode==='gate'}
              />
            </div>
            <Connector />

            {/* Final routing */}
            <div className="graph-column">
              <MonitorNode
                node={NODES[8]}
                state={visibleState('outcome')}
                stateLabel={visibleStateLabel('outcome')}
                onClick={()=>onNodeClick('outcome')}
                active={activeNode==='outcome'}
              />
            </div>
          </section>

          {/* Legend */}
          <section className="monitor-legend">
            <span className="legend-item"><span className="legend-dot legend-pending"/>Pending</span>
            <span className="legend-item"><span className="legend-dot legend-running"/>Running</span>
            <span className="legend-item"><span className="legend-dot legend-completed"/>Completed</span>
            <span className="legend-item"><span className="legend-dot legend-failed"/>Failed</span>
            <span className="legend-item"><span className="legend-dot legend-skipped"/>Skipped</span>
          </section>

          {/* Node detail panel */}
          {activeNode&&nodeStates[activeNode]&&nodeStates[activeNode].output&&(
            <NodeDetailPanel
              node={NODES.find(n=>n.id===activeNode)}
              data={nodeStates[activeNode].output}
              trace={traceForRole(detail.agent_trace, NODES.find(n=>n.id===activeNode)?.roleKey)}
              detail={detail}
              onClose={()=>setActiveNode(null)}
            />
          )}

          {/* Gate details */}
          {detail.gate&&activeNode==='gate'&&(
            <section className="monitor-detail-panel">
              <div className="detail-panel-header">
                <h3>Independent Policy Gate</h3>
                <button className="small secondary" onClick={()=>setActiveNode(null)}>Close</button>
              </div>
              <div className="detail-panel-body">
                <div className="detail-row">
                  <span className="detail-label">Decision path</span>
                  <b>{pathLabel(detail.gate.path)}</b>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Auto-eligible</span>
                  <b>{detail.gate.can_auto?'Yes':'No — human review required'}</b>
                </div>
                {detail.gate.blocking_rules&&detail.gate.blocking_rules.length>0&&(
                  <div className="detail-row">
                    <span className="detail-label">Blocking rules</span>
                    <span className="rule-chips">
                      {detail.gate.blocking_rules.map(r=><span key={r} className="rule-chip">{r}</span>)}
                    </span>
                  </div>
                )}
                {detail.gate.reasons&&detail.gate.reasons.length>0&&(
                  <div className="detail-section">
                    <h4>Escalation reasons</h4>
                    <ul className="reason-list">
                      {detail.gate.reasons.map((r,i)=><li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Outcome details */}
          {activeNode==='outcome'&&nodeStates.outcome&&nodeStates.outcome.output&&(
            <section className="monitor-detail-panel">
              <div className="detail-panel-header">
                <h3>Final Routing Decision</h3>
                <button className="small secondary" onClick={()=>setActiveNode(null)}>Close</button>
              </div>
              <div className="detail-panel-body">
                <div className="detail-row">
                  <span className="detail-label">Routing path</span>
                  <b>{pathLabel(nodeStates.outcome.output.path)}</b>
                </div>
                {nodeStates.outcome.output.mock_action?(
                  <>
                    <div className="detail-row">
                      <span className="detail-label">Recorded action</span>
                      <b>{dispositionLabel(nodeStates.outcome.output.mock_action.disposition)}</b>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Amount</span>
                      <b>SGD {Number(nodeStates.outcome.output.mock_action.amount||0).toFixed(2)}</b>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Receipt</span>
                      <code className="receipt-code">{nodeStates.outcome.output.mock_action.receipt}</code>
                    </div>
                    <p className="detail-note">Simulated record · No real funds transferred</p>
                  </>
                ):nodeStates.outcome.output.path==='IMMEDIATE_HUMAN_REVIEW'?(
                  <p className="detail-note">Safety incident — mandatory human review. No AI outcome, no financial action.</p>
                ):(
                  <p className="detail-note">Case routed to human review. No automated financial action recorded.</p>
                )}
              </div>
            </section>
          )}
        </>
      )}

      <div className="monitor-back-link monitor-back-bottom">
        <Link href="/">← Back to home</Link>
        <span className="monitor-disclaimer">
          Recorded run replay · States derived from actual stored traces · No fabricated timestamps
        </span>
      </div>
    </main>
  );
}

// ── MonitorNode component ──────────────────────────────────────────────────
function MonitorNode({node,state,stateLabel,onClick,active,compact}){
  const cls=STATE_CLASS[state]||STATE_CLASS.pending;
  const clickable=state==='completed'||state==='failed';
  return(
    <div
      className={`monitor-node ${cls} ${compact?'compact':''} ${active?'node-active':''} ${clickable?'clickable':''}`}
      onClick={clickable?onClick:undefined}
      role={clickable?'button':'img'}
      tabIndex={clickable?0:-1}
      aria-label={`${node.label} — ${stateLabel}`}
      onKeyDown={e=>{if(clickable&&(e.key==='Enter'||e.key===' ')){e.preventDefault();onClick()}}}
    >
      <div className="node-icon"/>
      <div className="node-label">{node.label}</div>
      <div className="node-sub">{node.sub}</div>
      <div className="node-state-tag">{stateLabel}</div>
    </div>
  );
}

// ── Connector between graph columns ─────────────────────────────────────────
function Connector(){
  return <div className="graph-connector" aria-hidden="true"><div className="connector-line"/></div>;
}

// ── NodeDetailPanel — shows actual agent output ────────────────────────────
function NodeDetailPanel({node,data,trace,detail,onClose}){
  // For agent nodes, data is the agent output dict
  const isAgent=!!data.agent_name;
  const failed=_isFailed(data);

  return(
    <section className="monitor-detail-panel">
      <div className="detail-panel-header">
        <h3>{node.label}</h3>
        <button className="small secondary" onClick={onClose}>Close</button>
      </div>
      <div className="detail-panel-body">
        {failed&&(
          <div className="alert alert-error">
            <b>Agent failure detected</b>
            {data.failure_kind&&<div>Failure kind: {data.failure_kind}</div>}
            {data.validation_error&&<div>Validation errors: {data.validation_error}</div>}
            {data.error_code&&<div>Error code: {data.error_code}</div>}
            {data.missing_fields&&data.missing_fields.length>0&&<div>Missing fields: {data.missing_fields.join(', ')}</div>}
            {data.invalid_fields&&data.invalid_fields.length>0&&<div>Invalid fields: {data.invalid_fields.join(', ')}</div>}
          </div>
        )}

        {isAgent&&data.summary&&(
          <div className="detail-section">
            <h4>Agent summary</h4>
            <p className="agent-summary">{data.summary}</p>
          </div>
        )}

        {isAgent&&data.recommended_disposition&&(
          <div className="detail-row">
            <span className="detail-label">Recommended disposition</span>
            <b>{dispositionLabel(data.recommended_disposition)}</b>
          </div>
        )}

        {isAgent&&data.recommended_amount!=null&&(
          <div className="detail-row">
            <span className="detail-label">Recommended amount</span>
            <b>SGD {Number(data.recommended_amount).toFixed(2)}</b>
          </div>
        )}

        {isAgent&&data.policy_rule_ids&&data.policy_rule_ids.length>0&&(
          <div className="detail-section">
            <h4>Policy references</h4>
            <div className="rule-chips">
              {data.policy_rule_ids.map(r=><span key={r} className="rule-chip">{r}</span>)}
            </div>
          </div>
        )}

        {isAgent&&data.supporting_evidence&&data.supporting_evidence.length>0&&(
          <div className="detail-section">
            <h4>Supporting evidence (fact keys)</h4>
            <ul className="evidence-list">
              {data.supporting_evidence.map((e,i)=><li key={i}>{e}</li>)}
            </ul>
          </div>
        )}

        {isAgent&&data.opposing_evidence&&data.opposing_evidence.length>0&&(
          <div className="detail-section">
            <h4>Opposing evidence</h4>
            <ul className="evidence-list">
              {data.opposing_evidence.map((e,i)=><li key={i}>{e}</li>)}
            </ul>
          </div>
        )}

        {isAgent&&data.uncertainties&&data.uncertainties.length>0&&(
          <div className="detail-section">
            <h4>Uncertainties</h4>
            <ul className="evidence-list">
              {data.uncertainties.map((u,i)=><li key={i}>{u}</li>)}
            </ul>
          </div>
        )}

        {isAgent&&data.mode&&(
          <div className="detail-row">
            <span className="detail-label">Mode</span>
            <code className="mode-code">{data.mode}</code>
          </div>
        )}

        {/* Trace entries for this agent */}
        {trace&&trace.length>0&&(
          <div className="detail-section">
            <h4>Recorded trace entries</h4>
            <div className="trace-entries">
              {trace.map((t,i)=>{
                const hasError=t.error_code||t.final===false&&t.error_code;
                return(
                  <div key={i} className={`trace-entry ${hasError?'trace-error':''}`}>
                    {t.event_author&&<span className="trace-field">author: {t.event_author}</span>}
                    {t.final!==undefined&&<span className="trace-field">final: {String(t.final)}</span>}
                    {t.tool_calls&&t.tool_calls.length>0&&
                      <span className="trace-field">tools: {t.tool_calls.join(', ')}</span>
                    }
                    {t.mode&&<span className="trace-field">mode: {t.mode}</span>}
                    {t.operation&&<span className="trace-field">op: {t.operation}</span>}
                    {t.error_code&&<span className="trace-field trace-err">error: {t.error_code}</span>}
                  </div>
                );
              })}
            </div>
            <p className="detail-note">
              Trace entries are recorded during actual execution. Concurrent agents
              may not preserve exact wall-clock completion order.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
