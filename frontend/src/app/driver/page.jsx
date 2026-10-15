'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';

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

  return <main>
    <header className="masthead">
      <div className="brand">
        <div className="brand-icon" style={{background:'linear-gradient(135deg,#0e8f87,#2dbfa8)'}}>D</div>
        <div><h1>RydeResolve <span>Driver</span></h1><p>Evidence, requests, and compensation status</p></div>
      </div>
      <div className="demo-label">HACKATHON DEMO · NO REAL PAYMENTS</div>
    </header>

    <section className="card connection">
      <div>
        <h2>Driver access</h2>
        <p>Enter your driver demo passcode from backend/.env. This is demo-only access, not production identity. The demo API is not user-isolated; role filtering in UI does not ensure real privacy.</p>
      </div>
      <input aria-label="Demo passcode" type="password" placeholder="driver passcode" value={api.key} onChange={e=>api.setKey(e.target.value)}/>
      <button disabled={api.busy||!api.key} onClick={()=>api.run(connect)}>Connect</button>
    </section>

    {api.error&&<div className="alert error" role="alert">{api.error}</div>}
    {api.notice&&<div className="alert success">{api.notice}</div>}

    {policy&&<div className="micro">Backend: {policy.ai_mode==='mock'?'MOCK MODE (no model calls)':'LIVE ADK'} · Policy signoff: {policy.team_signoff_valid?'verified':'missing'} · {policy.storage_mode}</div>}

    <div className="workspace">
      <aside className="card sidebar">
        <div className="section-head"><h2>Synthetic demo cases</h2></div>
        {cases.length===0?<p className="muted">Enter passcode and click Connect.</p>:cases.map(item=>(
          <button key={item.case_id} className={'case-item '+(detail?.case_id===item.case_id?'selected':'')} onClick={()=>api.run(()=>selectCase(item.case_id))}>
            <strong>{item.case_id}</strong>
            <span>{item.category.replaceAll('_',' ')}</span>
            <em className={'status '+(tones[item.status]||'neutral')}>{item.status.replaceAll('_',' ')}</em>
          </button>
        ))}
      </aside>

      <div className="primary">
        {!detail?<div className="card empty"><div className="empty-symbol">⌁</div><h2>Select a case</h2><p>View evidence history, respond to pending requests, and check compensation.</p></div>:
        <>
          <div className="card case-title">
            <div className="section-head"><div><p className="eyebrow">CASE {detail.case_id}</p><h2>{detail.category.replaceAll('_',' ')}</h2></div><em className={'status '+(tones[detail.status]||'neutral')}>{detail.status}</em></div>
            <p>{detail.description}</p>
            <div className="facts"><span>Disputed: SGD {detail.dispute_amount??'unknown'}</span><span>Filed by: {detail.filed_by}</span></div>
          </div>

          {detail.path&&<div className="card result">
            <p className="eyebrow">CURRENT STATUS</p>
            <h2>{detail.path.replaceAll('_',' ')}</h2>
            <p>{detail.candidate?.reason||'Awaiting processing.'}</p>
            {detail.mock_action&&<div className="receipt"><b>{detail.mock_action.status}</b> · {detail.mock_action.disposition} SGD {detail.mock_action.amount}</div>}
          </div>}

          {detail.path==='IMMEDIATE_HUMAN_REVIEW'&&<div className="card highlight" style={{borderLeft:'5px solid #ad3140'}}>
            <p className="eyebrow">⚠ IMMEDIATE HUMAN REVIEW</p>
            <h3>Safety case — no automated decision</h3>
            <p className="muted">This trip has been escalated for mandatory human review. AI does not determine fault or propose a remedy. A reviewer will investigate and contact you through official channels if needed.</p>
          </div>}

          {detail.clarifications?.some(c=>c.status==='PENDING'&&c.recipient==='driver')&&(
            <div className="card highlight">
              <p className="eyebrow">PENDING REQUEST</p>
              <h3>Clarification requested from you</h3>
              <p className="muted">⚠ Do not reply while driving. Pull over safely before responding.</p>
              {detail.clarifications.filter(c=>c.status==='PENDING'&&c.recipient==='driver').map(c=>(
                <div key={c.request_id}>
                  <p>{c.question}</p>
                  <em className="status bad">UNVERIFIED_PARTY_ACCOUNT</em>
                  <textarea placeholder="Your response..." value={answer} onChange={e=>setAnswer(e.target.value)}/>
                  <button disabled={api.busy||!answer.trim()} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id+'/clarifications/'+c.request_id+'/reply',{method:'POST',body:{answer}});setDetail(r);setAnswer('');api.setNotice('Response stored as unverified claim. The reviewer may request source documentation.')})}>Submit response</button>
                </div>
              ))}
              <p className="muted">Your answer alone is not verified evidence — the reviewer may request source documentation.</p>
            </div>
          )}

          {detail.notifications&&detail.notifications.length>0&&(
            <div className="card outbox">
              <p className="eyebrow">OUTCOME NOTIFICATIONS</p>
              <h3>Simulated outbox — NOT DELIVERED</h3>
              <p className="muted">All entries are explicitly simulated. No email, SMS, push, or payment was sent. The demo API is not user-isolated; role filtering in UI does not ensure real privacy.</p>
              <div className="notif-list">{detail.notifications.filter(n=>n.recipient==='driver'||n.recipient==='all').map((n,i)=>(
                <div key={i} className="notif-item">
                  <div className="notif-head"><span className="notif-kind">{n.kind.replaceAll('_',' ')}</span><em className="status bad">NOT DELIVERED</em></div>
                  <p className="notif-msg">{n.message}</p>
                  <div className="notif-meta"><span>{n.created_at}</span>{n.receipt&&<span>Receipt: {n.receipt}</span>}</div>
                </div>
              ))}</div>
            </div>
          )}

          <div className="card">
            <h3>Outcome explanation</h3>
            <p className="muted">This is a synthetic demo. No real money was moved. Disposition meanings:</p>
            <ul style={{fontSize:'12px',color:'#3d516c',lineHeight:'1.8',paddingLeft:'18px'}}>
              <li><b>refund</b> — simulated SGD credit back to the rider's demo account. Not a real payment.</li>
              <li><b>credit</b> — simulated SGD credit to the rider's demo wallet. Not a real payment.</li>
              <li><b>no_action</b> — no monetary transfer. The disputed amount was not moved.</li>
              <li><b>reject_claim</b> — claim rejected. No refund, credit, or transfer.</li>
              <li><b>undetermined / pending review</b> — no automated outcome. A human reviewer must decide.</li>
            </ul>
          </div>

          <div className="card">
            <h3>Evidence and facts</h3>
            <p className="muted">Claims are not automatically verified; review evidence sources.</p>
            <details><summary>Show facts</summary><pre className="json">{JSON.stringify(detail.facts,null,2)}</pre></details>
            <details><summary>Show event record</summary><pre className="json">{JSON.stringify(detail.events,null,2)}</pre></details>
          </div>
        </>}
      </div>
    </div>

    <div className="card" style={{textAlign:'center',padding:'16px'}}>
      <Link href="/" className="lab-enter">← Back to role selection</Link>
      <span style={{margin:'0 12px',color:'#ccc'}}>·</span>
      <Link href="/lab" className="lab-enter">Full dashboard →</Link>
    </div>

    <footer>RydeResolve is a synthetic hackathon prototype. No real payments or notifications were sent.</footer>
  </main>;
}

const tones={RESOLVED:'good',REVIEWED_AND_RESOLVED:'good',AWAITING_CLARIFICATION:'warn',REVIEW_REQUIRED:'bad',NEW:'neutral'};
