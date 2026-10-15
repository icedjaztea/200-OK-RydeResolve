// Server-side proxy: browsers never need to know backend network address.
// The backend still independently authorizes every request from X-Demo-Key.
async function forward(request,{params}) {
  const parts = (await params).path || [];
  if(parts.some(s=>s==='..' || s.includes('/') || s.includes('\\'))) return new Response('Invalid path',{status:400});
  const backend = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/,'');
  const path = parts.map(s=>encodeURIComponent(s)).join('/');
  const url = `${backend}/${path}${new URL(request.url).search}`;
  const headers = {};
  const key=request.headers.get('x-demo-key');
  const ct=request.headers.get('content-type');
  if(key) headers['X-Demo-Key']=key;
  if(ct) headers['Content-Type']=ct;
  try {
    const resp=await fetch(url,{method:request.method,headers,
      body:['POST','PUT','PATCH'].includes(request.method)?await request.arrayBuffer():undefined,
      cache:'no-store',redirect:'manual'});
    const body=await resp.arrayBuffer();
    return new Response(body,{status:resp.status,headers:{'content-type':resp.headers.get('content-type')||'application/json','cache-control':'no-store'}});
  }catch(e){return Response.json({error:'Backend unreachable. Confirm FastAPI is running and BACKEND_URL is correct.'},{status:502});}
}
export async function GET(req,ctx){return forward(req,ctx)}
export async function POST(req,ctx){return forward(req,ctx)}
