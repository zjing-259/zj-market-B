import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import { randomUUID } from 'node:crypto'

const root=path.resolve(import.meta.dirname,'../..')
const work=path.resolve(process.argv[3]??'')
const mode=process.argv[2]
if(!work.startsWith(path.join(root,'target','team-discovery','td04_')))throw Error('Unsafe TD04 work path')
const origin='https://zj-market.test:8444'
const ca=fs.readFileSync(path.join(work,'private/runtime/web-ca.pem'))
const accounts=JSON.parse(fs.readFileSync(path.join(work,'private/control/demo-accounts.json')))
const report={stage:'TD-04',mode,status:'RUNNING',checks:[],orders:{}}
const check=(value,label)=>{if(!value)throw Error(label);report.checks.push(label);console.log('PASS '+label)}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
async function until(job,predicate,label,seconds=120){const end=Date.now()+seconds*1000;let value;do{value=await job();if(predicate(value))return value;await sleep(1000)}while(Date.now()<end);throw Error('Timeout '+label+' '+JSON.stringify(value))}

class Client {
  token='';cookies=new Map()
  async raw(route,method='GET',body,extra={}){
    return new Promise((resolve,reject)=>{
      const req=https.request({hostname:'zj-market.test',port:8444,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,
        lookup:(_host,_options,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',
          Cookie:[...this.cookies].map(([key,value])=>key+'='+value).join('; '),...(this.token?{Authorization:'Bearer '+this.token}:{}),...extra}},res=>{
        for(const raw of res.headers['set-cookie']??[]){const [key,value]=raw.split(';')[0].split('=',2);this.cookies.set(key,value)}
        let text='';res.on('data',chunk=>text+=chunk);res.on('end',()=>{try{resolve({status:res.statusCode,body:JSON.parse(text),headers:res.headers})}catch{reject(Error('Non-JSON response'))}})
      });req.on('error',reject);req.setTimeout(15000,()=>req.destroy(Error('HTTPS timeout')));if(body!==undefined)req.write(JSON.stringify(body));req.end()
    })
  }
  async api(route,method='GET',body){const response=await this.raw(route,method,body);if(response.body.code!=='0000')throw Error(route+' '+response.status+' '+response.body.code);return response.body.data}
  async login(credentials){const csrf=await this.api('/auth/csrf');const response=await this.raw('/auth/login','POST',credentials,{[csrf.headerName]:csrf.token});check(response.status===200,'login-'+credentials.loginName);this.token=response.body.data.accessToken}
  async loseResponse(route,body){
    return new Promise((resolve,reject)=>{
      const req=https.request({hostname:'zj-market.test',port:8444,path:'/api/v1'+route,method:'POST',ca,rejectUnauthorized:true,family:4,
        lookup:(_host,_options,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:[...this.cookies].map(([k,v])=>k+'='+v).join('; '),Authorization:'Bearer '+this.token}},res=>{
        const status=res.statusCode;res.destroy();resolve(status)
      });req.on('error',reject);req.setTimeout(15000,()=>req.destroy(Error('HTTPS timeout')));req.write(JSON.stringify(body));req.end()
    })
  }
}

