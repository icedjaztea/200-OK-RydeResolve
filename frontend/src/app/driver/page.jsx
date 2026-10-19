'use client';
import {useState,useEffect} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {validateAttachments,uploadReportAttachments} from '../../lib/reportAttachments';
import {CaseTimeline} from '../../lib/Timeline';
import MapView from '../../lib/MapView';
import {getTrips,addTrip,findTrip,formatTripDateTime,formatFare} from '../../lib/trips';
import {
  TONES, statusLabel, pathLabel, categoryLabel, dispositionLabel, notifKindLabel,
  outcomeExplanation, driverNextAction,
} from '../../lib/labels';

const SINGAPORE_AREAS = [
  'Orchard Road','Marina Bay','Tampines','Jurong East','Ang Mo Kio',
  'Bedok','Clementi','Bishan','Paya Lebar','Holland Village',
  'Sentosa','Changi Airport','Sengkang','Punggol','Woodlands',
  'Yishun','Serangoon','Kallang','Geylang','Novena',
];

function rand(items){return items[Math.floor(Math.random()*items.length)];}
function randBetween(min,max){return Math.random()*(max-min)+min;}
function randInt(min,max){return Math.floor(Math.random()*(max-min+1))+min;}

const NAV_TABS = [
  {id:'disputes',label:'Disputes',icon:'📋'},
  {id:'trips',label:'Trips',icon:'🚗'},
  {id:'account',label:'Account',icon:'⚙'},
];

