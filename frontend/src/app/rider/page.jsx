'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {CaseTimeline} from '../../lib/Timeline';
import {
  TONES, statusLabel, pathLabel, categoryLabel, dispositionLabel, notifKindLabel,
  outcomeExplanation, riderNextAction,
} from '../../lib/labels';

const CATEGORIES = [
  {value:'fare_dispute',label:'Fare dispute'},
  {value:'route_deviation',label:'Route deviation'},
  {value:'no_show_charge',label:'No-show charge (rider)'},
  {value:'driver_no_show',label:'Driver no-show'},
  {value:'property_damage',label:'Property damage'},
  {value:'safety_incident',label:'Safety incident'},
];

function genCaseId(){
  const ts=Date.now().toString(36).toUpperCase().slice(-6);
  const rnd=Math.random().toString(36).toUpperCase().slice(2,6);
  return `RIDER-${ts}-${rnd}`;
}

const NAV_TABS = [
  {id:'cases',label:'My Cases',icon:'📋'},
  {id:'report',label:'Report',icon:'➕'},
  {id:'account',label:'Account',icon:'⚙'},
];

export default function RiderPortal(){
  const api=useApi();
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [tab,setTab]=useState('cases');
  const [answer,setAnswer]=useState('');
  const [showForm,setShowForm]=useState(false);

  // Form state
  const [form,setForm]=useState({category:'',trip_id:'',description:'',dispute_amount:''});
  const [formError,setFormError]=useState('');
  const [formBusy,setFormBusy]=useState(false);

  async function connect(){
    await api.call('health');
    const list=await api.call('cases');
    setCases(list);
  }

  async function selectCase(id){
    setDetail(await api.call('cases/'+id));
    setTab('cases');
  }

  async function refreshCases(openId){
    const list=await api.call('cases');
    setCases(list);
    if(openId) setDetail(await api.call('cases/'+openId));
  }

  function validateForm(){
    if(!form.category) return 'Please select a dispute category.';
    if(!form.trip_id.trim()) return 'Please enter a trip reference.';
    if(form.trip_id.trim().length<2) return 'Trip reference must be at least 2 characters.';
    if(!form.description.trim()) return 'Please describe the issue.';
    if(form.description.trim().length<5) return 'Description must be at least 5 characters.';
    if(form.description.trim().length>3000) return 'Description must be 3000 characters or fewer.';
    if(form.dispute_amount){
      const amt=parseFloat(form.dispute_amount);
      if(isNaN(amt)||amt<0) return 'Disputed amount must be a positive number.';
      if(amt>100000) return 'Disputed amount cannot exceed SGD 100,000.';
    }
    return null;
  }

  async function submitCase(){
    const err=validateForm();
    if(err){setFormError(err);return}
    setFormError('');setFormBusy(true);
    const case_id=genCaseId();
    const payload={case_id,trip_id:form.trip_id.trim(),category:form.category,filed_by:'rider',description:form.description.trim(),synthetic:true};
    const amt=parseFloat(form.dispute_amount);
    if(!isNaN(amt)&&amt>0) payload.dispute_amount=amt;
    try{
      await api.call('cases',{method:'POST',body:payload});
      await refreshCases(case_id);
      setShowForm(false);
      setTab('cases');
      setForm({category:'',trip_id:'',description:'',dispute_amount:''});
      api.setNotice(`Case ${case_id} created. Your report is recorded as an unverified user submission.`);
    }catch(e){
      setFormError(e.message&&e.message.includes('already exists')?'A case with this ID already exists. Please try again.':(e.message||'Failed to create case.'));
    }finally{setFormBusy(false)}
  }

  const outcome=outcomeExplanation(detail);
  const pendingClarifications=detail?.clarifications?.filter(c=>c.status==='PENDING'&&c.recipient==='rider')||[];
  const activeCases=cases.filter(c=>c.status!=='RESOLVED'&&c.status!=='REVIEWED_AND_RESOLVED');

  // --- Not connected: mobile connect screen ---
  if(!api.key||!cases.length){
    return <div className="app-shell">
      <div className="app-connect">
        <div className="app-logo-big">R</div>
        <h2>RydeResolve Rider</h2>
        <p>Enter your demo passcode to view your disputes. The backend enforces case isolation — you can only see your own cases.</p>
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

  // --- Connected: mobile app shell ---
  return <div className="app-shell">
    <header className="app-header">
      <div className="app-logo">R</div>
      <div style={{flex:1}}>
        <h1>RydeResolve <span>Rider</span></h1>
        <p className="app-sub">{activeCases.length} active case{activeCases.length!==1?'s':''}{pendingClarifications.length>0?` · ${pendingClarifications.length} awaiting your response`:''}</p>
      </div>
    </header>

    {api.error&&<div className="alert error" role="alert" style={{margin:'0 12px'}}>{api.error}</div>}
    {api.notice&&<div className="alert success" style={{margin:'0 12px'}}>{api.notice}</div>}

    <div className="app-body">
      {/* Tab: Cases */}
      {tab==='cases'&&!showForm&&!detail&&<>
        <div className="app-section-head">
          <h2>Your cases</h2>
          <button onClick={()=>setShowForm(true)}>Report an issue</button>
        </div>
        {cases.length===0?
          <div className="card empty" style={{padding:'40px 16px'}}><div className="empty-symbol">📋</div><h2>No cases yet</h2><p>Tap "Report an issue" to file a dispute.</p></div>
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

      {/* Tab: Cases — detail view */}
      {tab==='cases'&&!showForm&&detail&&<>
        <div className="app-section-head">
          <button className="secondary" onClick={()=>setDetail(null)}>← Back</button>
          <button disabled={api.busy} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id);setDetail(r);api.setNotice('Status refreshed.')})}>Refresh</button>
        </div>

        {/* Status hero */}
        <div className="app-status-hero">
          <div className="ash-icon">{detail.path==='IMMEDIATE_HUMAN_REVIEW'?'🛡':detail.status==='RESOLVED'||detail.status==='REVIEWED_AND_RESOLVED'?'✅':detail.status==='AWAITING_CLARIFICATION'?'❓':'⏳'}</div>
          <h2>{detail.path?pathLabel(detail.path):statusLabel(detail.status)}</h2>
          <p>{detail.candidate?.reason||riderNextAction(detail)}</p>
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
          </div>
        </div>

        {/* Safety escalation */}
        {detail.path==='IMMEDIATE_HUMAN_REVIEW'&&<div className="app-action-card" style={{background:'var(--bad-bg)',borderColor:'var(--bad-border)'}}>
          <h3 style={{color:'var(--bad-fg)'}}>Safety escalation</h3>
          <p style={{color:'var(--bad-fg)'}}>Your report has been escalated for mandatory human review. AI does not determine fault or propose a remedy. A reviewer will assess the situation. No automated decision has been made.</p>
        </div>}

        {/* Clarification needed */}
        {pendingClarifications.length>0&&<div className="app-action-card">
          <h3>Action needed</h3>
          <p>The reviewer needs more information from you. Your response will be recorded as an unverified claim.</p>
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
          <p className="muted" style={{marginTop:'8px'}}>{riderNextAction(detail)}</p>
        </div>}

        {/* Timeline */}
        <div className="card">
          <p className="eyebrow">CASE PROGRESS</p>
          <CaseTimeline detail={detail} role="rider"/>
        </div>

        {/* Notifications */}
        {detail.notifications&&detail.notifications.length>0&&<div className="card">
          <p className="eyebrow">UPDATES</p>
          <p className="muted">Simulated — not delivered.</p>
          <div className="notif-list">{detail.notifications.filter(n=>n.recipient==='rider'||n.recipient==='all').map((n,i)=>(
            <div key={i} className="notif-item">
              <div className="notif-head"><span className="notif-kind">{notifKindLabel(n.kind)}</span><em className="status bad">Not delivered</em></div>
              <p className="notif-msg">{n.message}</p>
            </div>
          ))}</div>
        </div>}
      </>}

      {/* Tab: Cases — report form */}
      {tab==='cases'&&showForm&&<>
        <div className="app-section-head">
          <button className="secondary" onClick={()=>{setShowForm(false);setFormError('')}}>← Cancel</button>
        </div>
        <div className="app-form">
          <h2 style={{fontSize:'18px',marginBottom:'8px'}}>Report an issue</h2>
          <p className="muted" style={{marginBottom:'12px'}}>Use synthetic test information only. Your report will be recorded as an unverified user submission.</p>
          <label>Dispute category</label>
          <select value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>
            <option value="">Select a category…</option>
            {CATEGORIES.map(c=><option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <label>Trip reference</label>
          <input value={form.trip_id} onChange={e=>setForm({...form,trip_id:e.target.value})} placeholder="e.g. TRIP-2024-00123"/>
          <label>Description ({form.description.length}/3000)</label>
          <textarea style={{minHeight:'100px'}} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Describe what happened during the trip…"/>
          <label>Disputed amount (SGD, optional)</label>
          <input type="number" min="0" step="0.01" max="100000" value={form.dispute_amount} onChange={e=>setForm({...form,dispute_amount:e.target.value})} placeholder="e.g. 15.50"/>
          {form.category==='safety_incident'&&<div className="alert error" style={{marginTop:'8px'}}>Safety allegations are escalated immediately. AI will not determine fault.</div>}
          {formError&&<div className="alert error" style={{marginTop:'10px'}}>{formError}</div>}
          <button disabled={formBusy||!form.category||!form.trip_id.trim()||!form.description.trim()} onClick={()=>api.run(submitCase)}>{formBusy?'Creating…':'Submit report'}</button>
        </div>
      </>}

      {/* Tab: Report shortcut */}
      {tab==='report'&&<>
        {setShowForm(true),setTab('cases'),null}
      </>}

      {/* Tab: Account */}
      {tab==='account'&&<>
        <div className="app-section-head"><h2>Account</h2></div>
        <div className="card">
          <h3 style={{margin:'0 0 8px'}}>Demo session</h3>
          <p className="muted">You are connected as a Rider. Case isolation is enforced by the backend — you can only see your own cases.</p>
        </div>
        <div className="card">
          <h3 style={{margin:'0 0 8px'}}>About this demo</h3>
          <p className="muted">RydeResolve is a synthetic demo. No real payments, notifications, or account actions were executed. All data is synthetic.</p>
        </div>
        <div className="card" style={{textAlign:'center'}}>
          <Link href="/" className="lab-enter">← Back to role selection</Link>
        </div>
      </>}
    </div>

    {/* Bottom nav */}
    <nav className="app-nav" role="navigation" aria-label="Main navigation">
      {NAV_TABS.map(t=><button key={t.id} className={tab===t.id?'active':''} onClick={()=>{if(t.id==='report'){setShowForm(true);setTab('cases')}else{setTab(t.id);setShowForm(false);if(t.id==='cases')setDetail(null)}}} aria-label={t.label}>
        <span className="nav-icon">{t.icon}</span>
        {t.label}
      </button>)}
    </nav>

    <div className="demo-badge">SYNTHETIC DEMO</div>
  </div>;
}
