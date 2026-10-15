'use client';
import {useState,useEffect,useCallback} from 'react';
import {
  TONES, statusLabel, pathLabel, categoryLabel, dispositionLabel, notifKindLabel,
} from '../../lib/labels';

export default function Dashboard(){
  const [key,setKey]=useState('');const [role,setRole]=useState('reviewer');
  const [cases,setCases]=useState([]);const [detail,setDetail]=useState(null);
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const [reviewDisposition,setReviewDisposition]=useState('refund');const [reviewAmount,setReviewAmount]=useState('0');
  const [reviewReason,setReviewReason]=useState('');const [precedent,setPrecedent]=useState('');
  const [answer,setAnswer]=useState('');const [field,setField]=useState('rider_notified');
  const [factValue,setFactValue]=useState('false');const [provenance,setProvenance]=useState('Synthetic verified notification event export');
  const [learning,setLearning]=useState([]);const [learningId,setLearningId]=useState('');const [report,setReport]=useState(null);
  const [policy,setPolicy]=useState(null);
  const [uploadFile,setUploadFile]=useState(null);
  const [uploadReport,setUploadReport]=useState(null);
  const [rollbackReason,setRollbackReason]=useState('');
  const [packet,setPacket]=useState(null);

  const call=useCallback(async(path,opts={})=>{
    if(!key)throw Error('Enter your demo passcode first.');
    const headers={'X-Demo-Key':key,...opts.headers};
    if(opts.body && !(opts.body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch('/api/proxy/'+path,{method:opts.method||'GET',headers,
      body:opts.body instanceof FormData?opts.body:opts.body?JSON.stringify(opts.body):undefined});
    let data;try{data=await response.json()}catch{data={detail:`HTTP ${response.status}`}}
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data));
    return data;
  },[key]);

  const refresh=useCallback(async(keep)=>{
    if(!key)return;
    const list=await call('cases');setCases(list);
    if(keep){setDetail(await call('cases/'+keep))}
  },[call,key]);

  useEffect(()=>{if(key){refresh(detail?.case_id).catch(e=>setError(e.message))}},[key]);
  async function run(fn){setBusy(true);setError('');setNotice('');try{await fn()}catch(e){setError(e.message)}finally{setBusy(false)}}
  const selected=detail?.case_id;
  const latestPending=detail?.clarifications?.find(c=>c.status==='PENDING');

  return <main>
    <header className="masthead">
      <div className="brand"><div className="brand-icon">R</div><div><h1>RydeResolve <span>Lab</span></h1><p>Synthetic, policy-grounded dispute resolution</p></div></div>
      <div className="demo-label">HACKATHON DEMO · NO REAL PAYMENTS</div>
    </header>
    <section className="connection card">
      <div><h2>Demo access</h2><p>Enter a role's passcode from backend/.env. This is demo-only access, not production identity.</p></div>
      <select value={role} onChange={e=>setRole(e.target.value)}><option value="reviewer">Reviewer</option><option value="rider">Rider</option><option value="driver">Driver</option></select>
      <input aria-label="Demo passcode" type="password" placeholder={`${role} passcode`} value={key} onChange={e=>setKey(e.target.value)}/>
      <button onClick={()=>run(async()=>{await refresh(selected);setPolicy(await call('health'))})} disabled={busy||!key}>Connect</button>
    </section>
    {error&&<div className="alert error" role="alert">{error}</div>}{notice&&<div className="alert success">{notice}</div>}
    {policy&&<div className="micro">Backend: {policy.ai_mode==='mock'?'MOCK MODE (no model calls)':'LIVE ADK'} · Policy signoff: {policy.team_signoff_valid?'verified':'missing — automatic decisions blocked'} · {policy.storage_mode}</div>}
    <section className="workspace">
      <aside className="card sidebar">
        <div className="section-head"><h2>Case queue</h2><button className="small" disabled={!key||busy} onClick={()=>run(async()=>{await call('cases/seed',{method:'POST'});await refresh();setNotice('Synthetic cases loaded.')})}>Load demos</button></div>
        {cases.length===0?<p className="muted">Enter demo key, click Connect, then Load demos.</p>:cases.map(item=><button key={item.case_id} className={'case-item '+(selected===item.case_id?'selected':'')} onClick={()=>run(async()=>setDetail(await call('cases/'+item.case_id)))}>
          <strong>{item.case_id}</strong><span>{categoryLabel(item.category)}</span><em className={'status '+(TONES[item.status]||'neutral')}>{statusLabel(item.status)}</em>
        </button>)}
      </aside>
      <div className="primary">
        {!detail?<div className="card empty"><div className="empty-symbol">⌁</div><h2>Select a synthetic case</h2><p>Explore evidence, opposing advocates, rule references, safe review gates and mock remedies.</p></div>:
        <>
          <div className="card case-title">
            <div className="section-head"><div><p className="eyebrow">CASE {detail.case_id}</p><h2>{categoryLabel(detail.category)}</h2></div><em className={'status '+(TONES[detail.status]||'neutral')}>{statusLabel(detail.status)}</em></div>
            <p>{detail.description}</p><div className="facts"><span>Disputed: SGD {detail.dispute_amount!=null?Number(detail.dispute_amount).toFixed(2):'unknown'}</span><span>Policy: {detail.policy_version||'2.1'}</span><span>Source: SYNTHETIC</span></div>
            <button disabled={busy||!key||detail.status==='RESOLVED'||detail.status==='REVIEWED_AND_RESOLVED'} onClick={()=>run(async()=>{const result=await call('cases/'+selected+'/process',{method:'POST'});setDetail(result);await refresh(selected);setNotice('Case processing finished. Inspect the route and trace.');})}>Process / Re-evaluate case</button>
          </div>
          {detail.path&&<div className="card result"><p className="eyebrow">Decision path</p><h2>{pathLabel(detail.path)}</h2><p>{detail.candidate?.reason||'Awaiting evidence or human reviewer'}</p>
            {detail.gate?.reasons?.length>0&&<ul>{detail.gate.reasons.map((r,i)=><li key={i}>{r}</li>)}</ul>}
            {detail.mock_action&&<div className="receipt"><b>{dispositionLabel(detail.mock_action.disposition)}</b> · SGD {Number(detail.mock_action.amount||0).toFixed(2)}<br/><small style={{color:'#5a7a62'}}>Test transaction · No real funds transferred · Receipt: {detail.mock_action.receipt}</small></div>}
          </div>}
          {detail.path==='IMMEDIATE_HUMAN_REVIEW'&&<div className="card highlight" style={{borderLeft:'5px solid #ad3140'}}><p className="eyebrow">⚠ SAFETY ESCALATION</p><h3>This case requires immediate human review</h3><p className="muted">AI does not determine fault or propose a remedy for safety incidents. A reviewer must independently assess safety allegations per SF-5.1 and SF-5.2.</p></div>}
          {detail.notifications&&detail.notifications.length>0&&<div className="card outbox">
            <p className="eyebrow">NOTIFICATION OUTBOX</p>
            <h3>Simulated notifications — not delivered</h3>
            <p className="muted">All entries are simulated. No email, SMS, push, or payment was sent. The demo API is not user-isolated; role filtering does not ensure real privacy.</p>
            <div className="notif-list">{detail.notifications.map((n,i)=><div key={i} className="notif-item">
              <div className="notif-head"><span className="notif-kind">{notifKindLabel(n.kind)}</span><span className="notif-recipient">To: {n.recipient}</span><em className="status bad">Not delivered</em></div>
              <p className="notif-msg">{n.message}</p>
              <div className="notif-meta"><span>{n.created_at}</span>{n.receipt&&<span>Test receipt: {n.receipt}</span>}{n.request_id&&<span>Request: {n.request_id}</span>}</div>
            </div>)}</div>
          </div>}
          <div className="twocol">
            <div className="card"><h3>Evidence and facts</h3><p className="muted">Claims are not automatically verified; review evidence sources.</p><Json value={detail.facts}/></div>
            <div className="card"><h3>Routing index</h3><p className="muted">Candidate rules are not rulings.</p>{detail.routing?.candidate_rule_ids?.length?<div className="chips">{detail.routing.candidate_rule_ids.map(i=><span key={i}>{i}</span>)}</div>:<p>Process the case to retrieve routing IDs.</p>}</div>
          </div>
          {detail.agent_outputs&&<div className="card"><h3>Advocate and Judge outputs</h3><p className="muted">Visible results and tool/event traces, not private model chain of thought.</p>
              <div className="agents">{Object.entries(detail.agent_outputs).map(([n,v])=><div key={n} className="agent"><b>{n}</b><p>{v.summary}</p><small>Rules: {(v.policy_rule_ids||[]).join(', ')||'—'}</small>{v.mode&&<small> · {v.mode}</small>}</div>)}</div>
              <details><summary>Technical trace (events)</summary><Json value={detail.agent_trace}/></details>
            </div>}
          {detail.status==='AWAITING_CLARIFICATION'&&latestPending&&<div className="card highlight"><p className="eyebrow">ACTIVE INVESTIGATION</p><h3>Awaiting {latestPending.recipient}'s clarification</h3><p>{latestPending.question}</p><textarea placeholder="Answer as the intended party. Remember: answer alone is not verified evidence." value={answer} onChange={e=>setAnswer(e.target.value)}/><button disabled={busy||!answer} onClick={()=>run(async()=>{const p=await call(`cases/${selected}/clarifications/${latestPending.request_id}/reply`,{method:'POST',body:{answer}});setDetail(p);setAnswer('');setNotice('Your response has been recorded as an unverified claim. The reviewer may request source documentation.')})}>Submit clarification</button></div>}
          {role==='reviewer'&&detail.status!=='RESOLVED'&&detail.status!=='REVIEWED_AND_RESOLVED'&&<div className="card">
            <p className="eyebrow">EVIDENCE UPLOAD</p>
            <h3>Upload image or evidence file</h3>
            <p className="muted">PNG, JPEG, or PDF up to 5 MB. The visual description does not prove the image is authentic, taken in-app, or tied to the rider. Authenticity is unknown. Damage claims require mandatory human review.</p>
            <input aria-label="Choose synthetic image or evidence document" type="file" accept="image/png,image/jpeg,application/pdf" onChange={e=>setUploadFile(e.target.files?.[0]||null)}/>
            <button disabled={busy||!uploadFile} onClick={()=>run(async()=>{const form=new FormData();form.append('file',uploadFile);const result=await call('cases/'+selected+'/files',{method:'POST',body:form});setUploadReport(result);setDetail(await call('cases/'+selected));setNotice('Evidence file stored. Capture origin and authenticity remain unverified.');})}>Upload evidence</button>
            {uploadReport&&<details><summary>Image analysis and storage details</summary><Json value={uploadReport}/></details>}
          </div>}
          {role==='reviewer'&&detail.status!=='RESOLVED'&&detail.status!=='REVIEWED_AND_RESOLVED'&&<div className="card"><h3>Reviewer-only: Add synthetic verified-source fact</h3><p className="muted">For the investigation demo, import a synthetic system fact with provenance. Not a real integration.</p><div className="fieldgrid"><input value={field} onChange={e=>setField(e.target.value)} placeholder="Field name"/><input value={factValue} onChange={e=>setFactValue(e.target.value)} placeholder="JSON value, e.g. true"/><input value={provenance} onChange={e=>setProvenance(e.target.value)} placeholder="Source description"/></div><button disabled={busy||!field} onClick={()=>run(async()=>{let value;try{value=JSON.parse(factValue)}catch{value=factValue}const p=await call('cases/'+selected+'/evidence',{method:'POST',body:{field,value,provenance}});setDetail(p);setNotice('Synthetic evidence added; re-evaluate case.')})}>Attach fact</button></div>}
          {role==='reviewer'&&detail.status==='REVIEW_REQUIRED'&&<div className="card highlight"><p className="eyebrow">HUMAN REVIEW REQUIRED</p><h3>Authorized simulated reviewer decision</h3><div className="fieldgrid"><select value={reviewDisposition} onChange={e=>setReviewDisposition(e.target.value)}><option value="refund">Refund (simulated)</option><option value="credit">In-app credit (simulated)</option><option value="no_action">No action</option><option value="reject_claim">Reject claim</option></select><input type="number" min="0" step="0.01" value={reviewAmount} onChange={e=>setReviewAmount(e.target.value)} placeholder="SGD amount"/></div><textarea value={reviewReason} onChange={e=>setReviewReason(e.target.value)} placeholder="Write justification based on evidence and policy (10+ characters)"/><textarea value={precedent} onChange={e=>setPrecedent(e.target.value)} placeholder="Optional staged precedent for Innovation B"/><button disabled={busy||reviewReason.length<10} onClick={()=>run(async()=>{const p=await call('cases/'+selected+'/review',{method:'POST',body:{disposition:reviewDisposition,amount:Number(reviewAmount),reason:reviewReason,proposed_precedent:precedent||null}});setDetail(p);await refresh(selected);if(p.learning_proposal_id)setLearningId(p.learning_proposal_id);setNotice('Reviewer decision recorded. Test transaction generated — no real funds transferred.')})}>Finalize simulated review</button></div>}
          {role==='reviewer'&&detail.status==='REVIEW_REQUIRED'&&<div className="card packet">
            <p className="eyebrow">REVIEWER DECISION PACKET</p>
            <h3>Complete decision packet for {detail.case_id}</h3>
            <button className="small" disabled={busy} onClick={()=>run(async()=>{const p=await call('cases/'+selected+'/review-packet');setPacket(p);setNotice('Reviewer Decision Packet assembled.')})}>Generate decision packet</button>
            {packet&&packet.case_details?.case_id===selected&&<>
              <div className="packet-section"><h4>Case details</h4><div className="packet-grid"><div><span className="pkt-label">Filed by</span><span className="pkt-val">{packet.case_details.filed_by}</span></div><div><span className="pkt-label">Category</span><span className="pkt-val">{categoryLabel(packet.case_details.category)}</span></div><div><span className="pkt-label">Status</span><span className="pkt-val">{statusLabel(packet.case_details.status)}</span></div><div><span className="pkt-label">Policy version</span><span className="pkt-val">{packet.case_details.policy_version}</span></div><div><span className="pkt-label">Dispute value</span><span className="pkt-val">SGD {packet.case_details.dispute_value!=null?Number(packet.case_details.dispute_value).toFixed(2):'—'}</span></div><div><span className="pkt-label">Value basis</span><span className="pkt-val">{packet.case_details.dispute_value_basis}</span></div></div></div>
              <div className="packet-section"><h4>Filed-by allegation</h4><p>{packet.filed_by_allegation}</p></div>
              <div className="packet-section"><h4>Structured facts with provenance</h4>{packet.structured_facts.length>0?<table className="pkt-table"><thead><tr><th>Field</th><th>Value</th><th>Provenance</th><th>Verification</th></tr></thead><tbody>{packet.structured_facts.map((f,i)=><tr key={i}><td>{f.field}</td><td>{String(f.value)}</td><td>{f.provenance}</td><td>{f.verification}</td></tr>)}</tbody></table>:<p className="muted">No structured facts</p>}</div>
              <div className="packet-section"><h4>Gaps</h4>{packet.gaps.length>0?<ul>{packet.gaps.map((g,i)=><li key={i}>{g}</li>)}</ul>:<p className="muted">None</p>}</div>
              <div className="packet-section"><h4>Contradictions</h4>{packet.contradictions.length>0?<ul>{packet.contradictions.map((c,i)=><li key={i}>{c}</li>)}</ul>:<p className="muted">None</p>}</div>
              <div className="packet-section"><h4>Clarification history</h4>{packet.clarification_history.length>0?packet.clarification_history.map((c,i)=><div key={i} className="pkt-clar"><span className="pkt-label">To {c.recipient}</span><span className="pkt-val">{c.question}</span><em className={'status '+(c.status==='PENDING'?'warn':c.status==='ANSWERED'?'good':'neutral')}>{c.status==='PENDING'?'Pending':c.status==='ANSWERED'?'Answered':statusLabel(c.status)}</em></div>):<p className="muted">No clarifications issued</p>}</div>
              <div className="packet-section"><h4>Unverified replies</h4>{packet.unverified_replies.length>0?packet.unverified_replies.map((r,i)=><div key={i} className="pkt-clar"><span className="pkt-label">From {r.recipient}</span><span className="pkt-val">{r.answer}</span><em className="status bad">Unverified party account</em></div>):<p className="muted">No unverified replies</p>}</div>
              <div className="packet-section"><h4>Candidate policy IDs</h4><div className="chips">{packet.candidate_policy_ids.map(id=><span key={id}>{id}</span>)}</div></div>
              <div className="packet-section"><h4>Escalation blocking rule IDs</h4><div className="chips">{packet.escalation_blocking_rule_ids.map(id=><span key={id}>{id}</span>)}</div></div>
              <div className="packet-section"><h4>Gate reasons</h4>{packet.gate_reasons.length>0?<ul>{packet.gate_reasons.map((r,i)=><li key={i}>{r}</li>)}</ul>:<p className="muted">No blocking reasons</p>}</div>
              <div className="packet-section"><h4>Advocate summaries</h4>{Object.entries(packet.advocate_summaries).map(([role,sum])=><div key={role} className="pkt-adv"><b>{role}</b><p>{sum.summary}</p><small>Recommendation: {dispositionLabel(sum.recommended_disposition)} · Mode: {sum.mode}</small>{sum.policy_rule_ids?.length>0&&<small> · Rules: {sum.policy_rule_ids.join(', ')}</small>}</div>)}</div>
              <div className="packet-section"><h4>Observable event traces</h4><details><summary>{packet.event_traces.length} events (mock/live labeled)</summary><Json value={packet.event_traces}/></details></div>
              {packet.is_safety?<div className="packet-section pkt-safety"><h4>Safety note — no AI fault or remedy proposal</h4><p>{packet.safety_note||'Safety case: AI does not determine fault or propose a remedy. Reviewer must independently assess.'}</p></div>:<div className="packet-section pkt-proposal"><h4>Non-safety candidate — proposal only</h4><p>AI recommendation is a proposal only. The reviewer must independently decide.</p></div>}
              <div className="packet-section"><h4>AI recommendation (separate from human decision)</h4><div className="pkt-rec"><div><span className="pkt-label">Recommendation</span><span className="pkt-val">{dispositionLabel(packet.ai_recommendation.disposition)}</span></div><div><span className="pkt-label">Amount</span><span className="pkt-val">SGD {Number(packet.ai_recommendation.amount||0).toFixed(2)}</span></div><div><span className="pkt-label">Proposal only</span><span className="pkt-val">{String(packet.ai_recommendation.is_proposal_only)}</span></div></div><p className="muted">{packet.ai_recommendation.reason}</p></div>
              {packet.human_decision?<div className="packet-section pkt-decision"><h4>Human decision (authorized)</h4><div className="pkt-rec"><div><span className="pkt-label">Disposition</span><span className="pkt-val">{dispositionLabel(packet.human_decision.disposition)}</span></div><div><span className="pkt-label">Amount</span><span className="pkt-val">SGD {Number(packet.human_decision.amount||0).toFixed(2)}</span></div><div><span className="pkt-label">Reason</span><span className="pkt-val">{packet.human_decision.reason}</span></div><div><span className="pkt-label">Authorized by</span><span className="pkt-val">{packet.human_decision.authorized_by}</span></div><div><span className="pkt-label">Timestamp</span><span className="pkt-val">{packet.human_decision.timestamp}</span></div><div><span className="pkt-label">Test receipt</span><span className="pkt-val">{packet.human_decision.simulated_receipt}</span></div></div><p className="muted" style={{marginTop:'6px'}}>Test transaction — no real funds transferred.</p></div>:<div className="packet-section"><h4>Human decision</h4><p className="muted">No human decision recorded yet</p></div>}
              <div className="packet-section"><h4>Original escalation (preserved for traceability)</h4><p className="pkt-val">{pathLabel(packet.original_escalation)}</p></div>
              <div className="packet-section pkt-warning"><h4>⚠ Synthetic demo warning</h4><p>{packet.synthetic_warning}</p></div>
            </>}
          </div>}
          {role==='reviewer'&&<div className="card"><p className="eyebrow">GOVERNED LEARNING</p><h3>Test before release</h3><p>Stage a correction during reviewer decision above. Evaluate the 12-case regression suite, then approve the precedent. Policy JSON is never automatically changed.</p><div className="fieldgrid"><input value={learningId} onChange={e=>setLearningId(e.target.value)} placeholder="Learning proposal ID"/><button disabled={busy||!learningId} onClick={()=>run(async()=>{const p=await call('learning/'+learningId+'/evaluate',{method:'POST'});setNotice(`${p.evaluation.regression.passed}/${p.evaluation.regression.total} policy regression checks passed.`);await loadLearning()})}>Run regression</button><button disabled={busy||!learningId} onClick={()=>run(async()=>{await call('learning/'+learningId+'/approve',{method:'POST',body:{rationale:'Approved after policy and regression review for synthetic demo'}});setNotice('Approved precedent published.');await loadLearning()})}>Approve release</button></div>
            <div className="fieldgrid"><input aria-label="Learning rollback reason" value={rollbackReason} onChange={e=>setRollbackReason(e.target.value)} placeholder="Rollback reason (10+ characters)"/><button disabled={busy||!learningId||rollbackReason.trim().length<10} onClick={()=>run(async()=>{await call('learning/'+learningId+'/rollback',{method:'POST',body:{rationale:rollbackReason}});setNotice('Precedent rolled back.');await loadLearning()})}>Rollback</button></div>
            <button className="small" disabled={busy} onClick={()=>run(async()=>{setReport(await call('evaluation/reference'));await loadLearning()})}>Show evaluation report</button>
            {report&&<p><b>{report.passed}/{report.total}</b> deterministic regression cases passed. This is not live model accuracy.</p>}{learning.length>0&&<details><summary>Learning proposals</summary><Json value={learning}/></details>}</div>}
          <div className="card"><h3>Audit and state</h3><p className="muted">Case events are hash-linked for demo tamper detection. Tamper-evident hashes are not immutable storage.</p><details><summary>Show event record</summary><Json value={detail.events}/></details><details><summary>Show complete case document</summary><Json value={detail}/></details></div>
        </>}
      </div>
    </section>
    <footer>RydeResolve is a synthetic hackathon demo. No real payments, notifications, or account actions were executed. All data is synthetic.</footer>
  </main>;
  async function loadLearning(){const data=await call('learning');setLearning(data.proposals||[])}
}
function Json({value}){return <pre className="json">{JSON.stringify(value||{},null,2)}</pre>}
