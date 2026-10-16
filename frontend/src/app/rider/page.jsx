'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
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

export default function RiderPortal(){
  const api=useApi();
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [policy,setPolicy]=useState(null);
  const [answer,setAnswer]=useState('');

  // Form state
  const [showForm,setShowForm]=useState(false);
  const [form,setForm]=useState({category:'',trip_id:'',description:'',dispute_amount:''});
  const [formError,setFormError]=useState('');
  const [formBusy,setFormBusy]=useState(false);

  async function connect(){
    setPolicy(await api.call('health'));
    const list=await api.call('cases');
    setCases(list);
  }

  async function selectCase(id){
    setDetail(await api.call('cases/'+id));
  }

  async function refreshCases(openId){
    const list=await api.call('cases');
    setCases(list);
    if(openId){
      setDetail(await api.call('cases/'+openId));
    }
  }

  function validateForm(){
    if(!form.category){return 'Please select a dispute category.'}
    if(!form.trip_id.trim()){return 'Please enter a trip reference.'}
    if(form.trip_id.trim().length<2){return 'Trip reference must be at least 2 characters.'}
    if(!form.description.trim()){return 'Please describe the issue.'}
    if(form.description.trim().length<5){return 'Description must be at least 5 characters.'}
    if(form.description.trim().length>3000){return 'Description must be 3000 characters or fewer.'}
    if(form.dispute_amount){
      const amt=parseFloat(form.dispute_amount);
      if(isNaN(amt)||amt<0){return 'Disputed amount must be a positive number.'}
      if(amt>100000){return 'Disputed amount cannot exceed SGD 100,000.'}
    }
    return null;
  }

  async function submitCase(){
    const err=validateForm();
    if(err){setFormError(err);return}
    setFormError('');setFormBusy(true);
    const case_id=genCaseId();
    const payload={
      case_id,
      trip_id:form.trip_id.trim(),
      category:form.category,
      filed_by:'rider',
      description:form.description.trim(),
      synthetic:true,
    };
    const amt=parseFloat(form.dispute_amount);
    if(!isNaN(amt)&&amt>0){payload.dispute_amount=amt}
    try{
      await api.call('cases',{method:'POST',body:payload});
      await refreshCases(case_id);
      setShowForm(false);
      setForm({category:'',trip_id:'',description:'',dispute_amount:''});
      api.setNotice(`Case ${case_id} created. Your report is recorded as an unverified user submission.`);
    }catch(e){
      if(e.message&&e.message.includes('already exists')){
        setFormError('A case with this ID already exists. Please try again.');
      }else{
        setFormError(e.message||'Failed to create case. Please try again.');
      }
    }finally{
      setFormBusy(false);
    }
  }

  const outcome=outcomeExplanation(detail);

  return <main>
    <header className="masthead">
      <div className="brand">
        <div className="brand-icon">R</div>
        <div><h1>RydeResolve <span>Rider</span></h1><p>View cases, provide clarification, and report issues</p></div>
      </div>
      <div className="demo-label">DEMO ENVIRONMENT · SYNTHETIC DATA</div>
    </header>

    <section className="card connection">
      <div>
        <h2>Rider access</h2>
        <p>Enter your rider demo passcode from backend/.env. This is a demo environment using synthetic data only — not production identity. The backend enforces case isolation per authenticated demo identity.</p>
      </div>
      <input aria-label="Demo passcode" type="password" placeholder="rider passcode" value={api.key} onChange={e=>api.setKey(e.target.value)}/>
      <button disabled={api.busy||!api.key} onClick={()=>api.run(connect)}>Connect</button>
    </section>

    {api.error&&<div className="alert error" role="alert">{api.error}</div>}
    {api.notice&&<div className="alert success">{api.notice}</div>}

    {policy&&<div className="micro">Demo environment · {policy.ai_mode==='mock'?'Mock mode (no model calls)':'Live ADK'} · Policy signoff: {policy.team_signoff_valid?'verified':'missing'} · Storage: {policy.storage_mode}</div>}

    <div className="workspace">
      <aside className="card sidebar">
        <div className="section-head">
          <h2>Synthetic demo cases</h2>
          {api.key&&<button className="small" disabled={api.busy} onClick={()=>setShowForm(!showForm)}>{showForm?'Cancel':'Report an issue'}</button>}
        </div>
        {cases.length===0?
          <p className="muted">{api.key?'No cases loaded. Click "Report an issue" or load demo cases from the reviewer portal.':'Enter passcode and click Connect.'}</p>
        :cases.map(item=>(
          <button key={item.case_id} className={'case-item '+(detail?.case_id===item.case_id?'selected':'')} onClick={()=>api.run(()=>selectCase(item.case_id))}>
            <strong>{item.case_id}</strong>
            <span>{categoryLabel(item.category)}</span>
            <em className={'status '+(TONES[item.status]||'neutral')}>{statusLabel(item.status)}</em>
          </button>
        ))}
      </aside>

      <div className="primary">
        {showForm?
          <div className="card">
            <p className="eyebrow">REPORT AN ISSUE</p>
            <h3>File a new dispute</h3>
            <p className="muted">Use synthetic test information only — do not enter real customer personal data. Your report will be recorded as an unverified user submission and will not automatically trigger any financial action.</p>
            <div className="fieldgrid" style={{flexDirection:'column',alignItems:'stretch'}}>
              <label style={{fontSize:'12px',fontWeight:600,color:'#3d516c'}}>Dispute category</label>
              <select value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>
                <option value="">Select a category…</option>
                {CATEGORIES.map(c=><option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
              <label style={{fontSize:'12px',fontWeight:600,color:'#3d516c',marginTop:'8px'}}>Trip reference</label>
              <input value={form.trip_id} onChange={e=>setForm({...form,trip_id:e.target.value})} placeholder="e.g. TRIP-2024-00123"/>
              <label style={{fontSize:'12px',fontWeight:600,color:'#3d516c',marginTop:'8px'}}>Description <span style={{fontWeight:400,color:'#8899aa'}}>({form.description.length}/3000)</span></label>
              <textarea style={{minHeight:'120px'}} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Describe what happened during the trip…"/>
              <label style={{fontSize:'12px',fontWeight:600,color:'#3d516c',marginTop:'8px'}}>Disputed amount (SGD, optional)</label>
              <input type="number" min="0" step="0.01" max="100000" value={form.dispute_amount} onChange={e=>setForm({...form,dispute_amount:e.target.value})} placeholder="e.g. 15.50"/>
              <small style={{color:'#8899aa',fontSize:'11px'}}>Provide the amount you believe was incorrectly charged. Leave blank if the dispute is not about a specific amount (e.g. route deviation or safety).</small>
              {form.category==='safety_incident'&&<div className="alert error" style={{marginTop:'8px'}}>Safety allegations are escalated immediately for mandatory human review. AI will not determine fault or propose a remedy.</div>}
            </div>
            {formError&&<div className="alert error" style={{marginTop:'10px'}}>{formError}</div>}
            <button disabled={formBusy||!form.category||!form.trip_id.trim()||!form.description.trim()} onClick={()=>api.run(submitCase)} style={{marginTop:'14px'}}>{formBusy?'Creating case…':'Submit report'}</button>
          </div>
        :!detail?
          <div className="card empty"><div className="empty-symbol">⌁</div><h2>Select a case</h2><p>View your dispute status, provide clarifications, and see outcomes. Or click "Report an issue" to file a new case.</p></div>
        :
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
              <span>Policy: {detail.policy_version||'2.1'}</span>
            </div>
            <button disabled={api.busy||!api.key} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id);setDetail(r);api.setNotice('Case status refreshed.')})}>Refresh status</button>
          </div>

          {detail.path&&<div className="card result">
            <p className="eyebrow">CURRENT STATUS</p>
            <h2>{pathLabel(detail.path)}</h2>
            <p>{detail.candidate?.reason||riderNextAction(detail)}</p>
            {detail.gate?.reasons?.length>0&&<div style={{marginTop:'8px'}}><p className="muted" style={{marginBottom:'4px'}}>Policy rationale:</p><ul style={{fontSize:'12px',color:'#3d516c',lineHeight:'1.6',paddingLeft:'18px'}}>{detail.gate.reasons.map((r,i)=><li key={i}>{r}</li>)}</ul></div>}
            {detail.mock_action&&<div className="receipt">
              <b>{dispositionLabel(detail.mock_action.disposition)}</b> · SGD {Number(detail.mock_action.amount||0).toFixed(2)}
              <br/><small style={{color:'#5a7a62'}}>Test transaction · No real funds transferred · Receipt: {detail.mock_action.receipt}</small>
            </div>}
          </div>}

          {detail.path==='IMMEDIATE_HUMAN_REVIEW'&&<div className="card highlight" style={{borderLeft:'5px solid #ad3140'}}>
            <p className="eyebrow">⚠ SAFETY ESCALATION</p>
            <h3>This case requires immediate human review</h3>
            <p className="muted">Your report has been escalated for mandatory human review. AI does not determine fault or propose a remedy for safety incidents. A reviewer will assess the situation and contact you through official channels if needed. No automated decision has been made.</p>
          </div>}

          {detail.clarifications?.filter(c=>c.status==='PENDING'&&c.recipient==='rider').length>0&&(
            <div className="card highlight">
              <p className="eyebrow">CLARIFICATION REQUESTED</p>
              <h3>We need more information from you</h3>
              <p className="muted">Please provide additional details so the reviewer can continue the investigation. Your response will be recorded as an unverified claim — the reviewer may request source documentation to verify it.</p>
              {detail.clarifications.filter(c=>c.status==='PENDING'&&c.recipient==='rider').map(c=>(
                <div key={c.request_id} style={{marginTop:'12px'}}>
                  <p style={{fontWeight:500}}>{c.question}</p>
                  <em className="status bad">Your account statement — unverified</em>
                  <textarea placeholder="Type your response here…" value={answer} onChange={e=>setAnswer(e.target.value)} style={{marginTop:'8px'}}/>
                  <button disabled={api.busy||!answer.trim()} onClick={()=>api.run(async()=>{const r=await api.call('cases/'+detail.case_id+'/clarifications/'+c.request_id+'/reply',{method:'POST',body:{answer}});setDetail(r);setAnswer('');api.setNotice('Your response has been recorded as an unverified claim. The reviewer may request source documentation.')})}>Submit response</button>
                </div>
              ))}
            </div>
          )}

          {detail.notifications&&detail.notifications.length>0&&(
            <div className="card outbox">
              <p className="eyebrow">CASE UPDATES</p>
              <h3>Simulated notifications — not delivered</h3>
              <p className="muted">These are simulated messages for demo purposes. No email, SMS, push notification, or payment was sent.</p>
              <div className="notif-list">{detail.notifications.filter(n=>n.recipient==='rider'||n.recipient==='all').map((n,i)=>(
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
            <p style={{fontSize:'13px',lineHeight:'1.6',color:'#3d516c'}}>{outcome}</p>
            <p className="muted" style={{marginTop:'8px'}}>{riderNextAction(detail)}</p>
          </div>}

          <div className="card">
            <h3>Case details</h3>
            <p className="muted">The information below is from your unverified report and any evidence the reviewer has added. Claims are not automatically verified.</p>
            <details><summary>Show case facts</summary><pre className="json">{JSON.stringify(detail.facts,null,2)}</pre></details>
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
