'use client';
import {useRef,useState} from 'react';
import {validateAttachments,uploadReportAttachments} from './reportAttachments';
import {statusLabel,dispositionLabel} from './labels';

export default function AppealPanel({detail,api,role,onOpen}){
  const [open,setOpen]=useState(false);
  const [reason,setReason]=useState('');
  const [files,setFiles]=useState([]);
  const [saved,setSaved]=useState(null);
  const [failed,setFailed]=useState([]);
  const [message,setMessage]=useState('');
  const submitting=useRef(false);
  const resolved=['RESOLVED','REVIEWED_AND_RESOLVED'].includes(detail.status);
  const existing=detail.appeals?.find(a=>a.filed_by===role);
  async function submit(e){
    e.preventDefault();
    if(submitting.current)return;
    const invalid=validateAttachments(files);
    if(invalid){setMessage(invalid);return;}
    submitting.current=true;
    try{await api.run(async()=>{
      const appeal=saved||await api.call(`cases/${detail.case_id}/appeals`,{method:'POST',body:{reason:reason.trim()}});
      setSaved(appeal);
      const retry=await uploadReportAttachments(api.call,appeal.case_id,saved?failed.map(x=>x.file):files,
        (i,n)=>setMessage(`Uploading ${i} of ${n}. Checking the image…`));
      setFailed(retry);
      if(retry.length){setMessage('Your appeal is saved. Retry the remaining files below; no new appeal will be created.');return;}
      setMessage('Appeal submitted.');
      await onOpen(appeal.case_id);
    });}finally{submitting.current=false;}
  }
  if(!resolved&&!detail.appeal_of&&!detail.appeals?.length)return null;
  return <section className="card appeal-panel">
    {detail.appeal_of&&<>
      <p className="eyebrow">APPEAL</p>
      <h3>Reviewing an earlier decision</h3>
      <p>The earlier decision and evidence remain on record. New files and responses belong to this appeal.</p>
      {detail.original_decision&&<p>Earlier outcome: <b>{dispositionLabel(detail.original_decision.disposition)}</b> · SGD {Number(detail.original_decision.amount||0).toFixed(2)}</p>}
      <button type="button" className="secondary" disabled={api.busy} onClick={()=>api.run(()=>onOpen(detail.appeal_of))}>View original case</button>
    </>}
    {detail.appeals?.length>0&&<div><h3>Linked appeals</h3>{detail.appeals.map(a=><p key={a.case_id}><button type="button" className="secondary" disabled={api.busy} onClick={()=>api.run(()=>onOpen(a.case_id))}>View {a.filed_by} appeal · {statusLabel(a.status)}</button></p>)}</div>}
    {resolved&&['driver','rider'].includes(role)&&(!existing||saved)&&<>
      <h3>Disagree with the decision?</h3>
      <p>Explain what should be reconsidered. Your original evidence is included automatically. You can add new photos or documents. The other linked party will be asked to respond before a reviewer decides.</p>
      {!open?<button type="button" disabled={api.busy} onClick={()=>setOpen(true)}>Appeal decision</button>:<form className="app-form" onSubmit={submit}>
        <label htmlFor="appeal-reason">Why should we reconsider?</label>
        <textarea id="appeal-reason" required minLength={10} maxLength={3000} value={reason} disabled={api.busy||!!saved} onChange={e=>setReason(e.target.value)} placeholder="Explain what was missed or what new evidence changes the decision."/>
        <label htmlFor="appeal-files">New photos or documents (optional)</label>
        <input id="appeal-files" type="file" multiple accept="image/png,image/jpeg,application/pdf" disabled={api.busy||!!saved} onChange={e=>{setFiles(Array.from(e.target.files||[]));setMessage('')}}/>
        <p className="muted">PNG, JPEG or PDF · Up to 5 MB each. You can also add files from the appeal after submission.</p>
        {files.length>0&&<ul>{files.map((f,i)=><li key={i}>{f.name}</li>)}</ul>}
        {message&&<p role="status">{message}</p>}
        {failed.length>0&&<ul>{failed.map((f,i)=><li key={i}>{f.file.name}: {f.error}</li>)}</ul>}
        <div className="appeal-actions"><button type="submit" disabled={api.busy||reason.trim().length<10}>{api.busy?'Submitting…':saved?'Retry remaining files':'Submit appeal'}</button>
        {saved?<button type="button" className="secondary" disabled={api.busy} onClick={()=>api.run(()=>onOpen(saved.case_id))}>Open saved appeal</button>:<button type="button" className="secondary" disabled={api.busy} onClick={()=>setOpen(false)}>Cancel</button>}</div>
      </form>}
    </>}
  </section>;
}
