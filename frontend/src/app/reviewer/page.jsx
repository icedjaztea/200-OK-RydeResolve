'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {
  TONES, statusLabel, pathLabel, categoryLabel, dispositionLabel, notifKindLabel,
} from '../../lib/labels';

const REVIEW_DISPOSITIONS=[
  {value:'refund',label:'Refund (simulated)'},
  {value:'credit',label:'In-app credit (simulated)'},
  {value:'no_action',label:'No action'},
  {value:'reject_claim',label:'Reject claim'},
];

export default function ReviewerWorkbench(){
  const api=useApi();
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [policy,setPolicy]=useState(null);
  const [reviewDisposition,setReviewDisposition]=useState('refund');
  const [reviewAmount,setReviewAmount]=useState('0');
  const [reviewReason,setReviewReason]=useState('');
  const [precedent,setPrecedent]=useState('');
  const [packet,setPacket]=useState(null);
  const [report,setReport]=useState(null);
  const [learning,setLearning]=useState([]);
  const [learningId,setLearningId]=useState('');
  const [rollbackReason,setRollbackReason]=useState('');
  const [uploadFile,setUploadFile]=useState(null);
  const [uploadReport,setUploadReport]=useState(null);
  const [field,setField]=useState('rider_notified');
  const [factValue,setFactValue]=useState('false');
  const [provenance,setProvenance]=useState('Synthetic verified notification event export');
  const [auditResult,setAuditResult]=useState(null);

  async function connect(){
    setPolicy(await api.call('health'));
    const list=await api.call('cases');
    setCases(list);
  }

  async function selectCase(id){
    setDetail(await api.call('cases/'+id));
    setPacket(null);
  }

  async function loadLearning(){const data=await api.call('learning');setLearning(data.proposals||[])}

  const selected=detail?.case_id;
  const isSafety=detail?.path==='IMMEDIATE_HUMAN_REVIEW';

  return <main>
    <header className="masthead">
      <div className="brand">
        <div className="brand-icon" style={{background:'linear-gradient(135deg,#6b4fce,#9a7ee5)'}}>Rv</div>
        <div><h1>RydeResolve <span>Reviewer</span></h1><p>Operational dispute resolution workbench</p></div>
      </div>
      <div className="demo-label">DEMO ENVIRONMENT · SYNTHETIC DATA</div>
    </header>

    <section className="card connection">
      <div>
        <h2>Reviewer access</h2>
        <p>Enter your reviewer demo passcode from backend/.env. The backend enforces reviewer authorization independently. The demo API is not case-isolated; role filtering does not ensure real privacy.</p>
      </div>
      <input aria-label="Demo passcode" type="password" placeholder="reviewer passcode" value={api.key} onChange={e=>api.setKey(e.target.value)}/>
      <button disabled={api.busy||!api.key} onClick={()=>api.run(connect)}>Connect</button>
      {policy&&<span className="micro" style={{marginLeft:'12px'}}>Demo · {policy.ai_mode==='mock'?'Mock':'Live ADK'} · signoff: {policy.team_signoff_valid?'verified':'missing'}</span>}
    </section>

    {api.error&&<div className="alert error" role="alert">{api.error}</div>}
    {api.notice&&<div className="alert success">{api.notice}</div>}

    <div className="workspace">
      <aside className="card sidebar">
        <div className="section-head">
          <h2>Case queue</h2>
          <button className="small" disabled={!api.key||api.busy} onClick={()=>api.run(async()=>{await api.call('cases/seed',{method:'POST'});const l=await api.call('cases');setCases(l);api.setNotice('Synthetic demo cases loaded.')})}>Load demos</button>
        </div>
        {cases.length===0?<p className="muted">Enter passcode, click Connect, then Load demos.</p>:cases.map(item=>(
          <button key={item.case_id} className={'case-item '+(selected===item.case_id?'selected':'')} onClick={()=>api.run(()=>selectCase(item.case_id))}>
            <strong>{item.case_id}</strong>
            <span>{categoryLabel(item.category)}</span>
            <em className={'status '+(TONES[item.status]||'neutral')}>{statusLabel(item.status)}</em>
          </button>
        ))}
      </aside>

      <div className="primary">
        {!detail?<div className="card empty"><div className="empty-symbol">⌁</div><h2>Select a case</h2><p>Full reviewer workbench: evidence review, advocate perspectives, policy gates, decision packet, learning loop.</p></div>:
        <>
          <div className="card case-title">
            <div className="section-head">
              <div><p className="eyebrow">CASE {detail.case_id}</p><h2>{categoryLabel(detail.category)}</h2></div>
              <em className={'status '+(TONES[detail.status]||'neutral')}>{statusLabel(detail.status)}</em>
            </div>
            <p>{detail.description}</p>
            <div className="facts">
              <span>Disputed: SGD {detail.dispute_amount!=null?Number(detail.dispute_amount).toFixed(2):'unknown'}</span>
              <span>Trip: {detail.trip_id||'—'}</span>
              <span>Filed by: {detail.filed_by||'—'}</span>
              <span>Policy: {detail.policy_version||'2.1'}</span>
              <span>Source: SYNTHETIC</span>
            </div>
            <button disabled={api.busy||!api.key||detail.status==='RESOLVED'||detail.status==='REVIEWED_AND_RESOLVED'} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+selected+'/process',{method:'POST'});setDetail(r);api.setNotice('Case processing complete.')})}>Process / Re-evaluate</button>
          </div>

          {detail.path&&<div className="card result">
            <p className="eyebrow">DECISION PATH</p>
            <h2>{pathLabel(detail.path)}</h2>
            <p>{detail.candidate?.reason||'Awaiting evidence or human review.'}</p>
            {detail.gate?.reasons?.length>0&&<div style={{marginTop:'8px'}}><p className="muted" style={{marginBottom:'4px'}}>Policy rationale:</p><ul style={{fontSize:'12px',color:'#3d516c',lineHeight:'1.6',paddingLeft:'18px'}}>{detail.gate.reasons.map((r,i)=><li key={i}>{r}</li>)}</ul></div>}
            {detail.mock_action&&<div className="receipt">
              <b>{dispositionLabel(detail.mock_action.disposition)}</b> · SGD {Number(detail.mock_action.amount||0).toFixed(2)}
              <br/><small style={{color:'#5a7a62'}}>Test transaction · No real funds transferred · Receipt: {detail.mock_action.receipt}</small>
            </div>}
          </div>}

          {isSafety&&<div className="card highlight" style={{borderLeft:'5px solid #ad3140'}}>
            <p className="eyebrow">⚠ IMMEDIATE HUMAN REVIEW</p>
            <h3>Safety case — no AI fault or remedy ruling</h3>
            <p className="muted">AI does not determine fault or propose a remedy for safety incidents. The reviewer must independently assess safety allegations, determine fault, and select the remedy. Mandatory human review per SF-5.1 and SF-5.2.</p>
          </div>}

          {detail.notifications&&detail.notifications.length>0&&(
            <div className="card outbox">
              <p className="eyebrow">NOTIFICATION OUTBOX</p>
              <h3>Simulated notifications — not delivered</h3>
              <p className="muted">All entries are simulated. No email, SMS, push, or payment was sent. The demo API is not case-isolated.</p>
              <div className="notif-list">{detail.notifications.map((n,i)=>(
                <div key={i} className="notif-item">
                  <div className="notif-head"><span className="notif-kind">{notifKindLabel(n.kind)}</span><span className="notif-recipient">To: {n.recipient}</span><em className="status bad">Not delivered</em></div>
                  <p className="notif-msg">{n.message}</p>
                  <div className="notif-meta"><span>{n.created_at}</span>{n.receipt&&<span>Test receipt: {n.receipt}</span>}</div>
                </div>
              ))}</div>
            </div>
          )}

          <div className="twocol">
            <div className="card"><h3>Evidence and facts</h3><p className="muted">Claims are not automatically verified. Review provenance before relying on any fact.</p><details><summary>Show case facts</summary><pre className="json">{JSON.stringify(detail.facts,null,2)}</pre></details></div>
            <div className="card"><h3>Routing index</h3><p className="muted">Candidate rules are not rulings — they indicate which policy rules may apply.</p>{detail.routing?.candidate_rule_ids?.length?<div className="chips">{detail.routing.candidate_rule_ids.map(i=><span key={i}>{i}</span>)}</div>:<p className="muted">Process the case to retrieve routing IDs.</p>}</div>
          </div>

          {detail.agent_outputs&&<div className="card"><h3>Advocate and Judge outputs</h3><p className="muted">Visible results and traces — not private model chain of thought.</p>
            <div className="agents">{Object.entries(detail.agent_outputs).map(([n,v])=><div key={n} className="agent"><b>{n}</b><p>{v.summary}</p><small>Rules: {(v.policy_rule_ids||[]).join(', ')||'—'}</small>{v.mode&&<small> · {v.mode}</small>}</div>)}</div>
            <details><summary>Technical trace (events)</summary><pre className="json">{JSON.stringify(detail.agent_trace,null,2)}</pre></details>
          </div>}

          {detail.status==='AWAITING_CLARIFICATION'&&detail.clarifications?.some(c=>c.status==='PENDING')&&<div className="card highlight">
            <p className="eyebrow">ACTIVE INVESTIGATION</p>
            <h3>Clarification in progress — reviewer observes</h3>
            <p className="muted">The case is awaiting a party's clarification. As reviewer you observe; do not impersonate the rider or driver.</p>
            {detail.clarifications.filter(c=>c.status==='PENDING').map(c=>(
              <div key={c.request_id} className="pkt-clar">
                <div><span className="pkt-label">Requested from</span><span className="pkt-val">{c.recipient}</span><em className="status warn">Pending response</em></div>
                <p style={{marginTop:'4px'}}>{c.question}</p>
                <small>Required verified system evidence: {(c.required_verified_fields||[]).join(', ')||'—'}</small>
              </div>
            ))}
            {detail.clarifications.filter(c=>c.status==='ANSWERED').length>0&&<div className="packet-section"><h4>Unverified replies received</h4>
              {detail.clarifications.filter(c=>c.status==='ANSWERED').map(c=>(
                <div key={c.request_id} className="pkt-clar">
                  <div><span className="pkt-label">From</span><span className="pkt-val">{c.recipient}</span><em className="status bad">Unverified party account</em></div>
                  <p style={{marginTop:'4px'}}>{c.answer}</p>
                </div>
              ))}
            </div>}
          </div>}

          {detail.status!=='RESOLVED'&&detail.status!=='REVIEWED_AND_RESOLVED'&&<div className="card">
            <p className="eyebrow">EVIDENCE UPLOAD</p>
            <h3>Upload image or evidence file</h3>
            <p className="muted">PNG, JPEG, or PDF up to 5 MB. The visual description does not prove the image is authentic, taken in-app, or tied to the rider. Authenticity is unknown. Damage claims require mandatory human review.</p>
            <input aria-label="Choose synthetic image or evidence document" type="file" accept="image/png,image/jpeg,application/pdf" onChange={e=>setUploadFile(e.target.files?.[0]||null)}/>
            <button disabled={api.busy||!uploadFile} onClick={()=>api.run(async()=>{const form=new FormData();form.append('file',uploadFile);const result=await api.call('cases/'+selected+'/files',{method:'POST',body:form});setUploadReport(result);setDetail(await api.call('cases/'+selected));api.setNotice('Evidence file stored. Capture origin and authenticity remain unverified.')})}>Upload evidence</button>
            {uploadReport&&<details><summary>Image analysis and storage details</summary><pre className="json">{JSON.stringify(uploadReport,null,2)}</pre></details>}
          </div>}

          {detail.status!=='RESOLVED'&&detail.status!=='REVIEWED_AND_RESOLVED'&&<div className="card">
            <h3>Reviewer-only: Add synthetic verified-source fact</h3>
            <p className="muted">Import a synthetic system fact with provenance. Not a real integration. Party statements are never promoted to system facts.</p>
            <div className="fieldgrid">
              <input value={field} onChange={e=>setField(e.target.value)} placeholder="Field name"/>
              <input value={factValue} onChange={e=>setFactValue(e.target.value)} placeholder="JSON value, e.g. true"/>
              <input value={provenance} onChange={e=>setProvenance(e.target.value)} placeholder="Source description"/>
            </div>
            <button disabled={api.busy||!field} onClick={()=>api.run(async()=>{let value;try{value=JSON.parse(factValue)}catch{value=factValue}const p=await api.call('cases/'+selected+'/evidence',{method:'POST',body:{field,value,provenance}});setDetail(p);api.setNotice('Synthetic evidence added. Re-evaluate the case to see the updated assessment.')})}>Attach fact</button>
          </div>}

          {detail.status==='REVIEW_REQUIRED'&&<div className="card highlight">
            <p className="eyebrow">HUMAN REVIEW REQUIRED</p>
            <h3>Authorized simulated reviewer decision</h3>
            <div className="fieldgrid">
              <select value={reviewDisposition} onChange={e=>setReviewDisposition(e.target.value)}>{REVIEW_DISPOSITIONS.map(d=><option key={d.value} value={d.value}>{d.label}</option>)}</select>
              <input type="number" min="0" step="0.01" value={reviewAmount} onChange={e=>setReviewAmount(e.target.value)} placeholder="SGD amount"/>
            </div>
            <textarea value={reviewReason} onChange={e=>setReviewReason(e.target.value)} placeholder="Write justification based on evidence and policy (10+ characters)"/>
            <textarea value={precedent} onChange={e=>setPrecedent(e.target.value)} placeholder="Optional staged precedent for Innovation B"/>
            <button disabled={api.busy||reviewReason.length<10} onClick={()=>api.run(async()=>{const p=await api.call('cases/'+selected+'/review',{method:'POST',body:{disposition:reviewDisposition,amount:Number(reviewAmount),reason:reviewReason,proposed_precedent:precedent||null}});setDetail(p);if(p.learning_proposal_id)setLearningId(p.learning_proposal_id);api.setNotice('Reviewer decision recorded. Test transaction generated — no real funds transferred.')})}>Finalize review</button>
          </div>}

          {detail.status==='REVIEW_REQUIRED'&&<div className="card packet">
            <p className="eyebrow">REVIEWER DECISION PACKET</p>
            <h3>Decision packet for {detail.case_id}</h3>
            <button className="small" disabled={api.busy} onClick={()=>api.run(async()=>{const p=await api.call('cases/'+selected+'/review-packet');setPacket(p);api.setNotice('Decision packet assembled.')})}>Generate decision packet</button>
            {packet&&packet.case_details?.case_id===selected&&<>
              <div className="packet-section"><h4>Case details</h4><div className="packet-grid">
                <div><span className="pkt-label">Filed by</span><span className="pkt-val">{packet.case_details.filed_by}</span></div>
                <div><span className="pkt-label">Category</span><span className="pkt-val">{categoryLabel(packet.case_details.category)}</span></div>
                <div><span className="pkt-label">Status</span><span className="pkt-val">{statusLabel(packet.case_details.status)}</span></div>
                <div><span className="pkt-label">Policy version</span><span className="pkt-val">{packet.case_details.policy_version||'2.1'}</span></div>
                <div><span className="pkt-label">Rulebook version</span><span className="pkt-val">{packet.case_details.rulebook_version||'—'}</span></div>
                <div><span className="pkt-label">Dispute value</span><span className="pkt-val">SGD {packet.case_details.dispute_value!=null?Number(packet.case_details.dispute_value).toFixed(2):'—'}</span></div>
                <div><span className="pkt-label">Value basis</span><span className="pkt-val">{packet.case_details.dispute_value_basis||'—'}</span></div>
              </div></div>

              <div className="packet-section"><h4>Filed-by allegation</h4><p>{packet.filed_by_allegation||'—'}</p></div>

              <div className="packet-section"><h4>Structured facts with provenance</h4>
                {packet.structured_facts?.length>0?<table className="pkt-table"><thead><tr><th>Field</th><th>Value</th><th>Provenance</th><th>Verification</th></tr></thead><tbody>{packet.structured_facts.map((f,i)=><tr key={i}><td>{f.field}</td><td>{String(f.value)}</td><td>{f.provenance}</td><td>{f.verification}</td></tr>)}</tbody></table>:<p className="muted">No structured facts</p>}
              </div>

              <div className="packet-section"><h4>Gaps (missing evidence)</h4>{packet.gaps?.length>0?<ul>{packet.gaps.map((g,i)=><li key={i}>{g}</li>)}</ul>:<p className="muted">None</p>}</div>

              <div className="packet-section"><h4>Contradictions (conflicting evidence)</h4>{packet.contradictions?.length>0?<ul>{packet.contradictions.map((c,i)=><li key={i}>{c}</li>)}</ul>:<p className="muted">None</p>}</div>

              <div className="packet-section"><h4>Clarification history</h4>
                {packet.clarification_history?.length>0?packet.clarification_history.map((c,i)=><div key={i} className="pkt-clar">
                  <span className="pkt-label">Requested from {c.recipient}</span>
                  <span className="pkt-val">{c.question}</span>
                  <em className={'status '+(c.status==='PENDING'?'warn':c.status==='ANSWERED'?'good':'neutral')}>{c.status==='PENDING'?'Pending':c.status==='ANSWERED'?'Answered':statusLabel(c.status)}</em>
                </div>):<p className="muted">No clarifications issued</p>}
              </div>

              <div className="packet-section"><h4>Unverified replies</h4>
                {packet.unverified_replies?.length>0?packet.unverified_replies.map((r,i)=><div key={i} className="pkt-clar">
                  <span className="pkt-label">From {r.recipient}</span>
                  <span className="pkt-val">{r.answer}</span>
                  <em className="status bad">Unverified party account</em>
                </div>):<p className="muted">No unverified replies</p>}
              </div>

              <div className="packet-section"><h4>Candidate policy IDs</h4>{packet.candidate_policy_ids?.length>0?<div className="chips">{packet.candidate_policy_ids.map(id=><span key={id}>{id}</span>)}</div>:<p className="muted">None</p>}</div>

              <div className="packet-section"><h4>Escalation blocking rule IDs</h4>{packet.escalation_blocking_rule_ids?.length>0?<div className="chips">{packet.escalation_blocking_rule_ids.map(id=><span key={id}>{id}</span>)}</div>:<p className="muted">No blocking rules</p>}</div>

              <div className="packet-section"><h4>Gate reasons</h4>{packet.gate_reasons?.length>0?<ul>{packet.gate_reasons.map((r,i)=><li key={i}>{r}</li>)}</ul>:<p className="muted">No blocking reasons</p>}</div>

              <div className="packet-section"><h4>Advocate summaries <small className="pkt-mode">{packet.advocate_summaries?Object.keys(packet.advocate_summaries).length+' agents':'—'}</small></h4>
                {packet.advocate_summaries&&Object.entries(packet.advocate_summaries).map(([role,sum])=><div key={role} className="pkt-adv"><b>{role}</b><p>{sum.summary}</p><small>Recommendation: {dispositionLabel(sum.recommended_disposition)} · Mode: {sum.mode}{sum.policy_rule_ids?.length>0?' · Rules: '+sum.policy_rule_ids.join(', '):''}</small></div>)}
              </div>

              <div className="packet-section"><h4>Observable event traces</h4>
                {packet.event_traces?.length>0?<details><summary>{packet.event_traces.length} events (mock/live labeled)</summary><pre className="json">{JSON.stringify(packet.event_traces,null,2)}</pre></details>:<p className="muted">No events recorded</p>}
              </div>

              {packet.is_safety?<div className="packet-section pkt-safety"><h4>Safety note — no AI fault or remedy proposal</h4><p>{packet.safety_note||'Safety case: AI does not determine fault or propose a remedy. Reviewer must independently assess.'}</p></div>:<div className="packet-section pkt-proposal"><h4>Non-safety candidate — proposal only</h4><p>AI recommendation is a proposal only. The reviewer must independently decide.</p></div>}

              <div className="packet-section"><h4>AI recommendation (separate from human decision)</h4>
                <div className="pkt-rec">
                  <div><span className="pkt-label">Recommendation</span><span className="pkt-val">{dispositionLabel(packet.ai_recommendation.disposition)}</span></div>
                  <div><span className="pkt-label">Amount</span><span className="pkt-val">SGD {Number(packet.ai_recommendation.amount||0).toFixed(2)}</span></div>
                  <div><span className="pkt-label">Proposal only</span><span className="pkt-val">{String(packet.ai_recommendation.is_proposal_only)}</span></div>
                </div>
                {packet.ai_recommendation.reason&&<p className="muted" style={{marginTop:'6px'}}>{packet.ai_recommendation.reason}</p>}
              </div>

              {packet.human_decision?<div className="packet-section pkt-decision"><h4>Human decision (authorized)</h4>
                <div className="pkt-rec">
                  <div><span className="pkt-label">Disposition</span><span className="pkt-val">{dispositionLabel(packet.human_decision.disposition)}</span></div>
                  <div><span className="pkt-label">Amount</span><span className="pkt-val">SGD {Number(packet.human_decision.amount||0).toFixed(2)}</span></div>
                  <div><span className="pkt-label">Reason</span><span className="pkt-val">{packet.human_decision.reason}</span></div>
                  <div><span className="pkt-label">Authorized by</span><span className="pkt-val">{packet.human_decision.authorized_by}</span></div>
                  <div><span className="pkt-label">Timestamp</span><span className="pkt-val">{packet.human_decision.timestamp}</span></div>
                  <div><span className="pkt-label">Test receipt</span><span className="pkt-val">{packet.human_decision.simulated_receipt}</span></div>
                </div>
                <p className="muted" style={{marginTop:'6px'}}>Test transaction — no real funds transferred.</p>
              </div>:<div className="packet-section"><h4>Human decision</h4><p className="muted">No human decision recorded yet</p></div>}

              <div className="packet-section"><h4>Original escalation (preserved for traceability)</h4><p className="pkt-val">{pathLabel(packet.original_escalation)||'—'}</p></div>

              <div className="packet-section pkt-warning"><h4>⚠ Synthetic demo warning</h4><p>{packet.synthetic_warning}</p></div>
            </>}
          </div>}

          <div className="card">
            <p className="eyebrow">GOVERNED LEARNING</p>
            <h3>Test before release</h3>
            <div className="fieldgrid">
              <input value={learningId} onChange={e=>setLearningId(e.target.value)} placeholder="Learning proposal ID"/>
              <button disabled={api.busy||!learningId} onClick={()=>api.run(async()=>{const p=await api.call('learning/'+learningId+'/evaluate',{method:'POST'});api.setNotice(`${p.evaluation.regression.passed}/${p.evaluation.regression.total} regression checks passed.`);await loadLearning()})}>Run regression</button>
              <button disabled={api.busy||!learningId} onClick={()=>api.run(async()=>{await api.call('learning/'+learningId+'/approve',{method:'POST',body:{rationale:'Approved after policy and regression review for synthetic demo'}});api.setNotice('Approved precedent published.');await loadLearning()})}>Approve release</button>
            </div>
            <div className="fieldgrid">
              <input aria-label="Rollback reason" value={rollbackReason} onChange={e=>setRollbackReason(e.target.value)} placeholder="Rollback reason (10+ chars)"/>
              <button disabled={api.busy||!learningId||rollbackReason.trim().length<10} onClick={()=>api.run(async()=>{await api.call('learning/'+learningId+'/rollback',{method:'POST',body:{rationale:rollbackReason}});api.setNotice('Precedent rolled back.');await loadLearning()})}>Rollback</button>
            </div>
            <button className="small" disabled={api.busy} onClick={()=>api.run(async()=>{setReport(await api.call('evaluation/reference'));await loadLearning()})}>Show evaluation report</button>
            {report&&<p><b>{report.passed}/{report.total}</b> deterministic regression cases passed.</p>}
            {learning.length>0&&<details><summary>Learning proposals</summary><pre className="json">{JSON.stringify(learning,null,2)}</pre></details>}
          </div>

          <div className="card"><h3>Audit and state</h3><p className="muted">Case events are hash-linked for demo tamper detection. Tamper-evident hashes are not immutable storage.</p>
            <button className="small" disabled={api.busy} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+selected+'/verify-audit');setAuditResult(r);api.setNotice(r.valid?'Audit chain verified — no tampering detected.':'Audit chain broken — events may have been altered.')})}>Verify audit integrity</button>
            {auditResult&&<p><b>Chain valid: {String(auditResult.valid)}</b></p>}
            <details><summary>Show event record</summary><pre className="json">{JSON.stringify(detail.events,null,2)}</pre></details>
            <details><summary>Show complete case document</summary><pre className="json">{JSON.stringify(detail,null,2)}</pre></details>
          </div>
        </>}
      </div>
    </div>

    <div className="card" style={{textAlign:'center',padding:'16px'}}>
      <Link href="/" className="lab-enter">← Back to role selection</Link>
      <span style={{margin:'0 12px',color:'#ccc'}}>·</span>
      <Link href="/lab" className="lab-enter">Full dashboard →</Link>
    </div>

    <footer>RydeResolve is a synthetic hackathon demo. No real payments, notifications, or account actions were executed. All data is synthetic.</footer>
  </main>;
}