async function order(client,goods,teamId){
  const trial=await until(async()=>{const response=await client.raw('/products/'+goods+'/trial','POST',{});if(response.body.code==='DEPENDENCY_UNAVAILABLE')return null;if(response.body.code!=='0000')throw Error('Trial '+response.status+' '+response.body.code);return response.body.data},Boolean,'trial-dependency-ready',45)
  check(trial.state==='AVAILABLE'&&trial.offer?.targetCount===2,'current-trial-'+(teamId?'join':'open'))
  const confirmationResponse=await client.raw('/purchase-confirmations','POST',{goodsId:goods,mode:teamId?'JOIN':'OPEN',...(teamId?{teamId}:{}),expectedOffer:trial.offer})
  if(confirmationResponse.body.code!=='0000')return {rejected:confirmationResponse.body.code}
  const confirmation=confirmationResponse.body.data
  const intent=randomUUID()
  const accepted=await client.raw('/orders','POST',{purchaseIntentId:intent,confirmationId:confirmation.confirmationId})
  if(accepted.body.code!=='0000')return {rejected:accepted.body.code,intent}
  const orderId=accepted.body.data.orderId
  return {orderId,intent,confirmationId:confirmation.confirmationId}
}
async function pay(client,orderId){
  await until(()=>client.api('/orders/'+orderId),value=>value.status==='WAITING_PAYMENT','waiting-payment')
  const existing=await client.api('/orders/'+orderId+'/payment')
  if(existing.payment?.fundsState==='SUCCEEDED'&&existing.payment.aAcceptance==='ACCEPTED')return existing
  const operationId=randomUUID()
  const first=await until(async()=>{
    const response=await client.raw('/orders/'+orderId+'/payment-attempts','POST',{operationId,previousAttemptId:null})
    if(response.body.code==='PAYMENT_TIME_UNVERIFIABLE')return null
    if(response.body.code!=='0000')throw Error('Attempt '+response.status+' '+response.body.code)
    return response.body.data
  },Boolean,'payment-window-verified',90)
  check(first.accepted,'attempt-received')
  const current=await until(()=>client.api('/orders/'+orderId+'/payment'),value=>value.payment?.attempts.some(x=>x.canSelectResult),'attempt-open')
  const attempt=current.payment.attempts.find(x=>x.canSelectResult)
  const result=await client.api('/payments/'+current.payment.paymentId+'/attempts/'+attempt.attemptId+'/simulated-results','POST',{operationId:randomUUID(),result:'SUCCEEDED'})
  check(result.accepted,'payment-result-received')
  return until(()=>client.api('/orders/'+orderId+'/payment'),value=>value.payment?.fundsState==='SUCCEEDED'&&value.payment.aAcceptance==='ACCEPTED','A-payment-accepted')
}