export default function DriverPortal(){
  const api=useApi('driver_a');
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [tab,setTab]=useState('disputes');
  const [answer,setAnswer]=useState('');
  const [trips,setTrips]=useState([]);
  const [selectedTrip,setSelectedTrip]=useState(null);
  const [showTripForm,setShowTripForm]=useState(false);
  const [identity,setIdentity]=useState('driver_a');
  const [connected,setConnected]=useState(false);
  const [uploadFile,setUploadFile]=useState(null);
  const [showForm,setShowForm]=useState(false);
  const [form,setForm]=useState({category:'property_damage',trip_id:'',description:'',dispute_amount:''});
  const [formError,setFormError]=useState('');
  const [reportFiles,setReportFiles]=useState([]);
  const [pendingUploads,setPendingUploads]=useState(null);
  const [uploadProgress,setUploadProgress]=useState('');
  const [tripForm,setTripForm]=useState({
    pickup_location:'',dropoff_location:'',date:'',time:'',
    fare:'',distance_km:'',duration_min:'',rider_name:'',counterparty_id:'',rider_rating:''
  });

  useEffect(()=>{
    setTrips(getTrips(identity));
  },[identity]);

  // Auto-connect on mount
  useEffect(()=>{
    api.run(connect);
  },[api.key]);

  async function connect(){
    await api.call('health');
    const list=await api.call('cases');
    setCases(list);
    setTrips(getTrips(identity));
    setConnected(true);
  }

  async function selectCase(id){
    setDetail(await api.call('cases/'+id));
  }

  function selectTrip(trip){
    setSelectedTrip(trip);
    setTab('trips');
  }

  function reportTrip(tripId=''){
    setForm({category:'property_damage',trip_id:tripId,description:'',dispute_amount:''});
    setFormError('');setDetail(null);setShowForm(true);setTab('disputes');
    setUploadFile(null);setReportFiles([]);api.clear();
  }

  function chooseReportFiles(e){
    const selected=Array.from(e.target.files||[]);
    e.target.value='';
    const error=validateAttachments(selected);
    if(error){setFormError(error);return;}
    setFormError('');
    setReportFiles(previous=>[...previous,...selected.filter(file=>!previous.some(
      existing=>existing.name===file.name&&existing.size===file.size&&existing.lastModified===file.lastModified))]);
  }

  async function uploadFilesForCase(caseId,files){
    const failed=await uploadReportAttachments(api.call,caseId,files,
      (index,total)=>setUploadProgress(`Uploading attachment ${index} of ${total}. Image analysis may take a moment…`));
    setUploadProgress('');
    setPendingUploads(failed.length?{caseId,failed}:null);
    api.setNotice(failed.length?`Report saved. ${failed.length} attachment(s) need retry below.`:
      `Report saved. ${files.length} attachment(s) uploaded.`);
    setDetail(await api.call('cases/'+caseId));
  }

  async function submitCase(e){
    e.preventDefault();
    if(api.busy)return;
    const description=form.description.trim();
    if(!form.trip_id.trim()||description.length<5||description.length>3000){
      setFormError('Enter a trip reference and a description of 5–3000 characters.');return;
    }
    const amount=form.dispute_amount===''?null:Number(form.dispute_amount);
    if(amount!==null&&(!Number.isFinite(amount)||amount<0||amount>100000)){
      setFormError('Enter an amount between SGD 0 and 100,000.');return;
    }
    const attachmentError=validateAttachments(reportFiles);
    if(attachmentError){setFormError(attachmentError);return;}
    setFormError('');
    await api.run(async()=>{
      const case_id='DRIVER-'+crypto.randomUUID();
      const created=await api.call('cases',{method:'POST',body:{
        case_id,trip_id:form.trip_id.trim(),category:form.category,filed_by:'driver',
        description,dispute_amount:amount,synthetic:true,
        counterparty_id:findTrip(identity,form.trip_id.trim())?.counterparty_id||null,
      }});
      // Show the saved case immediately, even if refreshing the queue fails.
      setDetail(created);setShowForm(false);setUploadFile(null);
      const files=reportFiles;
      setReportFiles([]);
      api.setNotice(`Case ${case_id} created.`);
      if(files.length) await uploadFilesForCase(case_id,files);
      setCases(await api.call('cases'));
    });
  }

  function createTrip(){
    const fare=parseFloat(tripForm.fare);
    const distance=parseFloat(tripForm.distance_km);
    const duration=parseInt(tripForm.duration_min,10);
    const now=new Date();
    const trip={
      trip_id:`TRIP-${now.toISOString().slice(0,10).replace(/-/g,'')}-${String.fromCharCode(65+trips.length)}${randInt(100,999)}`,
      date:tripForm.date||now.toISOString().slice(0,10),
      time:tripForm.time||now.toTimeString().slice(0,5),
      pickup_location:tripForm.pickup_location||rand(SINGAPORE_AREAS),
      dropoff_location:tripForm.dropoff_location||rand(SINGAPORE_AREAS),
      pickup_lat:1.35+randBetween(-0.06,0.06),
      pickup_lng:103.82+randBetween(-0.08,0.08),
      dropoff_lat:1.35+randBetween(-0.06,0.06),
      dropoff_lng:103.82+randBetween(-0.08,0.08),
      distance_km:isNaN(distance)?Number(randBetween(3,12).toFixed(1)):distance,
      duration_min:isNaN(duration)?randInt(10,40):duration,
      fare:isNaN(fare)?Number(randBetween(8,35).toFixed(2)):fare,
      currency:'SGD',
      counterparty_id:tripForm.counterparty_id||null,
      rider_name:tripForm.counterparty_id?'Rider '+tripForm.counterparty_id.slice(-1).toUpperCase():(tripForm.rider_name||'Custom Rider'),
      rider_rating:isNaN(parseFloat(tripForm.rider_rating))?4.8:parseFloat(tripForm.rider_rating),
      status:'completed',
      payment_method:'Credit card',
      identity_id:identity,
      perspective:'driver',
    };
    const updated=addTrip(identity,trip);
    setTrips(updated);
    setShowTripForm(false);
    setTripForm({pickup_location:'',dropoff_location:'',date:'',time:'',fare:'',distance_km:'',duration_min:'',rider_name:'',counterparty_id:'',rider_rating:''});
    setSelectedTrip(trip);
    api.setNotice(`Trip ${trip.trip_id} created. Synthetic only.`);
  }

  const outcome=outcomeExplanation(detail);
  const pendingClarifications=detail?.clarifications?.filter(c=>c.status==='PENDING'&&c.recipient==='driver')||[];
  const actionNeededCases=cases.filter(c=>c.status==='AWAITING_CLARIFICATION');
  const activeCases=cases.filter(c=>c.status!=='RESOLVED'&&c.status!=='REVIEWED_AND_RESOLVED');
  const caseTrip=detail?findTrip(identity,detail.trip_id):null;

  // --- Loading (only while connecting, not when cases is empty) ---
  if(!connected){
    return <div className="app-shell">
      <div className="app-connect driver">
        <div className="app-logo-big">D</div>
        <h2>RydeResolve Driver</h2>
        <p>{api.error?'Unable to load your cases.':'Loading your disputes and trip history…'}</p>
        {api.error&&<button disabled={api.busy} onClick={()=>api.run(connect)}>Retry</button>}
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
      <select aria-label="Switch driver" disabled={api.busy} value={identity} onChange={e=>{setIdentity(e.target.value);api.setKey(e.target.value);setCases([]);setDetail(null);setShowForm(false);setSelectedTrip(null);setUploadFile(null);setReportFiles([]);setPendingUploads(null);setConnected(false)}} style={{padding:'6px 10px',borderRadius:'8px',border:'1px solid var(--border)'}}>
        <option value="driver_a">Driver A</option>
        <option value="driver_b">Driver B</option>
      </select>
    </header>

    {api.error&&<div className="alert error" role="alert" style={{margin:'0 12px'}}>{api.error}</div>}
    {api.notice&&<div className="alert success" style={{margin:'0 12px'}}>{api.notice}</div>}

    <div className="app-body">
      {tab==='disputes'&&!detail&&!showForm&&<>
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
        <div className="app-section-head"><h2>Your disputes</h2><button onClick={()=>reportTrip()}>Report an issue</button></div>
        {cases.length===0?
          <div className="card empty" style={{padding:'40px 16px'}}><div className="empty-symbol">📋</div><h2>No disputes</h2><p>No cases involving you at this time.</p></div>
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
          <button className="secondary" disabled={api.busy} onClick={()=>setDetail(null)}>← Back</button>
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

        {/* Trip info for dispute */}
        {caseTrip&&<div className="card trip-card">
          <p className="eyebrow">TRIP DETAILS</p>
          <div className="trip-row">
            <span className="trip-time">{formatTripDateTime(caseTrip)}</span>
            <span className="trip-fare">{formatFare(caseTrip)}</span>
          </div>
          <MapView trip={caseTrip} height={140} />
          <div className="trip-meta">
            <span>{caseTrip.distance_km.toFixed(1)} km</span>
            <span>{caseTrip.duration_min} min</span>
            <span>{caseTrip.payment_method}</span>
          </div>
          {caseTrip.perspective==='driver'&&caseTrip.rider_name&&<div className="trip-driver">
            <strong>{caseTrip.rider_name}</strong>
            <span>Rider rating {caseTrip.rider_rating}</span>
          </div>}
        </div>}

        {/* Attachments */}
        <div className="card">
          <p className="eyebrow">ATTACHMENTS</p>
          {uploadProgress&&<p role="status" aria-live="polite">{uploadProgress}</p>}
          {pendingUploads?.caseId===detail.case_id&&<div className="alert error" role="alert">
            <p>Your report is saved. These attachments were not confirmed uploaded:</p>
            <ul>{pendingUploads.failed.map(({file,error},index)=><li key={index}>{file.name}: {error}</li>)}</ul>
            <button type="button" disabled={api.busy} onClick={()=>api.run(()=>uploadFilesForCase(detail.case_id,pendingUploads.failed.map(item=>item.file)))}>Retry failed attachments</button>
          </div>}
          {detail.evidence?.filter(e=>e.type==='image_or_document').length>0?
            <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
              {detail.evidence.filter(e=>e.type==='image_or_document').map(ev=>{
                const ref=ev.content?.object_ref||'';
                const sha=ev.content?.sha256||'';
                const ct=ev.content?.content_type||'';
                const isImg=ct.includes('image');
                return <div key={ev.id} style={{display:'flex',alignItems:'center',gap:'8px',padding:'8px',border:'1px solid var(--border)',borderRadius:'8px'}}>
                  <span style={{fontSize:'20px'}}>{ct.includes('pdf')?'📄':isImg?'🖼':'📎'}</span>
                  <div style={{flex:1}}>
                    <div style={{fontSize:'13px',fontWeight:600}}>{ev.id}</div>
                    <div style={{fontSize:'11px',color:'var(--ink-secondary)'}}>{ct} · {ev.content?.size_bytes?Math.round(ev.content.size_bytes/1024)+'KB':'—'}</div>
                  </div>
                  <button className="small secondary" onClick={()=>window.open('/api/proxy/cases/'+detail.case_id+'/files/'+sha.slice(0,24),'_blank')}>View</button>
                </div>;
              })}
            </div>
          :<p className="muted" style={{fontSize:'13px'}}>No attachments yet.</p>}
          {detail.status!=='RESOLVED'&&detail.status!=='REVIEWED_AND_RESOLVED'&&<div style={{marginTop:'8px'}}>
            <input aria-label="Upload attachment" type="file" accept="image/png,image/jpeg,application/pdf" onChange={e=>setUploadFile(e.target.files?.[0]||null)} style={{fontSize:'12px'}}/>
            <button className="small" disabled={api.busy||!uploadFile} style={{marginTop:'6px'}} onClick={()=>api.run(async()=>{
              const form=new FormData();form.append('file',uploadFile);
              await api.call('cases/'+detail.case_id+'/files',{method:'POST',body:form});
              setDetail(await api.call('cases/'+detail.case_id));
              setUploadFile(null);
              api.setNotice('Attachment uploaded. Authenticity unverified.');
            })}>{api.busy?'Uploading…':'Upload'}</button>
          </div>}
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

      {tab==='disputes'&&showForm&&<>
        <div className="app-section-head">
          <button className="secondary" disabled={api.busy} onClick={()=>setShowForm(false)}>← Cancel</button>
        </div>
        <form className="app-form" onSubmit={submitCase}>
          <h2>Report an issue</h2>
          <p className="muted">Use synthetic test information only. Attach photos or documents below; they will upload when you submit your report.</p>
          <label htmlFor="driver-category">Dispute category</label>
          <select id="driver-category" disabled={api.busy} value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>
            {['property_damage','fare_dispute','route_deviation','no_show_charge','driver_no_show','safety_incident','other'].map(category=><option key={category} value={category}>{categoryLabel(category)}</option>)}
          </select>
          <label htmlFor="driver-past-trip">Choose a past trip</label>
          <select id="driver-past-trip" disabled={api.busy} value={trips.some(t=>t.trip_id===form.trip_id)?form.trip_id:''} onChange={e=>setForm({...form,trip_id:e.target.value})}>
            <option value="">Select a trip or enter its reference below…</option>
            {trips.map(t=><option key={t.trip_id} value={t.trip_id}>{t.trip_id} · {t.pickup_location} → {t.dropoff_location}</option>)}
          </select>
          <label htmlFor="driver-trip-reference">Trip reference</label>
          <input id="driver-trip-reference" required disabled={api.busy} value={form.trip_id} onChange={e=>setForm({...form,trip_id:e.target.value})}/>
          <p className="muted">{findTrip(identity,form.trip_id.trim())?.counterparty_id?'Linked Rider: '+findTrip(identity,form.trip_id.trim()).counterparty_id.slice(-1).toUpperCase()+' — this dispute will appear in their portal.':'Custom / unlinked trip — no rider will receive this dispute.'}</p>
          <label htmlFor="driver-description">Description ({form.description.length}/3000)</label>
          <textarea id="driver-description" required minLength={5} maxLength={3000} disabled={api.busy} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Describe the seat stain or other issue, when you noticed it, and the remedy you are requesting."/>
          <label htmlFor="driver-amount">Disputed amount (SGD, optional)</label>
          <input id="driver-amount" type="number" min="0" max="100000" step="0.01" disabled={api.busy} value={form.dispute_amount} onChange={e=>setForm({...form,dispute_amount:e.target.value})}/>
          <label htmlFor="driver-report-attachments">Photos and documents (optional)</label>
          <input id="driver-report-attachments" type="file" multiple accept="image/png,image/jpeg,application/pdf" disabled={api.busy} onChange={chooseReportFiles}/>
          <p className="muted">PNG, JPEG, or PDF · Up to 5 MB per file. Images are submitted for analysis after the report is saved.</p>
          {reportFiles.length>0&&<ul>{reportFiles.map((file,index)=><li key={index}>
            {file.name} ({Math.ceil(file.size/1024)} KB) <button type="button" className="small secondary" disabled={api.busy} aria-label={'Remove '+file.name} onClick={()=>setReportFiles(files=>files.filter((_,i)=>i!==index))}>Remove</button>
          </li>)}</ul>}
          {form.category==='safety_incident' &&<p className="alert error">Safety allegations require human review. AI will not determine fault.</p>}
          {formError&&<div className="alert error" role="alert">{formError}</div>}
          <button type="submit" disabled={api.busy}>{api.busy?'Saving report…':reportFiles.length?'Submit report & upload':'Submit report'}</button>
        </form>
      </>}

      {/* Tab: Trips */}
      {tab==='trips'&&!selectedTrip&&!showTripForm&&<>
        <div className="app-section-head">
          <h2>Your trips</h2>
          <button onClick={()=>setShowTripForm(true)}>Add trip</button>
        </div>
        {trips.length===0?
          <div className="card empty" style={{padding:'40px 16px'}}><div className="empty-symbol">🚗</div><h2>No trips yet</h2><p>Synthetic trips will appear here. Tap "Add trip" to create one.</p></div>
        :trips.map(trip=><div key={trip.trip_id} className="app-case-card" onClick={()=>selectTrip(trip)} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==='Enter')selectTrip(trip)}}>
          <div className="acc-top">
            <strong>{trip.trip_id}</strong>
            <span className="trip-fare-inline">{formatFare(trip)}</span>
          </div>
          <div className="acc-cat">{formatTripDateTime(trip)}</div>
          <div className="trip-list-route">{trip.pickup_location} → {trip.dropoff_location}</div>
        </div>)}
      </>}

      {/* Tab: Trips — detail */}
      {tab==='trips'&&selectedTrip&&!showTripForm&&<>
        <div className="app-section-head">
          <button className="secondary" onClick={()=>setSelectedTrip(null)}>← Back</button>
        </div>
        <div className="card trip-card">
          <p className="eyebrow">TRIP</p>
          <div className="trip-header">
            <h3>{selectedTrip.trip_id}</h3>
            <span className="trip-status completed">Completed</span>
          </div>
          <div className="trip-row">
            <span className="trip-time">{formatTripDateTime(selectedTrip)}</span>
            <span className="trip-fare">{formatFare(selectedTrip)}</span>
          </div>
          <p className="muted">{selectedTrip.counterparty_id?'Linked Rider: '+selectedTrip.counterparty_id.slice(-1).toUpperCase():'Custom — no linked rider'}</p>
          <MapView trip={selectedTrip} height={180} />
          <div className="trip-locations">
            <div className="trip-location pickup">
              <span className="trip-dot"/>
              <div>
                <div className="trip-loc-label">Pickup</div>
                <div className="trip-loc-name">{selectedTrip.pickup_location}</div>
              </div>
            </div>
            <div className="trip-location dropoff">
              <span className="trip-dot"/>
              <div>
                <div className="trip-loc-label">Drop-off</div>
                <div className="trip-loc-name">{selectedTrip.dropoff_location}</div>
              </div>
            </div>
          </div>
          <div className="trip-meta">
            <span>{selectedTrip.distance_km.toFixed(1)} km</span>
            <span>{selectedTrip.duration_min} min</span>
            <span>{selectedTrip.payment_method}</span>
          </div>
          <button style={{marginTop:'12px'}} onClick={()=>reportTrip(selectedTrip.trip_id)}>Report an issue with this trip</button>
          {selectedTrip.perspective==='driver'&&selectedTrip.rider_name&&<div className="trip-driver">
            <strong>{selectedTrip.rider_name}</strong>
            <span>Rider rating {selectedTrip.rider_rating}</span>
          </div>}
        </div>
      </>}

      {/* Tab: Trips — add form */}
      {tab==='trips'&&showTripForm&&<>
        <div className="app-section-head">
          <button className="secondary" onClick={()=>setShowTripForm(false)}>← Cancel</button>
        </div>
        <div className="app-form">
          <h2 style={{fontSize:'18px',marginBottom:'8px'}}>Add a synthetic trip</h2>
          <p className="muted" style={{marginBottom:'12px'}}>Only synthetic demo data. Fill in a few details or leave fields blank for random values.</p>
          <label>Pickup location</label>
          <select value={tripForm.pickup_location} onChange={e=>setTripForm({...tripForm,pickup_location:e.target.value})}>
            <option value="">Select pickup…</option>
            {SINGAPORE_AREAS.map(a=><option key={a} value={a}>{a}</option>)}
          </select>
          <label>Drop-off location</label>
          <select value={tripForm.dropoff_location} onChange={e=>setTripForm({...tripForm,dropoff_location:e.target.value})}>
            <option value="">Select drop-off…</option>
            {SINGAPORE_AREAS.map(a=><option key={a} value={a}>{a}</option>)}
          </select>
          <label>Date</label>
          <input type="date" value={tripForm.date} onChange={e=>setTripForm({...tripForm,date:e.target.value})}/>
          <label>Time</label>
          <input type="time" value={tripForm.time} onChange={e=>setTripForm({...tripForm,time:e.target.value})}/>
          <label>Fare (SGD)</label>
          <input type="number" min="0" step="0.01" value={tripForm.fare} onChange={e=>setTripForm({...tripForm,fare:e.target.value})} placeholder="e.g. 15.50"/>
          <label>Distance (km)</label>
          <input type="number" min="0" step="0.1" value={tripForm.distance_km} onChange={e=>setTripForm({...tripForm,distance_km:e.target.value})} placeholder="e.g. 8.5"/>
          <label>Duration (min)</label>
          <input type="number" min="1" value={tripForm.duration_min} onChange={e=>setTripForm({...tripForm,duration_min:e.target.value})} placeholder="e.g. 25"/>
          <label htmlFor="driver-trip-counterparty">Link to rider</label>
          <select id="driver-trip-counterparty" value={tripForm.counterparty_id} onChange={e=>setTripForm({...tripForm,counterparty_id:e.target.value})}>
            <option value="">Custom (no linked rider)</option>
            <option value="rider_a">Rider A</option>
            <option value="rider_b">Rider B</option>
          </select>
          <p className="muted">A linked rider can see disputes filed for this trip and respond to reviewer requests. Custom trips have no linked rider.</p>
          <label>Rider name (Custom only)</label>
          <input disabled={!!tripForm.counterparty_id} value={tripForm.rider_name} onChange={e=>setTripForm({...tripForm,rider_name:e.target.value})} placeholder="e.g. Jane Doe"/>
          <label>Rider rating</label>
          <input type="number" min="1" max="5" step="0.1" value={tripForm.rider_rating} onChange={e=>setTripForm({...tripForm,rider_rating:e.target.value})} placeholder="e.g. 4.8"/>
          <button onClick={()=>createTrip()}>Create trip</button>
        </div>
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
      {NAV_TABS.map(t=><button key={t.id} disabled={api.busy} className={tab===t.id?'active':''} onClick={()=>{setTab(t.id);setDetail(null);setSelectedTrip(null);setShowTripForm(false);setShowForm(false)}} aria-label={t.label}>
        <span className="nav-icon">{t.icon}</span>
        {t.label}
      </button>)}
    </nav>

    <div className="demo-badge">SYNTHETIC DEMO</div>
  </div>;
}
