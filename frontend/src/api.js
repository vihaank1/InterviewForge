const ROOT=(import.meta.env.VITE_API_URL||'http://127.0.0.1:8000').replace(/\/$/,'');
export async function api(path, options={}) {
 let res;
 try {res=await fetch(ROOT+'/api'+path,{method:options.body?'POST':'GET',headers:{'Content-Type':'application/json'},body:options.body?JSON.stringify(options.body):undefined});}
 catch {throw new Error('Cannot reach the backend. Start FastAPI at '+ROOT);}
 const data=await res.json().catch(()=>({}));
 if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'Request failed ('+res.status+')');
 return data;
}
export function post(path,body={}){return api(path,{body});}