try{
  const operator=new Client();await operator.login(accounts.b06operator)
  if(mode==='prepare'||mode==='prepare-unknown'||mode==='prepare-expiry'||mode==='prepare-tabs'){
    const product=await operator.api('/admin/products','POST',{goodsName:'TD04 last slot '+path.basename(work),description:'Isolated concurrency acceptance',imageUrl:null,originalPrice:'100.00',currency:'CNY',saleStatus:'ON_SALE'})
    const inventory=await operator.api('/admin/inventory/'+product.goodsId)
    await operator.api('/admin/inventory/'+product.goodsId+'/inbounds','POST',{operationId:randomUUID(),quantity:'10',expectedVersion:inventory.version,reason:'TD04 last slot fixture'})
    const fixtureName=mode==='prepare'?'race-fixture.json':mode==='prepare-unknown'?'unknown-fixture.json':mode==='prepare-expiry'?'expiry-fixture.json':'tabs-fixture.json'
    fs.writeFileSync(path.join(work,fixtureName),JSON.stringify({goodsId:product.goodsId},null,2))
    check(true,mode+'-product-stock')
  }else if(mode==='readonly'){
    const fixture=JSON.parse(fs.readFileSync(path.join(work,'race-fixture.json')))
    for(let i=0;i<25;i++){
      const response=await operator.raw('/products/'+fixture.goodsId+'/joinable-teams?limit=3')
      check(response.status===200&&response.body.code==='0000'&&response.headers['cache-control']?.includes('no-store'),'readonly-discovery-'+i)
    }
  }else if(mode==='outage'||mode==='recovered'||mode==='old-a'){
    const fixture=JSON.parse(fs.readFileSync(path.join(work,'race-fixture.json')))
    const request=()=>operator.raw('/products/'+fixture.goodsId+'/joinable-teams?limit=3')
    const response=mode==='recovered'?await until(request,value=>value.status===200,'discovery-RPC-cold-recovery',60):await request()
    if(mode==='outage'||mode==='old-a')check(response.status===503&&response.body.code!=='0000',mode==='outage'?'A-down-explicit-503':'old-A-missing-discovery-explicit-503')
    else check(response.status===200&&response.body.code==='0000','A-restart-discovery-recovers')
  }else if(mode==='disabled'){
    const fixture=JSON.parse(fs.readFileSync(path.join(work,'race-fixture.json')))
    const hidden=await operator.raw('/products/'+fixture.goodsId+'/joinable-teams?limit=3')
    check(hidden.status===404,'discovery-route-absent-when-flag-off')
    const original=await operator.api('/products/'+fixture.goodsId+'/trial','POST',{})
    check(original.state==='AVAILABLE','original-trial-remains-available')
    const anonymous=new Client();const denied=await anonymous.raw('/products/'+fixture.goodsId+'/joinable-teams?limit=3')
    check(denied.status===401,'flag-off-still-protects-route')
  }else if(mode==='unknown-send'){
    const fixturePath=path.join(work,'unknown-fixture.json'),fixture=JSON.parse(fs.readFileSync(fixturePath))
    const buyer=new Client();await buyer.login(accounts.b06buyer)
    await until(()=>buyer.api('/products/'+fixture.goodsId),value=>value.syncReady,'unknown-product-sync')
    const trial=await buyer.api('/products/'+fixture.goodsId+'/trial','POST',{})
    check(trial.state==='AVAILABLE','unknown-trial')
    const confirmation=await buyer.api('/purchase-confirmations','POST',{goodsId:fixture.goodsId,mode:'OPEN',expectedOffer:trial.offer})
    fixture.intent=randomUUID();fixture.confirmationId=confirmation.confirmationId
    fs.writeFileSync(fixturePath,JSON.stringify(fixture,null,2))
    const status=await buyer.loseResponse('/orders',{purchaseIntentId:fixture.intent,confirmationId:fixture.confirmationId})
    check(status===200||status===202,'client-dropped-order-response-after-server-headers')
    const active=await until(()=>buyer.api('/products/'+fixture.goodsId+'/active-order'),value=>!!value?.orderId,'unknown-order-recovered-by-active-key')
    fixture.orderId=active.orderId
    const actual=await until(()=>buyer.api('/orders/'+fixture.orderId),value=>value.status==='WAITING_PAYMENT','unknown-reserve-committed')
    fixture.teamId=actual.teamId
    fs.writeFileSync(fixturePath,JSON.stringify(fixture,null,2))
    check(!!fixture.teamId,'unknown-original-team-id-preserved')
  }else if(mode==='unknown-recover'){
    const fixture=JSON.parse(fs.readFileSync(path.join(work,'unknown-fixture.json')))
    const buyer=new Client();await buyer.login(accounts.b06buyer)
    const active=await buyer.api('/products/'+fixture.goodsId+'/active-order')
    check(active?.orderId===fixture.orderId,'restart-recovers-original-active-order')
    const replay=await buyer.raw('/orders','POST',{purchaseIntentId:fixture.intent,confirmationId:fixture.confirmationId})
    check(replay.body.code==='0000'&&replay.body.data.orderId===fixture.orderId,'same-business-key-replays-original-order')
    const current=await buyer.api('/orders/'+fixture.orderId)
    check(current.status==='WAITING_PAYMENT'&&current.teamId===fixture.teamId,'restart-keeps-A-team-and-payment-obligation')
    await buyer.api('/orders/'+fixture.orderId+'/cancel','POST',{operationId:randomUUID(),reason:'TD04 unknown recovery cleanup'})
    await until(()=>buyer.api('/orders/'+fixture.orderId),value=>value.status==='CLOSED','unknown-order-cancelled-after-recovery')
    check(true,'unknown-order-legal-unpaid-close')
  }else if(mode==='tabs'){
    const fixturePath=path.join(work,'tabs-fixture.json'),fixture=JSON.parse(fs.readFileSync(fixturePath))
    const left=new Client(),right=new Client();await left.login(accounts.b06buyer);await right.login(accounts.b06buyer)
    await until(()=>left.api('/products/'+fixture.goodsId),value=>value.syncReady,'tabs-product-sync')
    const results=await Promise.allSettled([order(left,fixture.goodsId),order(right,fixture.goodsId)])
    const submitted=results.map((r,i)=>({client:i?right:left,result:r.status==='fulfilled'?r.value:{rejected:r.reason.message}}))
    const accepted=submitted.filter(x=>x.result.orderId)
    check(accepted.length>=1,'two-tab-orders-attempted')
    const rows=await Promise.all(accepted.map(async x=>({client:x.client,id:x.result.orderId,order:await until(()=>x.client.api('/orders/'+x.result.orderId),o=>['WAITING_PAYMENT','CLOSED'].includes(o.status),'tabs-terminal-or-payable')})))
    const winners=rows.filter(x=>x.order.status==='WAITING_PAYMENT')
    check(winners.length===1,'same-user-sku-one-active-order')
    const active=await left.api('/products/'+fixture.goodsId+'/active-order')
    check(active?.orderId===winners[0].id,'both-tabs-resolve-original-active-order')
    await winners[0].client.api('/orders/'+winners[0].id+'/cancel','POST',{operationId:randomUUID(),reason:'TD04 tabs acceptance'})
    await until(()=>winners[0].client.api('/orders/'+winners[0].id),o=>o.status==='CLOSED','tabs-winner-closed')
    fixture.orders=accepted.map(x=>x.result.orderId);fixture.rejected=submitted.filter(x=>!x.result.orderId).map(x=>x.result.rejected)
    fs.writeFileSync(fixturePath,JSON.stringify(fixture,null,2))
    check(true,'two-tabs-no-duplicate-inventory-obligation')
  }else if(mode==='expiry-stage'){
    const fixturePath=path.join(work,'expiry-fixture.json'),fixture=JSON.parse(fs.readFileSync(fixturePath))
    const first=new Client(),second=new Client();await first.login(accounts.b06buyer);await second.login(accounts.b06buyer2)
    await until(()=>first.api('/products/'+fixture.goodsId),value=>value.syncReady,'expiry-product-sync')
    const opened=await order(first,fixture.goodsId);check(!!opened.orderId,'expiry-open')
    const own=await until(()=>first.api('/orders/'+opened.orderId),value=>value.status==='WAITING_PAYMENT','expiry-open-reserved')
    await pay(first,opened.orderId)
    const joined=await order(second,fixture.goodsId,own.teamId);check(!!joined.orderId,'expiry-join')
    const reserved=await until(()=>second.api('/orders/'+joined.orderId),value=>value.status==='WAITING_PAYMENT','expiry-join-reserved')
    const operationId=randomUUID()
    const attempted=await until(async()=>{const r=await second.raw('/orders/'+joined.orderId+'/payment-attempts','POST',{operationId,previousAttemptId:null});return r.body.code==='PAYMENT_TIME_UNVERIFIABLE'?null:r.body.code==='0000'?r.body.data:Promise.reject(Error('Attempt '+r.body.code))},Boolean,'expiry-attempt-accepted',40)
    check(attempted.accepted,'expiry-attempt-accepted')
    const payment=await until(()=>second.api('/orders/'+joined.orderId+'/payment'),value=>value.payment?.attempts.some(x=>x.canSelectResult),'expiry-attempt-open')
    const attempt=payment.payment.attempts.find(x=>x.canSelectResult)
    Object.assign(fixture,{openId:opened.orderId,joinId:joined.orderId,teamId:own.teamId,deadline:reserved.paymentDeadline,paymentId:payment.payment.paymentId,attemptId:attempt.attemptId})
    fs.writeFileSync(fixturePath,JSON.stringify(fixture,null,2))
    check(Date.parse(fixture.deadline)>Date.now()+5000,'expiry-test-has-time-window')
  }else if(mode==='expiry-result'){
    const fixture=JSON.parse(fs.readFileSync(path.join(work,'expiry-fixture.json')))
    const second=new Client();await second.login(accounts.b06buyer2)
    const response=await second.api('/payments/'+fixture.paymentId+'/attempts/'+fixture.attemptId+'/simulated-results','POST',{operationId:randomUUID(),result:'SUCCEEDED'})
    check(response.accepted,'expiry-window-result-intent-submitted')
    check(Date.now()<Date.parse(fixture.deadline),'expiry-result-intent-before-deadline')
    report.resultSubmittedAt=Date.now();report.deadline=fixture.deadline
  }else if(mode==='expiry-final'){
    const fixture=JSON.parse(fs.readFileSync(path.join(work,'expiry-fixture.json')))
    const first=new Client(),second=new Client();await first.login(accounts.b06buyer);await second.login(accounts.b06buyer2)
    const a=await until(()=>first.api('/orders/'+fixture.openId),value=>['GROUP_COMPLETED','CLOSED'].includes(value.status),'expiry-final-open',180)
    const b=await until(()=>second.api('/orders/'+fixture.joinId),value=>['GROUP_COMPLETED','CLOSED'].includes(value.status),'expiry-final-join',180)
    check(a.status===b.status,'expiry-consistent-terminal')
    report.orders={open:fixture.openId,join:fixture.joinId};report.teamId=fixture.teamId;report.goodsId=fixture.goodsId;report.terminal=a.status
    check(true,'expiry-late-A-event-finalized')
  }else if(mode==='race'){
    const fixture=JSON.parse(fs.readFileSync(path.join(work,'race-fixture.json')))
    const goods=fixture.goodsId
    const first=new Client(),second=new Client()
    await first.login(accounts.b06buyer);await second.login(accounts.b06buyer2)
    await until(()=>first.api('/products/'+goods),value=>value.syncReady,'race-product-sync')
    const active=await first.api('/products/'+goods+'/active-order')
    const opened=active?{orderId:active.orderId}:await order(first,goods)
    check(!!opened.orderId,'race-open-order')
    const held=await until(()=>first.api('/orders/'+opened.orderId),value=>value.status==='WAITING_PAYMENT','race-A-open-reserve')
    await pay(first,opened.orderId)
    const initial=await second.api('/products/'+goods+'/joinable-teams?limit=3')
    check(initial.state==='AVAILABLE'&&initial.items.some(x=>x.teamId===held.teamId),'paid-team-public-before-race')
    const [join2,join3]=await Promise.all([order(second,goods,held.teamId),order(operator,goods,held.teamId)])
    const submitted=[{...join2,client:second},{...join3,client:operator}].filter(x=>x.orderId)
    check(submitted.length>=1,'last-slot-join-attempts-submitted')
    const rows=await Promise.all(submitted.map(async entry=>({entry,order:await until(()=>entry.client.api('/orders/'+entry.orderId),value=>['WAITING_PAYMENT','CLOSED'].includes(value.status),'last-slot-outcome')})))
    const winners=rows.filter(x=>x.order.status==='WAITING_PAYMENT')
    check(winners.length===1,'exactly-one-last-slot-winner')
    check(rows.every(x=>x.order.requestedTeamId===held.teamId&&(!x.order.teamId||x.order.teamId===held.teamId)),'no-alternative-team')
    const winner=winners[0]
    await pay(winner.entry.client,winner.entry.orderId)
    await until(()=>first.api('/orders/'+opened.orderId),value=>value.status==='GROUP_COMPLETED','race-team-completed')
    for(const row of rows.filter(x=>x!==winner))await until(()=>row.entry.client.api('/orders/'+row.entry.orderId),value=>value.status==='CLOSED','loser-release')
    report.orders={open:opened.orderId,winner:winner.entry.orderId,losers:rows.filter(x=>x!==winner).map(x=>x.entry.orderId)}
    report.teamId=held.teamId;report.goodsId=goods
    check(true,'last-slot-real-A-B-MQ-completion')
  }else throw Error('Expected TD04 test mode')
  report.status='PASSED'
}catch(error){report.status='FAILED';report.error=error.message;throw error}
finally{fs.writeFileSync(path.join(work,'race-'+mode+'-report.json'),JSON.stringify(report,null,2)+'\n')}
