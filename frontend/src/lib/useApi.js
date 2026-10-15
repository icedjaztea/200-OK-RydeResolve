'use client';
import {useState,useCallback} from 'react';

/**
 * Shared API hook — wraps the /api/proxy pattern used across all portals.
 * Stores the demo passcode in React state (never in URLs).
 * The backend independently authorizes every request via X-Demo-Key.
 */
export function useApi(){
  const [key,setKey]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');

  const call=useCallback(async(path,opts={})=>{
    if(!key)throw Error('Enter your demo passcode first.');
    const headers={'X-Demo-Key':key,...opts.headers};
    if(opts.body && !(opts.body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch('/api/proxy/'+path,{method:opts.method||'GET',headers,
      body:opts.body instanceof FormData?opts.body:opts.body?JSON.stringify(opts.body):undefined});
    let data;try{data=await response.json()}catch{data={detail:`HTTP ${response.status}`}}
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data));
    return data;
  },[key]);

  async function run(fn){
    setBusy(true);setError('');setNotice('');
    try{await fn()}catch(e){setError(e.message)}finally{setBusy(false)}
  }

  function clear(){setError('');setNotice('')}

  return {key,setKey,call,run,busy,error,notice,setError,setNotice,clear};
}
