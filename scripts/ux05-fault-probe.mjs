// Harmless strict-TLS boundary probes. No orders or payment writes.
import fs from 'node:fs'
import https from 'node:https'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'..'), mode=process.argv[2]
if(!['maintenance','b-down','a-down','open'].includes(mode))throw Error('Explicit probe mode required')
const ca=fs.readFileSync(path.join(root,'.local/b06/runtime/web-ca.pem'))
let token,cookie=''
async function req(route,method='GET',body,headers={}) {
  return new Promise((resolve,reject)=>{
    const q=https.request({hostname:'zj-market-ux.test',port:8446,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:'https://zj-market-ux.test:8446','Content-Type':'application/json',Cookie:cookie,...(token?{Authorization:'Bearer '+token}:{}),...headers}},r=>{
      if(r.headers['set-cookie'])cookie=r.headers['set-cookie'].map(x=>x.split(';')[0]).join('; ')
      let raw='';r.on('data',x=>raw+=x);r.on('end',()=>{try{resolve({status:r.statusCode,type:r.headers['content-type'],body:JSON.parse(raw)})}catch{reject(Error('Non-JSON gateway response'))}})
    });q.on('error',reject);q.setTimeout(25000,()=>q.destroy(Error('Probe timeout')));if(body!==undefined)q.write(JSON.stringify(body));q.end()
  })
}
const status=await req('/system/status')
if(status.body.data?.mode!==(mode==='maintenance'?'MAINTENANCE':'NORMAL'))throw Error('Actual gate mismatch')
let result
if(mode==='maintenance') {
  result=await req('/orders','POST',{})
  if(result.status!==503||result.body.code!=='SITE_MAINTENANCE')throw Error('Maintenance write gate failed')
  if((await req('/auth/csrf')).status!==200)throw Error('Identity recovery blocked')
} else if(mode==='b-down') {
  result=await req('/products')
  if(result.status!==502||result.body.code!=='GATEWAY_UNAVAILABLE')throw Error('Upstream failure not normalized')
} else if(mode==='a-down') {
  const accounts=JSON.parse(fs.readFileSync(path.join(root,'.local/b06/control/demo-accounts.json'))),c=(await req('/auth/csrf')).body.data,a=accounts.b06buyer
  token=(await req('/auth/login','POST',{loginName:a.loginName,password:a.password},{[c.headerName]:c.token})).body.data.accessToken
  const fixture=JSON.parse(fs.readFileSync(path.join(root,'.local/ux05/ux05-20261019-01-ux/fixture.json')))
  result=await req('/products/'+fixture.goods.success+'/trial','POST',{})
  if(result.body.code==='0000'&&result.body.data?.state==='AVAILABLE')throw Error('Unavailable A reported available')
} else {
  result=await req('/orders','POST',{})
  if(result.status!==401||result.body.code!=='AUTH_REQUIRED')throw Error('Open authentication gate failed')
}
console.log(JSON.stringify({mode,status:'PASS',http:result.status,code:result.body.code,state:result.body.data?.state??null,strictTLS:true,noFinancialWrites:true}))
