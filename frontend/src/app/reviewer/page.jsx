'use client';
import {useState,useEffect,useRef} from 'react';
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

// Reviewer-friendly agent display names and order
const AGENT_DISPLAY={
  RiderAdvocate:{title:'Rider Perspective',icon:'🧑',desc:'Advocates for the rider\u2019s position'},
  DriverAdvocate:{title:'Driver Perspective',icon:'🚗',desc:'Advocates for the driver\u2019s position'},
  PolicyPrecedent:{title:'Policy & Precedent',icon:'📐',desc:'Matches applicable policy rules and prior precedents'},
  FraudBadFaith:{title:'Fraud & Bad-Faith Check',icon:'🔍',desc:'Screens for fraud indicators and bad-faith patterns'},
  Judge:{title:'Consistency Judge',icon:'⚖',desc:'Cross-checks all advocates for consistency'},
};
const AGENT_ORDER=['RiderAdvocate','DriverAdvocate','PolicyPrecedent','FraudBadFaith','Judge'];

// Human-readable labels for common fact field names
const FACT_LABELS={
  upfront_quote:'Upfront quote',actual_fare:'Actual fare',surge_before:'Surge before',
  surge_after:'Surge after',rider_notified:'Rider notified',notification_log_complete:'Notification log complete',
  difference_solely_surge:'Difference solely surge',rider_proceeded:'Rider proceeded',
  actual_distance_km:'Actual distance (km)',recommended_distance_km:'Recommended distance (km)',
  traffic_justified:'Traffic justified',excess_distance_fare:'Excess distance fare',
  rider_agreed:'Rider agreed',scheduled_pickup_at:'Scheduled pickup',cancellation_at:'Cancellation time',
  driver_arrived:'Driver arrived',rider_absent:'Rider absent',driver_message_count:'Driver messages',
  driver_call_count:'Driver calls',rider_disputes_claim:'Rider disputes claim',damage_kind:'Damage kind',
  photo_verifiable:'Photo verifiable',trip_link_verified:'Trip link verified',
  photo_submitted_within_24h:'Photo submitted within 24h',dispute_amount:'Dispute amount',
  dispute_value_basis:'Dispute value basis',
};

// Processing pipeline steps for the live progress display
const PROCESS_STEPS=[
  {id:'safety',label:'Safety screening',desc:'Checking for safety allegations'},
  {id:'routing',label:'Routing index',desc:'Identifying candidate policy rules'},
  {id:'gaps',label:'Evidence check',desc:'Checking for missing or conflicting evidence'},
  {id:'agents',label:'Agent evaluation',desc:'Running advocate and judge agents'},
  {id:'gate',label:'Policy gate',desc:'Applying deterministic policy validation'},
  {id:'outcome',label:'Outcome',desc:'Recording resolution or routing to review'},
];

function factLabel(field){return FACT_LABELS[field]||field.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}
function formatFactValue(v){
  if(v===true)return 'Yes';
  if(v===false)return 'No';
  if(v===null||v===undefined)return '—';
  if(typeof v==='number')return Number.isInteger(v)?String(v):v.toFixed(2);
  if(typeof v==='string')return v;
  return JSON.stringify(v);
}

// Convert rule condition/effect objects into reader-friendly sentences.
function readableCondition(rule){
  if(!rule)return null;
  const c=rule.condition;
  if(!c)return null;
  const parts=[];
  if(c.trigger==='route_differs_from_recommended') parts.push('The actual route differs from the GPS-recommended route.');
  if(c.notification_timing==='before_or_at_deviation') parts.push('Notification must be given before or at the point of deviation.');
  if(c.traffic_justification===true) parts.push('Traffic justification is present.');
  if(c.traffic_justification===false) parts.push('No traffic justification is present.');
  if(c.rider_informed_and_agreed===true) parts.push('The rider was informed and agreed.');
  if(c.rider_informed_and_agreed===false) parts.push('The rider was not informed or did not agree.');
  if(c.deviation_gt_1km===true) parts.push('The deviation exceeds 1 km.');
  if(c.deviation_gt_1km===false) parts.push('The deviation is 1 km or less.');
  if(c.rider_absent===true) parts.push('The rider was absent at pickup.');
  if(c.rider_absent===false) parts.push('The rider was present at pickup.');
  if(c.driver_arrived===true) parts.push('The driver arrived at the pickup location.');
  if(c.driver_arrived===false) parts.push('The driver did not arrive at the pickup location.');
  if(c.driver_contact_attempts?.chat>=1) parts.push('At least 1 in-app chat message was sent.');
  if(c.driver_contact_attempts?.call>=1) parts.push('At least 1 call was made via the app.');
  if(c.photo_verifiable===true) parts.push('Photo evidence is verifiable.');
  if(c.photo_verifiable===false) parts.push('Photo evidence is not verifiable.');
  if(c.photo_submitted_within_24h===true) parts.push('Photo evidence was submitted within 24 hours.');
  if(c.photo_submitted_within_24h===false) parts.push('Photo evidence was not submitted within 24 hours.');
  if(c.trip_link_verified===true) parts.push('The damage is linked to the trip.');
  if(c.trip_link_verified===false) parts.push('The damage is not linked to the trip.');
  if(c.fraud_flags>=1) parts.push(`At least ${c.fraud_flags} fraud flag(s) are present.`);
  // Fallback: list unknown boolean/object fields as bullet phrases.
  Object.entries(c).forEach(([k,v])=>{
    if(k.startsWith('dispute_value'))return;
    if(v===true) parts.push(`${k.replace(/_/g,' ')}.`);
    if(v===false) parts.push(`Not ${k.replace(/_/g,' ')}.`);
    if(typeof v==='string') parts.push(`${k.replace(/_/g,' ')}: ${v}.`);
  });
  return parts.length?parts:null;
}

