import fs from 'node:fs';import path from 'node:path';import https from 'node:https';import {randomUUID} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'../..'),action=process.argv[2],batch=process.argv[3],name=process.argv[4],option=process.argv[5];
if(!/^b065-[a-z0-9-]+$/.test(batch??''))throw Error('Invalid batch');
const work=path.join(root,'.local/b06/faults',batch),file=path.join(work,'fixture.json');
const ca=fs.readFileSync(path.join(root,'.local/b06/runtime/web-ca.pem')),accounts=JSON.parse(fs.readFileSync(path.join(root,'.local/b06/control/demo-accounts.json')));
let f=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):{batch,goods:{},orders:{}};let token;const cookies=new Map();
const save=()=>{fs.writeFileSync(file+'.tmp',JSON.stringify(f,null,2));fs.renameSync(file+'.tmp',file)};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function request(route,method='GET',body,headers={},lose=false){return new Promise((resolve,reject)=>{
 const req=https.request({hostname:'zj-market.test',port:443,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:'https://zj-market.test','Content-Type':'application/json',Cookie:[...cookies].map(([k,v])=>k+'='+v).join('; '),...(token?{Authorization:'Bearer '+token}:{}),...headers}},res=>{
  if(!res.socket.authorized){reject(Error('Untrusted TLS'));return}
  for(const c of res.headers['set-cookie']??[]){const s=c.split(';')[0],i=s.indexOf('=');cookies.set(s.slice(0,i),s.slice(i+1))}
  if(lose){const status=res.statusCode;res.destroy();resolve({status,receiptLost:true});return}
  let text='';res.on('data',b=>text+=b);res.on('end',()=>{let data;try{data=JSON.parse(text)}catch{data={code:'NON_JSON'}}resolve({status:res.statusCode,retryAfter:res.headers['retry-after'],...data})});res.on('error',reject);
 });req.on('error',reject);req.setTimeout(10000,()=>req.destroy(Error('HTTPS_TIMEOUT')));if(body!==undefined)req.write(JSON.stringify(body));req.end();
})}
async function api(route,method,body,headers){const r=await request(route,method,body,headers);if(r.code!=='0000')throw Error('API '+r.status+' '+r.code);return r.data}
async function stableWrite(route,body){return until(async()=>{const r=await request(route,'POST',body);if(r.code==='0000')return r.data;if(r.status===503){f.transientResponses??=[];f.transientResponses.push({status:r.status,code:r.code,at:new Date().toISOString()});save();return null}throw Error('API '+r.status+' '+r.code)},v=>v!==null,90)}
async function login(account){const csrf=await api('/auth/csrf');const r=await until(async()=>{const v=await request('/auth/login','POST',accounts[account],{[csrf.headerName]:csrf.token});if(v.status===429){const seconds=Math.max(1,Math.min(60,Number(v.retryAfter)||5));f.rateLimitWaits??=[];f.rateLimitWaits.push({account,seconds,at:new Date().toISOString()});save();await sleep(seconds*1000);return null}if(v.code!=='0000')throw Error('LOGIN '+v.status+' '+v.code);return v.data},v=>v!==null,90);token=r.accessToken}
async function until(fn,test,seconds=120){const end=Date.now()+seconds*1000;while(Date.now()<end){const v=await fn();if(test(v))return v;await sleep(1500)}throw Error('WAIT_TIMEOUT')}
if(action==='prepare'){
 await login('b06operator');
 for(const n of ['unpaid','success','refundBlocked','refundHealthy']){
  const p=await api('/admin/products','POST',{goodsName:'B065 '+batch+' '+n,description:'Independent actual fault acceptance',imageUrl:null,originalPrice:'100.00',currency:'CNY',saleStatus:'ON_SALE'});f.goods[n]=p.goodsId;save();
  const inv=await api('/admin/inventory/'+p.goodsId);await api('/admin/inventory/'+p.goodsId+'/inbounds','POST',{operationId:randomUUID(),quantity:'10',expectedVersion:inv.version,reason:'B065 fresh fault batch'});
 }
 console.log(JSON.stringify({prepared:true,goods:f.goods}));
}else if(action==='probe'){
 try{const r=await request(name);console.log(JSON.stringify({status:r.status,code:r.code}))}catch(e){console.log(JSON.stringify({status:null,transportUnknown:true,error:e.message==='HTTPS_TIMEOUT'?'TIMEOUT':'CONNECTION_ERROR'}))}
}else{
 const o=f.orders[name];const account=action==='hold'?(process.argv[6]??'b06buyer'):o?.account??'b06buyer';await login(account);
 if(action==='hold'){
  if(o)throw Error('Order name already exists');const goods=f.goods[option];if(!goods)throw Error('Unknown fixture goods');
  const team=process.argv[7];const trialResult=await until(()=>request('/products/'+goods+'/trial','POST',{}),v=>v.code==='0000'&&v.data.state==='AVAILABLE');const trial=trialResult.data;
  const confirmation=await api('/purchase-confirmations','POST',{goodsId:goods,mode:team?'JOIN':'OPEN',...(team?{teamId:team}:{}),expectedOffer:trial.offer});
  const data={account,goods,confirmationId:confirmation.confirmationId,purchaseIntentId:randomUUID(),operations:{}};f.orders[name]=data;save();
  const created=await api('/orders','POST',{purchaseIntentId:data.purchaseIntentId,confirmationId:data.confirmationId});data.orderId=created.orderId;save();
  const held=await until(()=>api('/orders/'+data.orderId),v=>v.status==='WAITING_PAYMENT');data.teamId=held.teamId;data.initial=held.status;save();console.log(JSON.stringify({orderId:data.orderId,teamId:data.teamId}));
 }else if(action==='create'||action==='replay-create'||action==='unavailable'){
  if(!o)throw Error('Missing order');o.operations.create??={operationId:randomUUID(),previousAttemptId:null};save();
  if(action==='unavailable'){
   try{const r=await request('/orders/'+o.orderId+'/payment-attempts','POST',o.operations.create);console.log(JSON.stringify({status:r.status,code:r.code,accepted:r.code==='0000'}))}catch{console.log(JSON.stringify({status:null,transportUnknown:true}))}
  }else{
   const route='/orders/'+o.orderId+'/payment-attempts';if(option==='lose'){
    const lost=await until(async()=>{const r=await request(route,'POST',o.operations.create,{},true);o.lostStatuses??=[];o.lostStatuses.push(r.status);save();if([200,202].includes(r.status))return r;if(r.status!==503)throw Error('LOST_REQUEST_STATUS_'+r.status);const q=await request('/orders/'+o.orderId+'/payment-operations/'+o.operations.create.operationId);if(q.code==='0000'&&q.data.receipt?.accepted)return {status:200,receiptLost:true,foundByOriginalOperation:true};if(![404,503].includes(q.status))throw Error('OPERATION_QUERY_UNEXPECTED');return null},v=>v!==null,90);o.receiptLost=true;save();console.log(JSON.stringify(lost));
   }else{
    const receipt=await stableWrite(route,o.operations.create);o.paymentId=receipt.paymentId;o.attemptId=receipt.attemptId;save();
    const p=await until(()=>api('/orders/'+o.orderId+'/payment'),v=>v.payment?.attempts.some(a=>a.attemptId===o.attemptId&&a.state==='OPEN'));o.payment=p.payment;save();console.log(JSON.stringify({paymentId:o.paymentId,attemptId:o.attemptId,receiptOperationId:receipt.operationId}));
   }
  }
 }else if(action==='choose'){
  o.operations.choose??={operationId:randomUUID(),result:'SUCCEEDED'};save();
  await stableWrite('/payments/'+o.paymentId+'/attempts/'+o.attemptId+'/simulated-results',o.operations.choose);
  const p=await until(()=>api('/payments/'+o.paymentId),v=>v.fundsState==='SUCCEEDED');o.payment=p;save();console.log(JSON.stringify({paymentId:p.paymentId,funds:p.fundsState,aAcceptance:p.aAcceptance,paidAt:p.paidAt}));
 }else if(action==='cancel'){
  o.operations.cancel??={operationId:randomUUID(),reason:'B065 controlled dependency interruption'};save();
  const r=await request('/orders/'+o.orderId+'/cancel','POST',o.operations.cancel);console.log(JSON.stringify({status:r.status,code:r.code,orderStatus:r.data?.status}));
 }else if(action==='trial'){
  const r=await stableWrite('/products/'+o.goods+'/trial',{});console.log(JSON.stringify({state:r.state}));
 }else if(action==='read'){
  const v=await api('/orders/'+o.orderId);console.log(JSON.stringify({status:v.status,teamId:v.teamId,payment:v.paymentSummary,refund:v.refundSummary}));
 }else throw Error('Unknown action');
}
