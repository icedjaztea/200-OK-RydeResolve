// A slow response remains pending. Never turn a UI notice into a failed request.
export async function processCaseRequest(call,caseId,onSlow){
  const timer=setTimeout(onSlow,25000);
  try{return await call(`cases/${caseId}/process`,{method:'POST'});}
  finally{clearTimeout(timer);}
}