function readableEffect(rule){
  if(!rule)return null;
  const e=rule.effect;
  if(!e)return null;
  const parts=[];
  if(e.permitted_reasons?.length) parts.push(`Permitted reasons: ${e.permitted_reasons.join(', ')}.`);
  if(e.notification_required===true) parts.push('Notification is required.');
  if(e.notification_required===false) parts.push('Notification is not required.');
  if(e.valid_notification_methods?.length) parts.push(`Valid notification methods: ${e.valid_notification_methods.map(m=>m.replace(/_/g,' ')).join(', ')}.`);
  if(e.reason_required===true) parts.push('A brief reason must be provided.');
  if(e.disposition){
    const amt=e.amount!=null?` SGD ${Number(e.amount).toFixed(2)}`:'';
    parts.push(`Ruling outcome: ${e.disposition.replace(/_/g,' ')}${amt}.`);
  }
  if(e.max_refund!=null) parts.push(`Maximum refund/credit: SGD ${Number(e.max_refund).toFixed(2)}.`);
  if(e.void_cancellation_fee===true) parts.push('The cancellation fee is voided.');
  if(e.goodwill_credit!=null) parts.push(`Goodwill credit of SGD ${Number(e.goodwill_credit).toFixed(2)} may apply.`);
  if(e.suspension_interim===true) parts.push('Interim suspension may apply pending human review.');
  // Fallback for other boolean/string fields.
  Object.entries(e).forEach(([k,v])=>{
    if(['permitted_reasons','valid_notification_methods','disposition','amount','max_refund'].includes(k))return;
    if(v===true) parts.push(`${k.replace(/_/g,' ')}.`);
    if(v===false) parts.push(`Not ${k.replace(/_/g,' ')}.`);
    if(typeof v==='string') parts.push(`${k.replace(/_/g,' ')}: ${v}.`);
  });
  return parts.length?parts:null;
}

