'use client';
import {useState,useCallback,useEffect} from 'react';

/**
 * Shared API hook — wraps the /api/proxy pattern used across all portals.
 * Open access: no passcode needed. The key is auto-set based on the page.
 */
export function useApi(defaultKey='rider'){
  const [key,setKey]=useState(defaultKey);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');

  useEffect(()=>{ if(!key) setKey(defaultKey); },[key,defaultKey]);

  const call=useCallback(async(path,opts={})=>{
    const k=key||defaultKey;
    const headers={'X-Demo-Key':k,...opts.headers};
    if(opts.body && !(opts.body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch('/api/proxy/'+path,{method:opts.method||'GET',headers,
      body:opts.body instanceof FormData?opts.body:opts.body?JSON.stringify(opts.body):undefined});
    let data;try{data=await response.json()}catch{data={detail:`HTTP ${response.status}`}}
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data));
    return data;
  },[key,defaultKey]);

  async function run(fn){
    setBusy(true);setError('');setNotice('');
    try{await fn()}catch(e){setError(e.message)}finally{setBusy(false)}
  }

  function clear(){setError('');setNotice('')}

  return {key,setKey,call,run,busy,error,notice,setError,setNotice,clear};
}
