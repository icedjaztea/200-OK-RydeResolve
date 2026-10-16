'use client';
import {useState,useEffect} from 'react';
import Link from 'next/link';
import {useApi} from '../../lib/useApi';
import {CaseTimeline} from '../../lib/Timeline';
import MapView from '../../lib/MapView';
import {getTrips,addTrip,findTrip,formatTripDateTime,formatFare} from '../../lib/trips';
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
  {value:'other',label:'Other / I\u2019m not sure'},
];

const SINGAPORE_AREAS = [
  'Orchard Road','Marina Bay','Tampines','Jurong East','Ang Mo Kio',
  'Bedok','Clementi','Bishan','Paya Lebar','Holland Village',
  'Sentosa','Changi Airport','Sengkang','Punggol','Woodlands',
  'Yishun','Serangoon','Kallang','Geylang','Novena',
];

function genCaseId(){
  const ts=Date.now().toString(36).toUpperCase().slice(-6);
  const rnd=Math.random().toString(36).toUpperCase().slice(2,6);
  return `RIDER-${ts}-${rnd}`;
}

function rand(items){return items[Math.floor(Math.random()*items.length)];}
function randBetween(min,max){return Math.random()*(max-min)+min;}
function randInt(min,max){return Math.floor(Math.random()*(max-min+1))+min;}

const NAV_TABS = [
  {id:'cases',label:'My Cases',icon:'📋'},
  {id:'trips',label:'Trips',icon:'🚗'},
  {id:'report',label:'Report',icon:'➕'},
  {id:'account',label:'Account',icon:'⚙'},
];