function ruleTitle(rule){
  if(!rule)return '';
  if(rule.title)return rule.title;
  const id=rule.rule_id||'';
  if(id.startsWith('RD')) return 'Route deviation';
  if(id.startsWith('NS')) return 'No-show / cancellation';
  if(id.startsWith('FA')) return 'Fare / surge';
  if(id.startsWith('PD')) return 'Property damage';
  if(id.startsWith('SF')) return 'Safety';
  if(id.startsWith('TH')) return 'Threshold / confidence';
  return 'Policy rule';
}

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
  const [processStep,setProcessStep]=useState(-1);
  const [ruleSnippets,setRuleSnippets]=useState({});
  const [expandedRules,setExpandedRules]=useState({});
  const processTimerRef=useRef(null);

  async function connect(){
    setPolicy(await api.call('health'));
    const list=await api.call('cases');
    setCases(list);
  }

  async function selectCase(id){
    if(processTimerRef.current){clearInterval(processTimerRef.current);processTimerRef.current=null}
    setProcessing(false);
    setProcessStep(-1);
    setDetail(await api.call('cases/'+id));
    setRuleSnippets({});
    setExpandedRules({});
    setPacket(null);
    setTab('overview');
  }

  async function loadRuleSnippets(ruleIds){
    if(!ruleIds||ruleIds.length===0) return;
    const needed=ruleIds.filter(id=>!ruleSnippets[id]);
    if(needed.length===0) return;
    try{
      const r=await api.call('policy/rules?ids='+needed.join(','));
      setRuleSnippets(prev=>({...prev,...Object.fromEntries(r.rules.map(rule=>[rule.rule_id,rule]))}));
    }catch{/* ignore — snippets are enhancement only */}
  }

  function toggleRule(ruleId){
    setExpandedRules(prev=>({...prev,[ruleId]:!prev[ruleId]}));
    const rule=ruleSnippets[ruleId];
    if(!rule&&ruleId) loadRuleSnippets([ruleId]);
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

  useEffect(()=>()=>{if(processTimerRef.current) clearInterval(processTimerRef.current)},[]);

  async function doProcess(){
    if(processing) return; // prevent duplicate clicks
    setProcessing(true);
    setProcessStep(0);
    // Walk through pipeline steps for visual feedback.
    // The actual API call blocks until processing completes server-side.
    let stepIdx=0;
    processTimerRef.current=setInterval(()=>{
      stepIdx++;
      if(stepIdx<PROCESS_STEPS.length) setProcessStep(stepIdx);
      else if(processTimerRef.current) clearInterval(processTimerRef.current);
    },400);
    // Safety timeout: if the server call hangs, reset the UI so the user can retry.
    const timeoutRef=setTimeout(()=>{
      if(processTimerRef.current){clearInterval(processTimerRef.current);processTimerRef.current=null}
      setProcessing(false);
      setProcessStep(-1);
      api.setError('Processing timed out. Please try again.');
    },25000);
    try{
      const r=await api.call('cases/'+selected+'/process',{method:'POST'});
      clearTimeout(timeoutRef);
      if(processTimerRef.current){clearInterval(processTimerRef.current);processTimerRef.current=null}
      setProcessStep(PROCESS_STEPS.length-1);
      setDetail(r);
      // Preload rule snippets for the routing + agent + gate rules
      const allRules=new Set();
      (r.routing?.candidate_rule_ids||[]).forEach(id=>allRules.add(id));
      (r.gate?.blocking_rules||[]).forEach(id=>allRules.add(id));
      (r.candidate?.rule_ids||[]).forEach(id=>allRules.add(id));
      Object.values(r.agent_outputs||{}).forEach(a=>(a.policy_rule_ids||[]).forEach(id=>allRules.add(id)));
      loadRuleSnippets([...allRules]);
      api.setNotice('Case processing complete.');
      // Clear processing highlight after 2s
      setTimeout(()=>{setProcessStep(-1)},2000);
    }catch(e){
      clearTimeout(timeoutRef);
      if(processTimerRef.current){clearInterval(processTimerRef.current);processTimerRef.current=null}
      setProcessStep(-1);
      api.setError(e.message);
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
        <Link href="/monitor" className="lab-enter">ADK Monitor</Link>
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
              {!isResolved&&<button disabled={processing} onClick={()=>{setTab('overview');api.run(doProcess)}}>{processing?'Processing…':'Process / Re-evaluate'}</button>}
              {processing&&processStep>=0&&<div className="process-timeline">
                {PROCESS_STEPS.map((step,i)=>{
                  const state=i<processStep?'done':i===processStep?'active':'pending';
                  return <div key={step.id} className={'process-step '+state}>
                    <div className="process-dot"/>
                    <div className="process-step-body">
                      <div className="process-step-label">{step.label}</div>
                      <div className="process-step-desc">{step.desc}</div>
                    </div>
                  </div>;
                })}
              </div>}
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

              {/* Manual classification required for "other" cases */}
              {detail.category==='other'&&!isResolved&&<div className="card highlight" style={{borderLeft:'4px solid var(--warn-fg)'}}>
                <p className="eyebrow">MANUAL CLASSIFICATION REQUIRED</p>
                <h3>Unclassified dispute category</h3>
                <p className="muted">This case was submitted as "Other / I'm not sure." The rider's description is shown above. Reclassify to a specific category before adjudication can proceed.</p>
                <div style={{display:'flex',gap:'8px',marginTop:'12px',flexWrap:'wrap',alignItems:'center'}}>
                  <select id="reclass-select" defaultValue="" aria-label="Reclassify case to category">
                    <option value="" disabled>Select new category…</option>
                    <option value="fare_dispute">Fare dispute</option>
                    <option value="route_deviation">Route deviation</option>
                    <option value="no_show_charge">No-show charge (rider)</option>
                    <option value="driver_no_show">Driver no-show</option>
                    <option value="property_damage">Property damage</option>
                  </select>
                  <button className="small" disabled={api.busy} onClick={()=>api.run(async()=>{
                    const sel=document.getElementById('reclass-select');
                    if(!sel||!sel.value){api.setError('Select a new category first.');return}
                    const reason='Reviewer reclassification from "other" to '+sel.value;
                    const r=await api.call('cases/'+detail.case_id+'/reclassify',{method:'POST',body:{category:sel.value,reason}});
                    setDetail(r);api.setNotice('Case reclassified to '+sel.value+'. Original category preserved for audit. Process the case to run policy evaluation.');
                  })}>Reclassify</button>
                </div>
                {detail.original_category&&<p className="muted" style={{fontSize:'11px',marginTop:'8px'}}>Original category: {categoryLabel(detail.original_category)}</p>}
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
                {detail.facts&&Object.keys(detail.facts).length>0?
                  <div className="fact-grid">
                    {Object.entries(detail.facts).map(([k,v])=>{
                      const ev=detail.evidence?.find(e=>e.field===k);
                      return <div key={k} className="fact-item">
                        <div className="fact-label">{factLabel(k)}</div>
                        <div className="fact-value">{formatFactValue(v)}</div>
                        {ev&&<div className="fact-prov"><span className="fact-prov-label">Source:</span> {ev.provenance||'fixture'}</div>}
                      </div>;
                    })}
                  </div>
                :<p className="muted">No structured facts recorded for this case.</p>}
              </div>

              <div className="card">
                <div className="section-head">
                  <h3>Routing index</h3>
                  <button className="small" disabled={api.busy} onClick={()=>loadRuleSnippets(detail.routing?.candidate_rule_ids||[])}>Load rule details</button>
                </div>
                <p className="muted">Candidate rules identified for this case category. These are not rulings — they identify which policy sections may apply.</p>
                {detail.routing?.candidate_rule_ids?.length?
                  <div className="rule-list">
                    {detail.routing.candidate_rule_ids.map(rid=>{
                      const rule=ruleSnippets[rid];
                      const isExpanded=expandedRules[rid];
                      return <div key={rid} className="rule-item">
                        <div className="rule-item-head" onClick={()=>{toggleRule(rid)}} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==='Enter'||e.key===' ')toggleRule(rid)}}>
                          <span className="rule-id">{rid}</span>
                          {rule&&<span className="rule-section">§{rule.source_section}</span>}
                          {detail.routing?.matched_phrase_rule_ids?.includes(rid)&&<span className="rule-matched">matched</span>}
                          <span className="rule-expand">{isExpanded?'▾':'▸'}</span>
                        </div>
                        {isExpanded&&rule&&<div className="rule-detail">
                          <div className="rule-detail-title">{ruleTitle(rule)}</div>
                          {rule.notes&&<div className="rule-field"><span className="rule-field-label">Summary:</span> {rule.notes}</div>}
                          {readableCondition(rule)&&<div className="rule-field">
                            <span className="rule-field-label">Condition:</span>
                            <ul className="rule-readable-list">{readableCondition(rule).map((line,i)=><li key={i}>{line}</li>)}</ul>
                          </div>}
                          {readableEffect(rule)&&<div className="rule-field">
                            <span className="rule-field-label">Effect:</span>
                            <ul className="rule-readable-list">{readableEffect(rule).map((line,i)=><li key={i}>{line}</li>)}</ul>
                          </div>}
                          {rule.evidence_requirements?.length>0&&<div className="rule-field"><span className="rule-field-label">Evidence required:</span> {rule.evidence_requirements.join(', ')}</div>}
                          {rule.precedence&&<div className="rule-field"><span className="rule-field-label">Precedence:</span> {rule.precedence}</div>}
                        </div>}
                        {isExpanded&&!rule&&<div className="rule-detail"><span className="muted">Loading rule details…</span></div>}
                      </div>;
                    })}
                  </div>
                :<p className="muted">Process the case to retrieve routing IDs.</p>}
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
              {detail.agent_outputs&&Object.keys(detail.agent_outputs).length>0?
                <div className="agent-flow">
                  {detail.path==='IMMEDIATE_HUMAN_REVIEW'&&<div className="agent-flow-skip">
                    <div className="skip-icon">⚠</div>
                    <div>
                      <b>Safety escalation — agents did not adjudicate</b>
                      <p className="muted">Safety allegations were detected during intake screening. The Consistency Judge was skipped per SF-5.1 / SF-5.2. No AI fault determination or remedy was proposed.</p>
                    </div>
                  </div>}
                  {AGENT_ORDER.filter(n=>detail.agent_outputs[n]).map((agentKey,idx)=>{
                    const v=detail.agent_outputs[agentKey];
                    const display=AGENT_DISPLAY[agentKey]||{title:agentKey,icon:'🔧',desc:''};
                    const hasError=v.parse_failed||v.agent_error||v.validation_error||v.failure_kind;
                    const traceEntry=detail.agent_trace?.find(t=>t.agent===agentKey);
                    return <div key={agentKey} className={'agent-step '+(hasError?'failed':'completed')}>
                      <div className="agent-step-connector">
                        <div className="agent-step-dot"/>
                        {idx<AGENT_ORDER.length-1&&<div className="agent-step-line"/>}
                      </div>
                      <div className="agent-step-card">
                        <div className="agent-step-head">
                          <span className="agent-step-icon">{display.icon}</span>
                          <div>
                            <div className="agent-step-title">{display.title}</div>
                            <div className="agent-step-sub">{display.desc}</div>
                          </div>
                          <div className="agent-step-meta">
                            {hasError?
                              <em className="status bad">Error: {v.failure_kind||v.parse_failed?'parse failed':'agent error'}</em>
                            :<em className="status good">{v.recommended_disposition?dispositionLabel(v.recommended_disposition):'evaluated'}</em>}
                            {v.mode&&<span className="agent-mode">{String(v.mode).toLowerCase().includes('mock')?'Mock':'Live'}</span>}
                          </div>
                        </div>
                        <p className="agent-step-summary">{v.summary}</p>
                        {v.recommended_amount!=null&&v.recommended_amount>0&&
                          <div className="agent-step-amount">Recommended: SGD {Number(v.recommended_amount).toFixed(2)}</div>}
                        {v.policy_rule_ids?.length>0&&<div className="agent-rules">
                          {v.policy_rule_ids.map(rid=>{
                            const rule=ruleSnippets[rid];
                            const isExpanded=expandedRules[rid];
                            return <div key={rid} className="agent-rule-chip-wrap">
                              <button className="rule-chip-btn" onClick={()=>toggleRule(rid)}>
                                {rid} <span className="rule-chip-expand">{isExpanded?'▾':'▸'}</span>
                              </button>
                              {isExpanded&&rule&&<div className="rule-popover">
                                <div className="rule-popover-head"><b>{rid}</b> <span className="muted">§{rule.source_section}</span></div>
                                <div className="rule-detail-title">{ruleTitle(rule)}</div>
                                {rule.notes&&<div className="rule-field"><span className="rule-field-label">Summary:</span> {rule.notes}</div>}
                                {readableCondition(rule)&&<div className="rule-field">
                                  <span className="rule-field-label">Condition:</span>
                                  <ul className="rule-readable-list">{readableCondition(rule).map((line,i)=><li key={i}>{line}</li>)}</ul>
                                </div>}
                                {readableEffect(rule)&&<div className="rule-field">
                                  <span className="rule-field-label">Effect:</span>
                                  <ul className="rule-readable-list">{readableEffect(rule).map((line,i)=><li key={i}>{line}</li>)}</ul>
                                </div>}
                                {rule.evidence_requirements?.length>0&&<div className="rule-field"><span className="rule-field-label">Evidence:</span> {rule.evidence_requirements.join(', ')}</div>}
                              </div>}
                              {isExpanded&&!rule&&<div className="rule-popover"><span className="muted">Loading…</span></div>}
                            </div>;
                          })}
                        </div>}
                        {(v.supporting_evidence?.length>0||v.opposing_evidence?.length>0)&&
                          <div className="agent-evidence-row">
                            {v.supporting_evidence?.length>0&&<div className="agent-ev-list"><span className="agent-ev-label">Supports:</span> {v.supporting_evidence.join(', ')}</div>}
                            {v.opposing_evidence?.length>0&&<div className="agent-ev-list"><span className="agent-ev-label">Opposes:</span> {v.opposing_evidence.join(', ')}</div>}
                          </div>}
                        {v.uncertainties?.length>0&&
                          <div className="agent-uncertainties"><span className="agent-ev-label">Uncertainties:</span> {v.uncertainties.join(', ')}</div>}
                        {traceEntry&&<details className="agent-trace"><summary>Trace entry</summary>
                          <div className="trace-mini">
                            {Object.entries(traceEntry).filter(([k])=>k!=='agent').map(([k,val])=>
                              <div key={k} className={'trace-field'+(k==='error_code'?' trace-err':'')}><b>{k}:</b> {String(val)}</div>
                            )}
                          </div>
                        </details>}
                      </div>
                    </div>;
                  })}
                  <details className="agent-tech-trace"><summary>Full technical trace (all agents)</summary><pre className="json">{JSON.stringify(detail.agent_trace,null,2)}</pre></details>
                </div>
              :<div className="card empty"><div className="empty-symbol">🤖</div><h2>No agent outputs</h2><p>Process the case to run the ADK agents.</p></div>}
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
