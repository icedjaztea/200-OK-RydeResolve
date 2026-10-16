'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {CaseTimeline} from '../../lib/Timeline';
import {
  TONES, statusLabel, pathLabel, categoryLabel, dispositionLabel, notifKindLabel,
} from '../../lib/labels';

const REVIEW_DISPOSITIONS=[
  {value:'refund',label:'Refund (simulated)'},
  {value:'credit',label:'In-app credit (simulated)'},
  {value:'no_action',label:'No action'},
  {value:'reject_claim',label:'Reject claim'},
];

const TABS=[
  {id:'overview',label:'Overview'},
  {id:'evidence',label:'Evidence'},
  {id:'agents',label:'Agent Findings'},
  {id:'decision',label:'Review Decision'},
  {id:'audit',label:'Audit / Advanced'},
];

export default function ReviewerWorkbench(){
  const api=useApi();
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [policy,setPolicy]=useState(null);
  const [tab,setTab]=useState('overview');
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
  const [showConfirm,setShowConfirm]=useState(false);
  const [processing,setProcessing]=useState(false);

  async function connect(){
    setPolicy(await api.call('health'));
    const list=await api.call('cases');
    setCases(list);
  }

  async function selectCase(id){
    setDetail(await api.call('cases/'+id));
    setPacket(null);
    setTab('overview');
  }

  async function loadLearning(){const data=await api.call('learning');setLearning(data.proposals||[])}

  const selected=detail?.case_id;
  const isSafety=detail?.path==='IMMEDIATE_HUMAN_REVIEW';
  const isReviewRequired=detail?.status==='REVIEW_REQUIRED';
  const isClarifying=detail?.status==='AWAITING_CLARIFICATION';
  const isResolved=detail?.status==='RESOLVED'||detail?.status==='REVIEWED_AND_RESOLVED';
  const reviewCases=cases.filter(c=>c.status==='REVIEW_REQUIRED'||c.status==='AWAITING_CLARIFICATION'||c.path==='IMMEDIATE_HUMAN_REVIEW');

  // Next recommended action banner
  function nextActionBanner(){
    if(!detail) return {cls:'idle',text:'Select a case from the queue to begin investigation.'};
    if(isSafety) return {cls:'safety',text:'SAFETY: Immediate human review required. AI cannot determine fault. Reviewer must independently assess.'};
    if(isClarifying) return {cls:'clarify',text:'CLARIFICATION: Awaiting party response. Monitor — do not impersonate the rider or driver.'};
    if(isReviewRequired) return {cls:'review',text:'REVIEW REQUIRED: Evaluate evidence, then finalize a decision in the Review Decision tab.'};
    if(isResolved) return {cls:'resolved',text:`RESOLVED: Case closed. ${detail.mock_action?`Disposition: ${dispositionLabel(detail.mock_action.disposition)}.`:''}`};
    if(detail.status==='NEW') return {cls:'idle',text:'NEW CASE: Click "Process" to run the evaluation pipeline.'};
    return {cls:'idle',text:'Process the case to generate the evaluation.'};
  }

  const banner=nextActionBanner();

  async function doProcess(){
    if(processing) return; // prevent duplicate
    setProcessing(true);
    try{
      const r=await api.call('cases/'+selected+'/process',{method:'POST'});
      setDetail(r);
      api.setNotice('Case processing complete.');
    }finally{setProcessing(false)}
  }

  async function doFinalize(){
    setShowConfirm(false);
    const p=await api.call('cases/'+selected+'/review',{method:'POST',body:{disposition:reviewDisposition,amount:Number(reviewAmount),reason:reviewReason,proposed_precedent:precedent||null}});
    setDetail(p);
    if(p.learning_proposal_id) setLearningId(p.learning_proposal_id);
    api.setNotice('Reviewer decision recorded. Simulated record generated — no real funds transferred.');
  }

  return <div className="reviewer-shell">
    {/* Top bar */}
    <div className="reviewer-top-bar">
      <div className="rtb-left">
        <div className="rtb-logo">Rv</div>
        <div><h1>RydeResolve <span>Reviewer</span></h1></div>
      </div>
      <div style={{display:'flex',alignItems:'center',gap:'12px'}}>
        {policy&&<span className="micro" style={{padding:0}}>{policy.ai_mode==='mock'?'Mock':'Live ADK'} · signoff: {policy.team_signoff_valid?'verified':'missing'}</span>}
        <div className="demo-label">DEMO</div>
        <Link href="/" className="lab-enter">← Exit</Link>
      </div>
    </div>

    {/* Connect */}
    {!policy&&<div className="card" style={{maxWidth:'500px',margin:'40px auto'}}>
      <h3 style={{marginTop:0}}>Reviewer access</h3>
      <p className="muted">Enter your reviewer demo passcode.</p>
      <div className="fieldgrid" style={{marginBottom:'12px'}}>
        <input aria-label="Demo passcode" type="password" placeholder="reviewer passcode" value={api.key} onChange={e=>api.setKey(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&api.key)api.run(connect)}}/>
        <button disabled={api.busy||!api.key} onClick={()=>api.run(connect)}>Connect</button>
      </div>
      {api.error&&<div className="alert error">{api.error}</div>}
    </div>}

    {policy&&<>
      {api.error&&<div className="alert error" role="alert">{api.error}</div>}
      {api.notice&&<div className="alert success">{api.notice}</div>}

      {reviewCases.length>0&&<div className="alert error" style={{display:'flex',alignItems:'center',gap:'10px'}}>
        <strong>{reviewCases.length} case{reviewCases.length>1?'s':''} need attention</strong>
        <span style={{fontSize:'12px'}}>{reviewCases.map(c=>c.case_id).join(', ')}</span>
      </div>}

      <div className="rw-workspace">
        {/* Sidebar — case queue */}
        <aside className="card sidebar rw-sidebar">
          <div className="section-head">
            <h2>Case queue</h2>
            <button className="small" disabled={api.busy} onClick={()=>api.run(async()=>{await api.call('cases/seed',{method:'POST'});const l=await api.call('cases');setCases(l);api.setNotice('Demo cases loaded.')})}>Load demos</button>
          </div>
          {cases.length===0?<p className="muted">No cases loaded.</p>:cases.map(item=>{
            const urgent=item.status==='REVIEW_REQUIRED'||item.path==='IMMEDIATE_HUMAN_REVIEW';
            return <button key={item.case_id} className={'case-item '+(selected===item.case_id?'selected':'')+(urgent?' urgent':'')} onClick={()=>api.run(()=>selectCase(item.case_id))}>
              <strong>{item.case_id}</strong>
              <span>{categoryLabel(item.category)}</span>
              <em className={'status '+(TONES[item.status]||'neutral')}>{statusLabel(item.status)}</em>
            </button>;
          })}
        </aside>

        {/* Center — investigation */}
        <div className="primary">
          {!detail?<div className="card empty"><div className="empty-symbol">⌁</div><h2>Select a case</h2><p>Choose a case from the queue to begin the investigation.</p></div>:
          <>
            {/* Next action banner */}
            <div className={'next-action-banner '+banner.cls} role="status">
              {banner.text}
            </div>

            {/* Case header */}
            <div className="card case-title" style={(isReviewRequired||isSafety)?{borderLeft:'4px solid var(--pink)'}:{}}>
              <div className="section-head">
                <div><p className="eyebrow">CASE {detail.case_id}</p><h2>{categoryLabel(detail.category)}</h2></div>
                <em className={'status '+(TONES[detail.status]||'neutral')}>{statusLabel(detail.status)}</em>
              </div>
              <p>{detail.description}</p>
              <div className="facts">
                <span>SGD {detail.dispute_amount!=null?Number(detail.dispute_amount).toFixed(2):'unknown'}</span>
                <span>Trip: {detail.trip_id||'—'}</span>
                <span>Filed by: {detail.filed_by||'—'}</span>
                <span>Policy: {detail.policy_version||'2.1'}</span>
                <span>Source: SYNTHETIC</span>
              </div>
              {!isResolved&&<button disabled={api.busy||processing} onClick={()=>api.run(doProcess)}>{processing?'Processing…':'Process / Re-evaluate'}</button>}
              {detail.mock_action&&<div className="receipt">
                <b>{dispositionLabel(detail.mock_action.disposition)}</b> · SGD {Number(detail.mock_action.amount||0).toFixed(2)}
                <br/><small>Simulated · No real funds transferred · Receipt: {detail.mock_action.receipt}</small>
              </div>}
            </div>

            {/* Tab bar */}
            <div className="tab-bar" role="tablist">
              {TABS.map(t=>{
                let badge=null;
                if(t.id==='evidence'&&detail.facts&&Object.keys(detail.facts).length>0) badge=<span className="tab-badge warn">{Object.keys(detail.facts).length}</span>;
                if(t.id==='agents'&&detail.agent_outputs) badge=<span className="tab-badge warn">{Object.keys(detail.agent_outputs).length}</span>;
                if(t.id==='decision'&&isReviewRequired) badge=<span className="tab-badge alert">!</span>;
                return <button key={t.id} role="tab" aria-selected={tab===t.id} className={tab===t.id?'active':''} onClick={()=>setTab(t.id)}>{t.label}{badge}</button>;
              })}
            </div>

            {/* Tab content */}
            {tab==='overview'&&<>
              {detail.path&&<div className="card result">
                <p className="eyebrow">DECISION PATH</p>
                <h2>{pathLabel(detail.path)}</h2>
                <p>{detail.candidate?.reason||'Awaiting evidence or human review.'}</p>
                {detail.gate?.reasons?.length>0&&<div style={{marginTop:'8px'}}><p className="muted">Policy rationale:</p><ul style={{fontSize:'12px',color:'var(--ink-secondary)',lineHeight:'1.6',paddingLeft:'18px'}}>{detail.gate.reasons.map((r,i)=><li key={i}>{r}</li>)}</ul></div>}
              </div>}

              {isSafety&&<div className="card highlight" style={{borderLeft:'4px solid var(--bad-fg)'}}>
                <p className="eyebrow">SAFETY ESCALATION</p>
                <h3>No AI fault or remedy ruling</h3>
                <p className="muted">AI does not determine fault or propose a remedy for safety incidents. Reviewer must independently assess per SF-5.1 and SF-5.2.</p>
              </div>}

              {detail.events?.length>0&&<div className="card">
                <p className="eyebrow">TIMELINE</p>
                <CaseTimeline detail={detail}/>
              </div>}

              {isClarifying&&detail.clarifications?.some(c=>c.status==='PENDING')&&<div className="card highlight">
                <p className="eyebrow">ACTIVE INVESTIGATION</p>
                <h3>Clarification in progress</h3>
                {detail.clarifications.filter(c=>c.status==='PENDING').map(c=>(
                  <div key={c.request_id} className="pkt-clar">
                    <span className="pkt-label">Asked: {c.recipient}</span>
                    <p>{c.question}</p>
                    <em className="status warn">Pending response</em>
                  </div>
                ))}
                {detail.clarifications.filter(c=>c.status==='ANSWERED').length>0&&<>
                  <h4 style={{marginTop:'12px'}}>Unverified replies</h4>
                  {detail.clarifications.filter(c=>c.status==='ANSWERED').map(c=>(
                    <div key={c.request_id} className="pkt-clar">
                      <span className="pkt-label">From: {c.recipient}</span>
                      <p>{c.answer}</p>
                      <em className="status bad">Unverified party account</em>
                    </div>
                  ))}
                </>}
              </div>}

              {detail.notifications&&detail.notifications.length>0&&<div className="card outbox">
                <p className="eyebrow">NOTIFICATION OUTBOX</p>
                <p className="muted">Simulated — not delivered.</p>
                <div className="notif-list">{detail.notifications.map((n,i)=>(
                  <div key={i} className="notif-item">
                    <div className="notif-head"><span className="notif-kind">{notifKindLabel(n.kind)}</span><span className="notif-recipient">To: {n.recipient}</span><em className="status bad">Not delivered</em></div>
                    <p className="notif-msg">{n.message}</p>
                  </div>
                ))}</div>
              </div>}
            </>}

            {tab==='evidence'&&<>
              <div className="card">
                <h3>Case facts</h3>
                <p className="muted">Claims are not automatically verified. Review provenance before relying on any fact.</p>
                <details><summary>Show case facts</summary><pre className="json">{JSON.stringify(detail.facts,null,2)}</pre></details>
              </div>
              <div className="card">
                <h3>Routing index</h3>
                <p className="muted">Candidate rules are not rulings.</p>
                {detail.routing?.candidate_rule_ids?.length?<div className="chips">{detail.routing.candidate_rule_ids.map(i=><span key={i}>{i}</span>)}</div>:<p className="muted">Process the case to retrieve routing IDs.</p>}
              </div>
              {!isResolved&&<div className="card">
                <p className="eyebrow">EVIDENCE UPLOAD</p>
                <h3>Upload image or evidence file</h3>
                <p className="muted">PNG, JPEG, or PDF up to 5 MB. Authenticity is unknown.</p>
                <input aria-label="Choose evidence document" type="file" accept="image/png,image/jpeg,application/pdf" onChange={e=>setUploadFile(e.target.files?.[0]||null)}/>
                <button disabled={api.busy||!uploadFile} onClick={()=>api.run(async()=>{const form=new FormData();form.append('file',uploadFile);const result=await api.call('cases/'+selected+'/files',{method:'POST',body:form});setUploadReport(result);setDetail(await api.call('cases/'+selected));api.setNotice('Evidence stored. Authenticity unverified.')})}>Upload evidence</button>
                {uploadReport&&<details><summary>Image analysis and storage</summary><pre className="json">{JSON.stringify(uploadReport,null,2)}</pre></details>}
              </div>}
              {!isResolved&&<div className="card">
                <h3>Add synthetic verified-source fact</h3>
                <p className="muted">Import a synthetic system fact with provenance. Party statements are never promoted to system facts.</p>
                <div className="fieldgrid">
                  <input value={field} onChange={e=>setField(e.target.value)} placeholder="Field name"/>
                  <input value={factValue} onChange={e=>setFactValue(e.target.value)} placeholder="JSON value"/>
                  <input value={provenance} onChange={e=>setProvenance(e.target.value)} placeholder="Source description"/>
                </div>
                <button disabled={api.busy||!field} onClick={()=>api.run(async()=>{let value;try{value=JSON.parse(factValue)}catch{value=factValue}const p=await api.call('cases/'+selected+'/evidence',{method:'POST',body:{field,value,provenance}});setDetail(p);api.setNotice('Evidence added. Re-evaluate to see updated assessment.')})}>Attach fact</button>
              </div>}
            </>}

            {tab==='agents'&&<>
              {detail.agent_outputs?<div className="card">
                <h3>Advocate and Judge findings</h3>
                <p className="muted">Visible results and traces — not private model chain of thought.</p>
                <div className="agents">{Object.entries(detail.agent_outputs).map(([n,v])=><div key={n} className="agent"><b>{n}</b><p>{v.summary}</p><small>Rules: {(v.policy_rule_ids||[]).join(', ')||'—'}</small>{v.mode&&<small> · {v.mode}</small>}</div>)}</div>
                <details><summary>Technical trace (events)</summary><pre className="json">{JSON.stringify(detail.agent_trace,null,2)}</pre></details>
              </div>:<div className="card empty"><div className="empty-symbol">🤖</div><h2>No agent outputs</h2><p>Process the case to run the ADK agents.</p></div>}
            </>}

            {tab==='decision'&&<>
              {isReviewRequired?<>
                <div className="card highlight">
                  <p className="eyebrow">HUMAN REVIEW REQUIRED</p>
                  <h3>Authorized simulated reviewer decision</h3>
                  <div className="fieldgrid">
                    <select value={reviewDisposition} onChange={e=>setReviewDisposition(e.target.value)}>{REVIEW_DISPOSITIONS.map(d=><option key={d.value} value={d.value}>{d.label}</option>)}</select>
                    <input type="number" min="0" step="0.01" value={reviewAmount} onChange={e=>setReviewAmount(e.target.value)} placeholder="SGD amount"/>
                  </div>
                  <textarea value={reviewReason} onChange={e=>setReviewReason(e.target.value)} placeholder="Write justification based on evidence and policy (10+ characters)"/>
                  <textarea value={precedent} onChange={e=>setPrecedent(e.target.value)} placeholder="Optional staged precedent for Innovation B"/>
                  <button disabled={api.busy||reviewReason.length<10} onClick={()=>setShowConfirm(true)}>Review decision before finalizing</button>
                </div>
                <div className="card packet">
                  <p className="eyebrow">DECISION PACKET</p>
                  <button className="small" disabled={api.busy} onClick={()=>api.run(async()=>{const p=await api.call('cases/'+selected+'/review-packet');setPacket(p);api.setNotice('Decision packet assembled.')})}>Generate decision packet</button>
                  {packet&&packet.case_details?.case_id===selected&&<>
                    <div className="packet-section"><h4>Case details</h4><div className="packet-grid">
                      <div><span className="pkt-label">Filed by</span><span className="pkt-val">{packet.case_details.filed_by}</span></div>
                      <div><span className="pkt-label">Category</span><span className="pkt-val">{categoryLabel(packet.case_details.category)}</span></div>
                      <div><span className="pkt-label">Status</span><span className="pkt-val">{statusLabel(packet.case_details.status)}</span></div>
                      <div><span className="pkt-label">Dispute</span><span className="pkt-val">SGD {packet.case_details.dispute_value!=null?Number(packet.case_details.dispute_value).toFixed(2):'—'}</span></div>
                    </div></div>
                    <div className="packet-section"><h4>Structured facts</h4>
                      {packet.structured_facts?.length>0?<table className="pkt-table"><thead><tr><th>Field</th><th>Value</th><th>Provenance</th><th>Verification</th></tr></thead><tbody>{packet.structured_facts.map((f,i)=><tr key={i}><td>{f.field}</td><td>{String(f.value)}</td><td>{f.provenance}</td><td>{f.verification}</td></tr>)}</tbody></table>:<p className="muted">None</p>}
                    </div>
                    <div className="packet-section"><h4>Gaps</h4>{packet.gaps?.length>0?<ul>{packet.gaps.map((g,i)=><li key={i}>{g}</li>)}</ul>:<p className="muted">None</p>}</div>
                    <div className="packet-section"><h4>Contradictions</h4>{packet.contradictions?.length>0?<ul>{packet.contradictions.map((c,i)=><li key={i}>{c}</li>)}</ul>:<p className="muted">None</p>}</div>
                    <div className="packet-section"><h4>Clarification history</h4>{packet.clarification_history?.length>0?packet.clarification_history.map((c,i)=><div key={i} className="pkt-clar"><span className="pkt-label">To {c.recipient}</span><span className="pkt-val">{c.question}</span><em className={'status '+(c.status==='PENDING'?'warn':'neutral')}>{c.status}</em></div>):<p className="muted">None</p>}</div>
                    <div className="packet-section"><h4>Advocate summaries</h4>{packet.advocate_summaries&&Object.entries(packet.advocate_summaries).map(([role,sum])=><div key={role} className="pkt-adv"><b>{role}</b><p>{sum.summary}</p><small>Rec: {dispositionLabel(sum.recommended_disposition)} · {sum.mode}</small></div>)}</div>
                    {packet.is_safety?<div className="packet-section pkt-safety"><h4>Safety — no AI fault or remedy</h4><p>{packet.safety_note||'AI does not determine fault.'}</p></div>:<div className="packet-section pkt-proposal"><h4>Non-safety — proposal only</h4><p>AI recommendation is a proposal. Reviewer decides.</p></div>}
                    <div className="packet-section"><h4>AI recommendation</h4>
                      <div className="pkt-rec"><div><span className="pkt-label">Recommendation</span><span className="pkt-val">{dispositionLabel(packet.ai_recommendation.disposition)}</span></div><div><span className="pkt-label">Amount</span><span className="pkt-val">SGD {Number(packet.ai_recommendation.amount||0).toFixed(2)}</span></div></div>
                    </div>
                    {packet.human_decision&&<div className="packet-section pkt-decision"><h4>Human decision</h4>
                      <div className="pkt-rec"><div><span className="pkt-label">Disposition</span><span className="pkt-val">{dispositionLabel(packet.human_decision.disposition)}</span></div><div><span className="pkt-label">Amount</span><span className="pkt-val">SGD {Number(packet.human_decision.amount||0).toFixed(2)}</span></div><div><span className="pkt-label">Reason</span><span className="pkt-val">{packet.human_decision.reason}</span></div></div>
                      <p className="muted" style={{marginTop:'6px'}}>Simulated — no real funds transferred.</p>
                    </div>}
                    <div className="packet-section pkt-warning"><h4>Synthetic demo warning</h4><p>{packet.synthetic_warning}</p></div>
                  </>}
                </div>
              </>:<div className="card empty"><div className="empty-symbol">✅</div><h2>No decision needed</h2><p>This case is {isResolved?'already resolved':isSafety?'a safety escalation — use the Overview tab':'not in REVIEW_REQUIRED state'}.</p></div>}
            </>}

            {tab==='audit'&&<>
              <div className="card">
                <p className="eyebrow">GOVERNED LEARNING</p>
                <h3>Test before release</h3>
                <div className="fieldgrid">
                  <input value={learningId} onChange={e=>setLearningId(e.target.value)} placeholder="Learning proposal ID"/>
                  <button disabled={api.busy||!learningId} onClick={()=>api.run(async()=>{const p=await api.call('learning/'+learningId+'/evaluate',{method:'POST'});api.setNotice(`${p.evaluation.regression.passed}/${p.evaluation.regression.total} checks passed.`);await loadLearning()})}>Run regression</button>
                  <button disabled={api.busy||!learningId} onClick={()=>api.run(async()=>{await api.call('learning/'+learningId+'/approve',{method:'POST',body:{rationale:'Approved after review'}});api.setNotice('Precedent published.');await loadLearning()})}>Approve</button>
                </div>
                <div className="fieldgrid" style={{marginTop:'8px'}}>
                  <input aria-label="Rollback reason" value={rollbackReason} onChange={e=>setRollbackReason(e.target.value)} placeholder="Rollback reason (10+ chars)"/>
                  <button disabled={api.busy||!learningId||rollbackReason.trim().length<10} onClick={()=>api.run(async()=>{await api.call('learning/'+learningId+'/rollback',{method:'POST',body:{rationale:rollbackReason}});api.setNotice('Rolled back.');await loadLearning()})}>Rollback</button>
                </div>
                <button className="small" disabled={api.busy} style={{marginTop:'8px'}} onClick={()=>api.run(async()=>{setReport(await api.call('evaluation/reference'));await loadLearning()})}>Show evaluation report</button>
                {report&&<p><b>{report.passed}/{report.total}</b> regression cases passed.</p>}
                {learning.length>0&&<details><summary>Learning proposals</summary><pre className="json">{JSON.stringify(learning,null,2)}</pre></details>}
              </div>
              <div className="card">
                <h3>Audit verification</h3>
                <p className="muted">Case events are hash-linked for tamper detection.</p>
                <button className="small" disabled={api.busy} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+selected+'/verify-audit');setAuditResult(r);api.setNotice(r.valid?'Audit verified.':'Audit broken.')})}>Verify audit integrity</button>
                {auditResult&&<p><b>Chain valid: {String(auditResult.valid)}</b></p>}
                <details><summary>Event record</summary><pre className="json">{JSON.stringify(detail.events,null,2)}</pre></details>
                <details><summary>Complete case document</summary><pre className="json">{JSON.stringify(detail,null,2)}</pre></details>
              </div>
            </>}
          </>}
        </div>
      </div>
    </>}

    {/* Confirmation dialog for human decision */}
    {showConfirm&&<div className="confirm-overlay" role="dialog" aria-modal="true" onClick={()=>setShowConfirm(false)}>
      <div className="confirm-dialog" onClick={e=>e.stopPropagation()}>
        <h3>Confirm reviewer decision</h3>
        <p className="muted" style={{marginBottom:'12px'}}>This will finalize the decision for {selected}. A simulated record will be generated — no real funds transferred.</p>
        <div className="confirm-summary">
          <div className="confirm-row"><span className="muted">Disposition</span><b>{dispositionLabel(reviewDisposition)}</b></div>
          <div className="confirm-row"><span className="muted">Amount</span><b>SGD {Number(reviewAmount||0).toFixed(2)}</b></div>
          <div className="confirm-row"><span className="muted">Reason</span><b>{reviewReason}</b></div>
          {precedent&&<div className="confirm-row"><span className="muted">Precedent</span><b>{precedent}</b></div>}
        </div>
        <p className="muted" style={{fontSize:'11px'}}>Backend validation will enforce minimum reason length and policy compliance.</p>
        <div className="confirm-actions">
          <button className="secondary" onClick={()=>setShowConfirm(false)}>Cancel</button>
          <button disabled={api.busy} onClick={()=>api.run(doFinalize)}>{api.busy?'Finalizing…':'Confirm decision'}</button>
        </div>
      </div>
    </div>}

    <div className="demo-badge">SYNTHETIC DEMO</div>
  </div>;
}
