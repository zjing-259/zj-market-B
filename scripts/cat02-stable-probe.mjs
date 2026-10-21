/** Readiness independent of any fixed goods ID or catalogue contents. */
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import {randomUUID} from 'node:crypto'

export function transport({ca,origin='https://zj-market.test'}){
 const url=new URL(origin)
 if(!['https://zj-market.test','https://zj-market-ux.test:8446'].includes(origin))throw Error('Owned HTTPS origin required')
 let cookie=''
 return async function request(route,method='GET',body,token,csrf){
  return new Promise((resolve,reject)=>{
   const req=https.request({hostname:url.hostname,port:url.port||443,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:cookie,...(token?{Authorization:'Bearer '+token}:{}),...(csrf?{[csrf.headerName]:csrf.token}:{})}},res=>{
    const tlsAuthorized=res.socket.authorized
    if(res.headers['set-cookie']?.length)cookie=res.headers['set-cookie'].map(v=>v.split(';')[0]).join('; ')
    let raw='';res.on('data',v=>raw+=v);res.on('end',()=>{try{resolve({status:res.statusCode,payload:JSON.parse(raw),tlsAuthorized,contentType:String(res.headers['content-type']??''),retryAfter:res.headers['retry-after']})}catch{reject(Error('Non-JSON readiness response'))}})
   });req.on('error',()=>reject(Error('Readiness HTTPS transport failed')));req.setTimeout(15000,()=>req.destroy());if(body!==undefined)req.write(JSON.stringify(body));req.end()
  })
 }
}
function valid(r){return r.tlsAuthorized&&r.contentType.includes('application/json')}
function ok(r,label){if(!valid(r)||r.status!==200||r.payload.code!=='0000')throw Error(label+' readiness failed')}
export async function checkReadiness(request,buyer,{teamId=randomUUID()}={}){
 if(!/^[a-f0-9-]{36}$/.test(teamId))throw Error('Valid random team query ID required')
 const csrf=await request('/auth/csrf');ok(csrf,'CSRF')
 const login=await request('/auth/login','POST',{loginName:buyer.loginName,password:buyer.password},undefined,csrf.payload.data);ok(login,'Identity')
 const token=login.payload.data?.accessToken;if(typeof token!=='string'||!token)throw Error('Access token missing')
 const mode=await request('/system/status');ok(mode,'Gateway');if(mode.payload.data?.mode!=='NORMAL')throw Error('Gateway is not NORMAL')
 const catalogue=await request('/products?page=1&size=20');ok(catalogue,'Catalogue')
 const page=catalogue.payload.data
 if(!Array.isArray(page?.items)||!Number.isInteger(page.total)||page.total<page.items.length||page.items.length>20||page.page!==1||page.size!==20)throw Error('Catalogue contract invalid')
 // This endpoint calls signed A TeamService.query before looking up any B product/order.
 const peer=await request('/teams/'+teamId,'GET',undefined,token)
 if(!valid(peer)||peer.status!==404||peer.payload.code!=='TEAM_NOT_FOUND')throw Error('Signed team readiness failed')
 // When products exist, retain the discovery route check without pinning one SKU.
 const candidate=page.items.find(p=>p.syncReady&&p.availability==='IN_STOCK'&&/^[a-f0-9-]{36}$/.test(p.goodsId))
 let discovery='SKIPPED_NO_ELIGIBLE_PRODUCT'
 if(candidate){const r=await request('/products/'+candidate.goodsId+'/joinable-teams','GET',undefined,token);ok(r,'Discovery');discovery=r.status}
 // No bearer token: authenticated cookies alone cannot authorize a write.
 const invalid=await request('/orders','POST',{})
 if(!valid(invalid)||invalid.status!==401||invalid.payload.code!=='AUTH_REQUIRED')throw Error('Invalid-write readiness failed')
 return{status:'STABLE_PROBE_PASS',contract:'sku-independent-signed-team-query-v1',catalogue:catalogue.status,catalogueTotal:page.total,signedTeam:peer.status,signedTeamCode:peer.payload.code,probeTeamId:teamId,discovery,invalidWrite:invalid.status,tlsAuthorized:true}
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(import.meta.filename)){
 try{
  const [caPath,accountPath,...extra]=process.argv.slice(2)
  if(!caPath||!accountPath||extra.length)throw Error('Two private input paths required; no goods seed accepted')
  const buyer=JSON.parse(fs.readFileSync(accountPath,'utf8')).b06buyer
  if(!buyer?.loginName||!buyer?.password)throw Error('Buyer input invalid')
  console.log(JSON.stringify(await checkReadiness(transport({ca:fs.readFileSync(caPath)}),buyer)))
 }catch(e){process.stderr.write('READINESS_FAILED '+e.message+'\n');process.exitCode=1}
}
