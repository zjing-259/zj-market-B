import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const root=path.resolve(import.meta.dirname,'../..');
const control=process.argv[3]??path.join(root,'.local/b06/control');
const ca=fs.readFileSync(path.join(process.argv[4]??path.join(root,'.local/b06/runtime'),'web-ca.pem'));
const accounts=JSON.parse(fs.readFileSync(path.join(control,'demo-accounts.json')));
const mode=process.argv[2];
let token;const cookies=new Map();
function check(ok,message){if(!ok)throw new Error(message)}
function request(route,method='GET',body,extra={}){
 return new Promise((resolve,reject)=>{
  const req=https.request({hostname:'zj-market-ux.test',family:4,autoSelectFamily:false,port:8446,path:route,method,ca,rejectUnauthorized:true,
   lookup:(host,opts,callback)=>callback(null,'127.0.0.1',4),
   headers:{Origin:'https://zj-market-ux.test:8446','Content-Type':'application/json',Cookie:[...cookies].map(([k,v])=>k+'='+v).join('; '),...(token?{Authorization:'Bearer '+token}:{}),...extra}},res=>{
    check(res.socket.authorized,'TLS authorization');for(const c of res.headers['set-cookie']??[]){const first=c.split(';')[0],i=first.indexOf('=');cookies.set(first.slice(0,i),first.slice(i+1))}
    let raw='';res.on('data',b=>raw+=b);res.on('end',()=>{let data;try{data=JSON.parse(raw)}catch{data={raw}}resolve({status:res.statusCode,body:data,headers:res.headers})});
   });req.on('error',reject);req.setTimeout(15000,()=>req.destroy(new Error('HTTPS timeout')));if(body!==undefined)req.write(JSON.stringify(body));req.end();
 });
}
async function api(route,method='GET',body,expected=[200]){const r=await request('/api/v1'+route,method,body);check(expected.includes(r.status),'HTTP '+r.status+' '+route+' '+r.body.code);check(r.body.code==='0000','API '+route+' '+r.body.code);return r.body.data}
async function login(){const csrf=await api('/auth/csrf');const r=await request('/api/v1/auth/login','POST',accounts.b06buyer,{[csrf.headerName]:csrf.token});check(r.status===200,'Login '+r.status);token=r.body.data.accessToken;check(r.headers['set-cookie']?.some(x=>x.includes('Secure')&&x.includes('HttpOnly')),'Secure HttpOnly refresh cookie');}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(work,test,label){for(let i=0;i<45;i++){const value=await work();if(test(value))return value;await sleep(2000)}throw new Error('Timeout '+label)}
async function offer(){const goods=fs.readFileSync(path.join(control,'seed-goods-id.txt'),'utf8').trim();await until(()=>api('/products/'+goods),p=>p.syncReady,'product actual A acceptance');const result=await until(async()=>{const r=await request('/api/v1/products/'+goods+'/trial','POST',{});if(r.status===503&&r.body.code==='DEPENDENCY_UNAVAILABLE')return null;check(r.status===200&&r.body.code==='0000','Trial HTTP '+r.status+' '+r.body.code);return r.body.data},x=>x!==null,'A RPC readiness');check(result.state==='AVAILABLE'&&result.offer.payPrice==='90.00'&&result.offer.targetCount===2,'Authenticated A trial');return {goods,offer:result.offer}}
if(mode==='gateway'){
 for(const route of ['/purchase-confirmations','/orders','/orders;matrix=1','/orders/unknown/payment-attempts','/payments/unknown/attempts/unknown/simulated-results','/unknown-new-write']){const r=await request('/api/v1'+route,'POST',{});check(r.status===503,'Maintenance gate '+route)}
 const r=await request('/api/v1/orders/unknown/cancel','POST',{});check(r.status===401,'Cancellation reaches authentication');console.log('CLIENT_PASS maintenance-gates');
}else{
 await login();
 if(mode==='ready'){const result=await offer();console.log('CLIENT_PASS actual-sync-signed-trial-secure-identity '+result.goods)}
 else if(mode==='hold'){
  const result=await offer();const confirmation=await api('/purchase-confirmations','POST',{goodsId:result.goods,mode:'OPEN',expectedOffer:result.offer},[201]);
  const intent=randomUUID();const order=await api('/orders','POST',{purchaseIntentId:intent,confirmationId:confirmation.confirmationId},[202]);
  const held=await until(()=>api('/orders/'+order.orderId),o=>o.status==='WAITING_PAYMENT','A reservation');check(held.canCancel,'Unexposed payment cancellable');const payment=await api('/orders/'+order.orderId+'/payment');check(payment.canCreateAttempt,'Open backend checkout really loaded');fs.writeFileSync(path.join(control,'smoke-order.json'),JSON.stringify({orderId:order.orderId,intent,goods:result.goods},null,2));console.log('CLIENT_PASS durable-held-order '+order.orderId);
 }else if(mode==='checkout-gate'){
  const {orderId}=JSON.parse(fs.readFileSync(path.join(control,'smoke-order.json')));const order=await api('/orders/'+orderId);check(order.status==='WAITING_PAYMENT','Held order remains eligible');
  const payment=await api('/orders/'+orderId+'/payment');check(payment.canCreateAttempt===false,'Backend checkout disabled, not merely nginx gate');
  const image=JSON.parse(fs.readFileSync(path.join(root,'deploy/b06/images.lock.json'))).java21;
  const body=JSON.stringify({operationId:randomUUID(),previousAttemptId:null});
  const config=['url = '+JSON.stringify('http://market-b:8080/api/v1/orders/'+orderId+'/payment-attempts'),'request = "POST"','header = '+JSON.stringify('Authorization: Bearer '+token),'header = "Content-Type: application/json"','header = "Origin: https://zj-market-ux.test:8446"','data = '+JSON.stringify(body)].join('\n');
  const result=spawnSync('docker',['--context','desktop-linux','run','--rm','-i','--network','zj-market-ux_edge','--memory','64m','--entrypoint','curl',image,'--silent','--show-error','--fail-with-body','--config','-'],{input:config,encoding:'utf8'});
  check(result.status===22,'Direct backend HTTP rejection');const reply=JSON.parse(result.stdout);check(reply.code==='PAYMENT_DISABLED','Direct backend PAYMENT_DISABLED');console.log('CLIENT_PASS backend-checkout-disabled-without-gateway');
 }else if(mode==='cancel'){
  const {orderId}=JSON.parse(fs.readFileSync(path.join(control,'smoke-order.json')));const r=await api('/orders/'+orderId+'/cancel','POST',{operationId:randomUUID(),reason:'B06 controlled startup acceptance'},[200,202]);console.log('CLIENT_PASS durable-cancel '+orderId);
 }else if(mode==='closed'){
  const {orderId}=JSON.parse(fs.readFileSync(path.join(control,'smoke-order.json')));const closed=await until(()=>api('/orders/'+orderId),o=>o.status==='CLOSED','maintenance recovery close');check(!closed.paymentEnabled,'Checkout remains closed');console.log('CLIENT_PASS maintenance-recovery-closed '+orderId);
 }else throw new Error('Unknown mode');
}