export default function RiderPortal(){
  const api=useApi('rider_a');
  const [cases,setCases]=useState([]);
  const [detail,setDetail]=useState(null);
  const [tab,setTab]=useState('cases');
  const [answer,setAnswer]=useState('');
  const [showForm,setShowForm]=useState(false);
  const [trips,setTrips]=useState([]);
  const [selectedTrip,setSelectedTrip]=useState(null);
  const [showTripForm,setShowTripForm]=useState(false);
  const [identity,setIdentity]=useState('rider_a');

  // Trip creation form
  const [tripForm,setTripForm]=useState({
    pickup_location:'',dropoff_location:'',date:'',time:'',
    fare:'',distance_km:'',duration_min:'',driver_name:'',vehicle_info:''
  });

  // Report form
  const [form,setForm]=useState({category:'',trip_id:'',description:'',dispute_amount:''});
  const [formError,setFormError]=useState('');
  const [formBusy,setFormBusy]=useState(false);

  useEffect(()=>{
    setTrips(getTrips(identity));
  },[identity]);

  // Auto-connect on mount
  useEffect(()=>{
    api.run(connect);
  },[]);

  async function connect(){
    await api.call('health');
    const list=await api.call('cases');
    setCases(list);
    setTrips(getTrips(identity));
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

  function selectTrip(trip){
    setSelectedTrip(trip);
    setTab('trips');
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
      driver_name:tripForm.driver_name||'Demo Driver',
      vehicle_info:tripForm.vehicle_info||'Toyota Corolla · SGY0000X',
      driver_rating:4.8,
      status:'completed',
      payment_method:'Credit card',
      identity_id:identity,
    };
    const updated=addTrip(identity,trip);
    setTrips(updated);
    setShowTripForm(false);
    setTripForm({pickup_location:'',dropoff_location:'',date:'',time:'',fare:'',distance_km:'',duration_min:'',driver_name:'',vehicle_info:''});
    setSelectedTrip(trip);
    api.setNotice(`Trip ${trip.trip_id} created. Synthetic only.`);
  }

  function validateForm(){
    if(!form.category) return 'Please select a dispute category.';
    if(!form.trip_id.trim()) return 'Please select or enter a trip reference.';
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

  const caseTrip=detail?findTrip(identity,detail.trip_id):null;

  // --- Loading screen ---
  if(!cases.length){
    return <div className="app-shell">
      <div className="app-connect">
        <div className="app-logo-big">R</div>
        <h2>RydeResolve Rider</h2>
        <p>Loading your disputes and trip history…</p>
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
      <select aria-label="Switch rider" value={identity} onChange={e=>{setIdentity(e.target.value);api.setKey(e.target.value);api.run(connect)}} style={{padding:'6px 10px',borderRadius:'8px',border:'1px solid var(--border)'}}>
        <option value="rider_a">Rider A</option>
        <option value="rider_b">Rider B</option>
      </select>
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
        :cases.map(item=>{
            const t=findTrip(identity,item.trip_id);
            return <div key={item.case_id} className={'app-case-card '+(detail?.case_id===item.case_id?'selected':'')} onClick={()=>api.run(()=>selectCase(item.case_id))} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==='Enter')api.run(()=>selectCase(item.case_id))}}>
              <div className="acc-top">
                <strong>{item.case_id}</strong>
                <em className={'status '+(TONES[item.status]||'neutral')}>{statusLabel(item.status)}</em>
              </div>
              <div className="acc-cat">{categoryLabel(item.category)}</div>
              {item.dispute_amount!=null&&<div className="acc-cat">SGD {Number(item.dispute_amount).toFixed(2)}</div>}
            </div>;
          })}
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
          <div className="trip-driver">
            <strong>{caseTrip.driver_name}</strong>
            <span>{caseTrip.vehicle_info}</span>
            <span>Rating {caseTrip.driver_rating}</span>
          </div>
        </div>}

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
          <button onClick={()=>{setForm({...form,trip_id:selectedTrip.trip_id});setShowForm(true);setTab('cases');}}>Report issue</button>
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
          <div className="trip-driver">
            <strong>{selectedTrip.driver_name}</strong>
            <span>{selectedTrip.vehicle_info}</span>
            <span>Rating {selectedTrip.driver_rating}</span>
          </div>
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
          <label>Driver name</label>
          <input value={tripForm.driver_name} onChange={e=>setTripForm({...tripForm,driver_name:e.target.value})} placeholder="e.g. Ahmad K."/>
          <label>Vehicle</label>
          <input value={tripForm.vehicle_info} onChange={e=>setTripForm({...tripForm,vehicle_info:e.target.value})} placeholder="e.g. Toyota Corolla · SGY1234A"/>
          <button onClick={()=>createTrip()}>Create trip</button>
        </div>
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
          <select value={form.trip_id.startsWith('TRIP-')?form.trip_id:''} onChange={e=>{
            const val=e.target.value;
            if(val==='manual') setForm({...form,trip_id:''});
            else setForm({...form,trip_id:val});
          }}>
            <option value="">Select a past trip…</option>
            {trips.map(t=><option key={t.trip_id} value={t.trip_id}>{t.trip_id} · {t.pickup_location} → {t.dropoff_location}</option>)}
            <option value="manual">Enter manually</option>
          </select>
          {(form.trip_id===''||form.trip_id==='manual')&&<input style={{marginTop:'8px'}} value={form.trip_id==='manual'?'':form.trip_id} onChange={e=>setForm({...form,trip_id:e.target.value})} placeholder="e.g. TRIP-2024-00123"/>}
          <label>Description ({form.description.length}/3000)</label>
          <textarea style={{minHeight:'100px'}} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Describe what happened during the trip…"/>
          <label>Disputed amount (SGD, optional)</label>
          <input type="number" min="0" step="0.01" max="100000" value={form.dispute_amount} onChange={e=>setForm({...form,dispute_amount:e.target.value})} placeholder="e.g. 15.50"/>
          {form.category==='safety_incident'&&<div className="alert error" style={{marginTop:'8px'}}>Safety allegations are escalated immediately. AI will not determine fault.</div>}
          {form.category==='other'&&<div className="alert" style={{marginTop:'8px',background:'var(--info-bg)',color:'var(--info-fg)',border:'1px solid var(--info-border)',padding:'10px 14px',borderRadius:'var(--r-md)'}}>Not sure which category fits? That\u2019s okay. Describe the situation in your own words and a reviewer will classify it for you. No automatic decision will be made until a human reviews it.</div>}
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
      {NAV_TABS.map(t=><button key={t.id} className={tab===t.id?'active':''} onClick={()=>{if(t.id==='report'){setShowForm(true);setTab('cases')}else{setTab(t.id);setShowForm(false);setDetail(null);setSelectedTrip(null);setShowTripForm(false)}}} aria-label={t.label}>
        <span className="nav-icon">{t.icon}</span>
        {t.label}
      </button>)}
    </nav>

    <div className="demo-badge">SYNTHETIC DEMO</div>
  </div>;
}
