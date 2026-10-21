import assert from 'node:assert/strict'
import {checkReadiness} from './cat02-stable-probe.mjs'
const product={goodsId:'0527e161-8ca8-4744-ba24-fd886536e5cf',syncReady:true,availability:'IN_STOCK'}
const good=data=>({status:200,payload:{code:'0000',data},tlsAuthorized:true,contentType:'application/json'})
function fake({items=[],peerStatus=404,peerCode='TEAM_NOT_FOUND',tls=true,mode='NORMAL',invalid=401}={}){
 const calls=[]
 const request=async(route,method='GET',body)=>{
  calls.push({route,method,body})
  if(route==='/auth/csrf')return good({headerName:'X-CSRF',token:'csrf'})
  if(route==='/auth/login')return good({accessToken:'test-only'})
  if(route==='/system/status')return good({mode})
  if(route.startsWith('/products?'))return good({items,total:items.length,page:1,size:20})
  if(route.startsWith('/teams/'))return{status:peerStatus,payload:{code:peerCode},tlsAuthorized:tls,contentType:'application/json'}
  if(route.endsWith('/joinable-teams'))return good({items:[]})
  if(route==='/orders')return{status:invalid,payload:{code:'AUTH_REQUIRED'},tlsAuthorized:true,contentType:'application/json'}
  throw Error('Unexpected request')
 };return{request,calls}
}
const buyer={loginName:'test-only',password:'test-only'}
let checks=0
for(const options of [{},{items:[product]},{items:[{...product,syncReady:false}]},{items:[{...product,availability:'OUT_OF_STOCK'}]}]){
 const f=fake(options),r=await checkReadiness(f.request,buyer);assert.equal(r.status,'STABLE_PROBE_PASS');assert(f.calls.some(x=>x.route.startsWith('/teams/')));assert(f.calls.filter(x=>x.method!=='GET').every(x=>['/auth/login','/orders'].includes(x.route)));checks++
}
for(const options of [{peerCode:'RESOURCE_NOT_FOUND'},{peerCode:'INTEGRATION_AUTH_FAILED',peerStatus:502},{peerCode:'DEPENDENCY_UNAVAILABLE',peerStatus:503},{peerStatus:200,peerCode:'0000'},{tls:false},{mode:'MAINTENANCE'},{invalid:200}]){await assert.rejects(checkReadiness(fake(options).request,buyer));checks++}
console.log('CAT02_PROBE_CONTRACT_PASS '+checks+' cases; empty catalogue and dependency/auth/TLS failures')
