'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {CaseTimeline} from '../../lib/Timeline';
import {
  TONES, statusLabel, pathLabel, categoryLabel, dispositionLabel, notifKindLabel,
  outcomeExplanation, driverNextAction,
} from '../../lib/labels';

const NAV_TABS = [
  {id:'disputes',label:'Disputes',icon:'🚗'},
  {id:'account',label:'Account',icon:'⚙'},
];

export default function DriverPortal(){
  const api=useApi();
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [tab,setTab]=useState('disputes');
  const [answer,setAnswer]=useState('');

  async function connect(){
    await api.call('health');
    const list=await api.call('cases');
    setCases(list);
  }

  async function selectCase(id){
    setDetail(await api.call('cases/'+id));
  }

  const outcome=outcomeExplanation(detail);
  const pendingClarifications=detail?.clarifications?.filter(c=>c.status==='PENDING'&&c.recipient==='driver')||[];
  const actionNeededCases=cases.filter(c=>c.status==='AWAITING_CLARIFICATION');
  const activeCases=cases.filter(c=>c.status!=='RESOLVED'&&c.status!=='REVIEWED_AND_RESOLVED');

  // --- Not connected ---
  if(!api.key||!cases.length){
    return <div className="app-shell">
      <div className="app-connect driver">
        <div className="app-logo-big">D</div>
        <h2>RydeResolve Driver</h2>
        <p>Enter your demo passcode to view disputes involving your trips. Case isolation is enforced — you can only see your own cases.</p>
        <input aria-label="Demo passcode" type="password" placeholder="Enter passcode" value={api.key} onChange={e=>api.setKey(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&api.key)api.run(connect)}}/>
        <button disabled={api.busy||!api.key} onClick={()=>api.run(connect)}>{api.busy?'Connecting…':'Connect'}</button>
      </div>
      {api.error&&<div className="alert error" role="alert" style={{margin:'0 16px'}}>{api.error}</div>}
      <div style={{textAlign:'center',padding:'16px'}}>
        <Link href="/" className="lab-enter">← Back to role selection</Link>
      </div>
      <div className="demo-badge">SYNTHETIC DEMO</div>
    </div>;
  }

  return <div className="app-shell">
    <header className="app-header">
      <div className="app-logo driver">D</div>
      <div style={{flex:1}}>
        <h1>RydeResolve <span>Driver</span></h1>
        <p className="app-sub">{activeCases.length} active case{activeCases.length!==1?'s':''}{actionNeededCases.length>0?` · ${actionNeededCases.length} need response`:''}</p>
      </div>
    </header>

    {api.error&&<div className="alert error" role="alert" style={{margin:'0 12px'}}>{api.error}</div>}
    {api.notice&&<div className="alert success" style={{margin:'0 12px'}}>{api.notice}</div>}

    <div className="app-body">
      {tab==='disputes'&&!detail&&<>
        {/* Action Needed section */}
        {actionNeededCases.length>0&&<>
          <div className="app-section-head"><h2 style={{color:'var(--bad-fg)'}}>Action needed</h2></div>
          <p className="muted" style={{margin:'0 0 12px'}}>You have pending clarification requests. Pull over safely before responding.</p>
          {actionNeededCases.map(item=>(
            <div key={item.case_id} className="app-case-card urgent" onClick={()=>api.run(()=>selectCase(item.case_id))} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==='Enter')api.run(()=>selectCase(item.case_id))}}>
              <div className="acc-top">
                <strong>{item.case_id}</strong>
                <em className="status bad">Response needed</em>
              </div>
              <div className="acc-cat">{categoryLabel(item.category)}</div>
            </div>
          ))}
        </>}

        {/* All cases */}
        <div className="app-section-head"><h2>Your disputes</h2></div>
        {cases.length===0?
          <div className="card empty" style={{padding:'40px 16px'}}><div className="empty-symbol">🚗</div><h2>No disputes</h2><p>No cases involving you at this time.</p></div>
        :cases.map(item=>(
          <div key={item.case_id} className={'app-case-card '+(detail?.case_id===item.case_id?'selected':'')} onClick={()=>api.run(()=>selectCase(item.case_id))} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==='Enter')api.run(()=>selectCase(item.case_id))}}>
            <div className="acc-top">
              <strong>{item.case_id}</strong>
              <em className={'status '+(TONES[item.status]||'neutral')}>{statusLabel(item.status)}</em>
            </div>
            <div className="acc-cat">{categoryLabel(item.category)}</div>
            {item.dispute_amount!=null&&<div className="acc-cat">SGD {Number(item.dispute_amount).toFixed(2)}</div>}
          </div>
        ))}
      </>}

      {tab==='disputes'&&detail&&<>
        <div className="app-section-head">
          <button className="secondary" onClick={()=>setDetail(null)}>← Back</button>
          <button disabled={api.busy} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id);setDetail(r);api.setNotice('Status refreshed.')})}>Refresh</button>
        </div>

        {/* Status hero */}
        <div className="app-status-hero">
          <div className="ash-icon">{detail.path==='IMMEDIATE_HUMAN_REVIEW'?'🛡':detail.status==='RESOLVED'||detail.status==='REVIEWED_AND_RESOLVED'?'✅':detail.status==='AWAITING_CLARIFICATION'?'❓':'⏳'}</div>
          <h2>{detail.path?pathLabel(detail.path):statusLabel(detail.status)}</h2>
          <p>{detail.candidate?.reason||driverNextAction(detail)}</p>
          <em className={'status '+(TONES[detail.status]||'neutral')}>{statusLabel(detail.status)}</em>
        </div>

        {/* Case info */}
        <div className="card">
          <div className="acc-top"><strong>{detail.case_id}</strong></div>
          <div className="acc-cat">{categoryLabel(detail.category)}</div>
          <p style={{fontSize:'13px',color:'var(--ink-secondary)',lineHeight:'1.6',margin:'8px 0'}}>{detail.description}</p>
          <div className="facts">
            <span>SGD {detail.dispute_amount!=null?Number(detail.dispute_amount).toFixed(2):'—'}</span>
            <span>Trip: {detail.trip_id||'—'}</span>
            <span>Filed by: {detail.filed_by||'—'}</span>
          </div>
        </div>

        {/* Safety */}
        {detail.path==='IMMEDIATE_HUMAN_REVIEW'&&<div className="app-action-card" style={{background:'var(--bad-bg)',borderColor:'var(--bad-border)'}}>
          <h3 style={{color:'var(--bad-fg)'}}>Safety escalation</h3>
          <p style={{color:'var(--bad-fg)'}}>This trip has been escalated for mandatory human review. AI does not determine fault or propose a remedy. A reviewer will investigate.</p>
        </div>}

        {/* Action needed — clarification */}
        {pendingClarifications.length>0&&<div className="app-action-card">
          <h3>Action needed</h3>
          <p>Do not reply while driving. Pull over safely first. Your response will be recorded as an unverified claim.</p>
          {pendingClarifications.map(c=>(
            <div key={c.request_id} style={{marginBottom:'16px'}}>
              <div className="clar-q">{c.question}</div>
              <em className="status bad" style={{marginBottom:'8px',display:'inline-block'}}>Your statement — unverified</em>
              <textarea placeholder="Type your response here…" value={answer} onChange={e=>setAnswer(e.target.value)}/>
              <button disabled={api.busy||!answer.trim()} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id+'/clarifications/'+c.request_id+'/reply',{method:'POST',body:{answer}});setDetail(r);setAnswer('');api.setNotice('Response recorded as unverified claim.')})}>{api.busy?'Sending…':'Submit response'}</button>
            </div>
          ))}
        </div>}

        {/* Outcome */}
        {detail.mock_action&&<div className="app-receipt">
          <b>{dispositionLabel(detail.mock_action.disposition)}</b> · SGD {Number(detail.mock_action.amount||0).toFixed(2)}
          <br/><small>Simulated record · No real funds transferred · Receipt: {detail.mock_action.receipt}</small>
        </div>}

        {outcome&&<div className="card">
          <p className="eyebrow">OUTCOME</p>
          <p style={{fontSize:'13px',color:'var(--ink-secondary)',lineHeight:'1.6'}}>{outcome}</p>
          <p className="muted" style={{marginTop:'8px'}}>{driverNextAction(detail)}</p>
        </div>}

        {/* Timeline */}
        <div className="card">
          <p className="eyebrow">CASE PROGRESS</p>
          <CaseTimeline detail={detail} role="driver"/>
        </div>

        {/* Notifications */}
        {detail.notifications&&detail.notifications.length>0&&<div className="card">
          <p className="eyebrow">UPDATES</p>
          <p className="muted">Simulated — not delivered.</p>
          <div className="notif-list">{detail.notifications.filter(n=>n.recipient==='driver'||n.recipient==='all').map((n,i)=>(
            <div key={i} className="notif-item">
              <div className="notif-head"><span className="notif-kind">{notifKindLabel(n.kind)}</span><em className="status bad">Not delivered</em></div>
              <p className="notif-msg">{n.message}</p>
            </div>
          ))}</div>
        </div>}
      </>}

      {tab==='account'&&<>
        <div className="app-section-head"><h2>Account</h2></div>
        <div className="card">
          <h3 style={{margin:'0 0 8px'}}>Demo session</h3>
          <p className="muted">Connected as Driver. Case isolation enforced — you can only see your own cases.</p>
        </div>
        <div className="card">
          <h3 style={{margin:'0 0 8px'}}>About this demo</h3>
          <p className="muted">RydeResolve is a synthetic demo. No real payments, notifications, or account actions were executed.</p>
        </div>
        <div className="card" style={{textAlign:'center'}}>
          <Link href="/" className="lab-enter">← Back to role selection</Link>
        </div>
      </>}
    </div>

    <nav className="app-nav" role="navigation" aria-label="Main navigation">
      {NAV_TABS.map(t=><button key={t.id} className={tab===t.id?'active':''} onClick={()=>{setTab(t.id);setDetail(null)}} aria-label={t.label}>
        <span className="nav-icon">{t.icon}</span>
        {t.label}
      </button>)}
    </nav>

    <div className="demo-badge">SYNTHETIC DEMO</div>
  </div>;
}
