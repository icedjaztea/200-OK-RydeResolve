'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {CaseTimeline} from '../../lib/Timeline';
import {
  TONES, statusLabel, pathLabel, categoryLabel, dispositionLabel, notifKindLabel,
  outcomeExplanation, driverNextAction,
} from '../../lib/labels';

export default function DriverPortal(){
  const api=useApi();
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [policy,setPolicy]=useState(null);
  const [answer,setAnswer]=useState('');

  async function connect(){
    setPolicy(await api.call('health'));
    const list=await api.call('cases');
    setCases(list);
  }

  async function selectCase(id){
    setDetail(await api.call('cases/'+id));
  }

  const outcome=outcomeExplanation(detail);

  return <main>
    <header className="masthead">
      <div className="brand">
        <div className="brand-icon" style={{background:'linear-gradient(135deg,#c91f56,#e8336a)'}}>D</div>
        <div><h1>RydeResolve <span>Driver</span></h1><p>View cases, respond to requests, and check outcomes</p></div>
      </div>
      <div className="demo-label">DEMO · SYNTHETIC DATA</div>
    </header>

    <section className="card connection">
      <div>
        <h2>Driver access</h2>
        <p>Enter your demo passcode. The backend enforces case isolation per authenticated identity — you can only see cases involving you.</p>
      </div>
      <input aria-label="Demo passcode" type="password" placeholder="driver passcode" value={api.key} onChange={e=>api.setKey(e.target.value)}/>
      <button disabled={api.busy||!api.key} onClick={()=>api.run(connect)}>Connect</button>
    </section>

    {api.error&&<div className="alert error" role="alert">{api.error}</div>}
    {api.notice&&<div className="alert success">{api.notice}</div>}

    {policy&&<div className="micro">{policy.ai_mode==='mock'?'Mock mode (no model calls)':'Live ADK'} · Policy signoff: {policy.team_signoff_valid?'verified':'missing'} · Storage: {policy.storage_mode}</div>}

    <div className="workspace">
      <aside className="card sidebar">
        <div className="section-head"><h2>Your cases</h2></div>
        {cases.length===0?
          <p className="muted">{api.key?'No cases loaded.':'Enter passcode and click Connect.'}</p>
        :cases.map(item=>(
          <button key={item.case_id} className={'case-item '+(detail?.case_id===item.case_id?'selected':'')} onClick={()=>api.run(()=>selectCase(item.case_id))}>
            <strong>{item.case_id}</strong>
            <span>{categoryLabel(item.category)}</span>
            <em className={'status '+(TONES[item.status]||'neutral')}>{statusLabel(item.status)}</em>
          </button>
        ))}
      </aside>

      <div className="primary">
        {!detail?<div className="card empty"><div className="empty-symbol">⌁</div><h2>Select a case</h2><p>View case history, respond to pending requests, and check outcomes.</p></div>:
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
            </div>
            <button disabled={api.busy||!api.key} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id);setDetail(r);api.setNotice('Case status refreshed.')})}>Refresh status</button>
          </div>

          {detail.path&&<div className="card result">
            <p className="eyebrow">CURRENT STATUS</p>
            <h2>{pathLabel(detail.path)}</h2>
            <p>{detail.candidate?.reason||driverNextAction(detail)}</p>
            {detail.gate?.reasons?.length>0&&<div style={{marginTop:'8px'}}><p className="muted" style={{marginBottom:'4px'}}>Policy rationale:</p><ul style={{fontSize:'12px',color:'var(--ink-secondary)',lineHeight:'1.6',paddingLeft:'18px'}}>{detail.gate.reasons.map((r,i)=><li key={i}>{r}</li>)}</ul></div>}
            {detail.mock_action&&<div className="receipt">
              <b>{dispositionLabel(detail.mock_action.disposition)}</b> · SGD {Number(detail.mock_action.amount||0).toFixed(2)}
              <br/><small style={{color:'var(--good-fg)'}}>Simulated record · No real funds transferred · Receipt: {detail.mock_action.receipt}</small>
            </div>}
          </div>}

          {detail.events?.length>0&&<div className="card">
            <p className="eyebrow">CASE ACTIVITY</p>
            <h3>Timeline</h3>
            <CaseTimeline detail={detail} role="driver"/>
          </div>}

          {detail.path==='IMMEDIATE_HUMAN_REVIEW'&&<div className="card highlight" style={{borderLeft:'4px solid var(--bad-fg)'}}>
            <p className="eyebrow">SAFETY ESCALATION</p>
            <h3>This case requires immediate human review</h3>
            <p className="muted">This trip has been escalated for mandatory human review. AI does not determine fault or propose a remedy. A reviewer will investigate and contact you through official channels if needed. No automated decision has been made.</p>
          </div>}

          {detail.clarifications?.some(c=>c.status==='PENDING'&&c.recipient==='driver')&&(
            <div className="card highlight">
              <p className="eyebrow">CLARIFICATION REQUESTED</p>
              <h3>The reviewer needs more information from you</h3>
              <p className="muted">Do not reply while driving. Pull over safely before responding. Your response will be recorded as an unverified claim — the reviewer may request source documentation to verify it.</p>
              {detail.clarifications.filter(c=>c.status==='PENDING'&&c.recipient==='driver').map(c=>(
                <div key={c.request_id} style={{marginTop:'12px'}}>
                  <p style={{fontWeight:500}}>{c.question}</p>
                  <em className="status bad">Your account statement — unverified</em>
                  <textarea placeholder="Type your response here…" value={answer} onChange={e=>setAnswer(e.target.value)} style={{marginTop:'8px'}}/>
                  <button disabled={api.busy||!answer.trim()} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id+'/clarifications/'+c.request_id+'/reply',{method:'POST',body:{answer}});setDetail(r);setAnswer('');api.setNotice('Your response has been recorded as an unverified claim.')})}>Submit response</button>
                </div>
              ))}
            </div>
          )}

          {detail.notifications&&detail.notifications.length>0&&(
            <div className="card outbox">
              <p className="eyebrow">CASE UPDATES</p>
              <h3>Simulated notifications — not delivered</h3>
              <p className="muted">No email, SMS, push notification, or payment was sent.</p>
              <div className="notif-list">{detail.notifications.filter(n=>n.recipient==='driver'||n.recipient==='all').map((n,i)=>(
                <div key={i} className="notif-item">
                  <div className="notif-head"><span className="notif-kind">{notifKindLabel(n.kind)}</span><em className="status bad">Not delivered</em></div>
                  <p className="notif-msg">{n.message}</p>
                  <div className="notif-meta"><span>{n.created_at}</span>{n.receipt&&<span>Test receipt: {n.receipt}</span>}</div>
                </div>
              ))}</div>
            </div>
          )}

          {outcome&&<div className="card">
            <p className="eyebrow">OUTCOME</p>
            <h3>Case outcome</h3>
            <p style={{fontSize:'13px',lineHeight:'1.6',color:'var(--ink-secondary)'}}>{outcome}</p>
            <p className="muted" style={{marginTop:'8px'}}>{driverNextAction(detail)}</p>
          </div>}

          <div className="card">
            <h3>Evidence and case details</h3>
            <p className="muted">Claims are not automatically verified. The reviewer may add verified evidence.</p>
            <details><summary>Show case facts</summary><pre className="json">{JSON.stringify(detail.facts,null,2)}</pre></details>
            <details><summary>Show event record</summary><pre className="json">{JSON.stringify(detail.events,null,2)}</pre></details>
          </div>
        </>}
      </div>
    </div>

    <div className="card" style={{textAlign:'center',padding:'16px'}}>
      <Link href="/" className="lab-enter">← Back to role selection</Link>
      <span style={{margin:'0 12px',color:'var(--ink-faint)'}}>·</span>
      <Link href="/lab" className="lab-enter">Full dashboard →</Link>
    </div>

    <footer>RydeResolve is a synthetic demo. No real payments, notifications, or account actions were executed.</footer>
  </main>;
}
