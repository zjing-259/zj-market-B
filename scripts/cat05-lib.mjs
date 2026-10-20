// CAT05 MAIN-only acceptance batch. Normal catalogue references are read-only.
import {accounts,ca} from './cat04-products.mjs'
export {accounts}
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import { randomUUID, createHash } from 'node:crypto'
export const root=path.resolve(import.meta.dirname,'..'),origin='https://zj-market.test'
export const batch=process.env.CAT_ACCEPTANCE_BATCH??'cat01-5-20261020-01',work=path.join(root,'.local/cat',batch),fixtureFile=path.join(work,'fixture.json')
if(!/^cat01-5-[0-9]{8}-[0-9]{2}$/.test(batch))throw Error('Explicit CAT05 batch format required')
if(path.basename(root)!=='zj-market-ux')throw Error('UX worktree required')
fs.mkdirSync(work,{recursive:true})
export const content=JSON.parse(fs.readFileSync(path.join(root,'docs/catalog-products.json'),'utf8'))
const lock=JSON.parse(fs.readFileSync(path.join(root,'docs/tests/cat01-2-acceptance.json'),'utf8'))
if(createHash('sha256').update(fs.readFileSync(path.join(root,'docs/catalog-products.json'))).digest('hex').toUpperCase()!==lock.contentSha256)throw Error('Frozen content changed')
export function save(file,value){const tmp=file+'.tmp';fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n');fs.renameSync(tmp,file)}
export function fixture(){const f=JSON.parse(fs.readFileSync(fixtureFile,'utf8'));if(f.project!=='zj-market-b06'||f.origin!==origin||f.batch!==batch)throw Error('Fixture ownership mismatch');return f}
export function persist(f){save(fixtureFile,f)}
export const pause=ms=>new Promise(r=>setTimeout(r,ms))
export async function until(fn,predicate,name,seconds=120){const end=Date.now()+seconds*1000;let v;do{v=await fn();if(predicate(v))return v;await pause(1000)}while(Date.now()<end);throw Error('Timeout '+name)}
export class Client {
 constructor(){this.access=null;this.cookies=new Map();this.trace=[]}
 async request(route,method='GET',body,extra={}){
  if(method!=='GET'&&!route.startsWith('/auth/')){
   if(fs.existsSync(path.join(work,'evidence-lock.json'))&&!(method==='PUT'&&route.startsWith('/admin/products/')&&body?.saleStatus==='OFF_SALE')&&!(method==='POST'&&/^\/products\/[^/]+\/trial$/.test(route)))throw Error('Sealed batch only permits owned off-sale cleanup and read-only trials')
   const f=fixture(),owned=new Set(f.items.map(x=>x.goodsId).filter(Boolean)),match=route.match(/^\/(?:admin\/products|admin\/inventory|products)\/([^/]+)/)
   const negative=route==='/purchase-confirmations'&&f.items.some(x=>x.key==='stockout'&&x.purpose==='ACCEPTANCE'&&x.goodsId===body?.goodsId)||route==='/orders'&&!!f.stockoutCheck?.confirmationId&&body?.confirmationId===f.stockoutCheck.confirmationId&&body?.purchaseIntentId===f.stockoutCheck.purchaseIntentId
   const trial=method==='POST'&&route.endsWith('/trial')&&f.showcase.some(x=>x.goodsId===match?.[1])
   if(route!=='/admin/products'&&!negative&&!trial&&(!match||!owned.has(decodeURIComponent(match[1]))))throw Error('Write is not owned by this main batch')
   if(!['POST','PUT'].includes(method))throw Error('Unsupported write')
  }
  return new Promise((resolve,reject)=>{
   const q=https.request({hostname:'zj-market.test',port:443,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:[...this.cookies].map(([k,v])=>k+'='+v).join('; '),...(this.access?{Authorization:'Bearer '+this.access}:{}),...extra}},res=>{
    for(const c of res.headers['set-cookie']??[]){const p=c.split(';')[0],i=p.indexOf('=');this.cookies.set(p.slice(0,i),p.slice(i+1))}
    let raw='';res.on('data',x=>raw+=x);res.on('end',()=>{try{const payload=JSON.parse(raw);this.trace.push({route,method,status:res.statusCode,code:payload.code});resolve({status:res.statusCode,retryAfter:res.headers['retry-after'],...payload})}catch{reject(Error('Untrusted response; retain original operation'))}})
   });q.on('error',()=>reject(Error('Outcome unknown; retain original operation')));q.setTimeout(15000,()=>q.destroy());if(body!==undefined)q.write(JSON.stringify(body));q.end()
  })
 }
 async api(route,method='GET',body,extra){const r=await this.request(route,method,body,extra);if(r.code!=='0000')throw Error('API rejected '+route+' '+r.status+' '+r.code);return r.data}
 async login(name='b06operator'){
  this.access=null;this.cookies.clear();const a=accounts[name]
  for(let attempt=0;attempt<4;attempt++){
   const csrf=await this.api('/auth/csrf'),r=await this.request('/auth/login','POST',{loginName:a.loginName,password:a.password},{[csrf.headerName]:csrf.token})
   if(r.code==='0000'){this.access=r.data.accessToken;return}
   if(r.status!==429||attempt===3)throw Error('Login rejected '+r.status+' '+r.code)
   const seconds=Number(r.retryAfter);if(!Number.isFinite(seconds)||seconds<1||seconds>60)throw Error('Review login Retry-After before proceeding')
   console.log('CAT05_AUTH_RATE_LIMIT_WAIT '+seconds+'s; no business operation retried');await pause(seconds*1000)
  }
 }
 async listing(){const items=[];let total;for(let page=1;page<1000;page++){const r=await this.api('/admin/products?page='+page+'&size=20');total??=r.total;if(r.total!==total)throw Error('Catalogue changed during recovery');items.push(...r.items);if(items.length>=total){if(items.length!==total||new Set(items.map(x=>x.goodsId)).size!==total)throw Error('Incomplete catalogue');return items}}throw Error('Pagination guard')}
}
export function initialize(){
 if(fs.existsSync(fixtureFile))return fixture()
 if(!fs.existsSync(path.join(work,'main-before.json')))throw Error('Frozen main baseline required')
 const normal=JSON.parse(fs.readFileSync(path.join(root,'docs/cat04-main-products.json'),'utf8'))
 const showcase=normal.products.map(p=>({...p,key:'showcase-'+p.key,purpose:'SHOWCASE',stock:'20',fields:{goodsName:p.goodsName}}))
 const items=[]
 for(const key of ['success','expiry','cancel','offpaid','stockout','noactivity','badimage'])items.push({key,purpose:'ACCEPTANCE',price:'100.00',payPrice:'90.00',stock:key==='stockout'?'0':'10',minutes:['expiry','offpaid','cancel'].includes(key)?2:30,activity:key!=='noactivity',fields:{goodsName:'CAT 专用验收 '+batch+' '+key,description:'本批专用验收；模拟资金，不真实发货。精确归属：'+batch+'/'+key,imageUrl:origin+(key==='badimage'?'/catalog/intentionally-missing.svg':'/catalog/cup.svg'),originalPrice:'100.00',currency:'CNY',saleStatus:'OFF_SALE'}})

 const f={batch,project:'zj-market-b06',origin,contentVersion:content.version,showcase,items,goods:{},createdAt:new Date().toISOString()};persist(f);return f
}
export const fields=p=>({goodsName:p.goodsName,description:p.description,imageUrl:p.imageUrl,originalPrice:p.originalPrice,currency:p.currency,saleStatus:p.saleStatus})
export function sameFields(a,b){return Object.keys(b).every(k=>a[k]===b[k])}
export async function waitSync(c,id){return until(()=>c.api('/admin/products/'+id),p=>p.syncReady&&p.sync?.confirmedVersion===p.productVersion,'current product sync '+id)}
export async function setSale(c,key,status){
 const f=fixture(),item=f.items.find(x=>x.key===key);if(!item?.goodsId)throw Error('Unknown batch item')
 if(status==='ON_SALE'&&(fs.existsSync(path.join(work,'evidence-lock.json'))||f.phase==='CLEANED'))throw Error('Sealed batch cannot be republished')
 const current=await c.api('/admin/products/'+item.goodsId)
 if(item.editStarted&&sameFields(current,fields(item.editStarted.body))){item.fields=fields(current);item.version=current.productVersion;item.editStarted=null;item.recoveredEdit=true;persist(f)}
 if(!sameFields(current,item.fields))throw Error('Product fields changed outside this journal')
 if(current.saleStatus===status)return {skipped:true,product:await waitSync(c,item.goodsId)}
 const body={...item.fields,saleStatus:status,expectedVersion:current.productVersion}
 item.editStarted={body,reason:'explicit-'+status};persist(f)
 const next=await c.api('/admin/products/'+item.goodsId,'PUT',body)
 if(status==='OFF_SALE'&&process.env.CAT_LOSE_OFFSALE_RECEIPT===key&&!item.editReceiptLossExercised){item.editReceiptLossExercised=true;persist(f);throw Error('INJECTED_OFFSALE_RESPONSE_LOSS retain original edit and query product')}
 item.fields=fields(next);item.version=next.productVersion;item.editStarted=null;persist(f)
 await waitSync(c,item.goodsId)
 return {skipped:false,product:next}
}
export function validateCleanupIds(ids,requireEvidence=true){
 const f=fixture()
 if(!ids.length||new Set(ids).size!==ids.length)throw Error('Explicit unique cleanup IDs required')
 for(const id of ids){const item=f.items.find(x=>x.goodsId===id);if(!item||item.purpose!=='ACCEPTANCE'||!item.createStarted||!item.beforeCreateIds)throw Error('Cleanup ID is not an owned ACCEPTANCE item')}
 if(requireEvidence){
  const file=path.join(work,'evidence-lock.json');if(!fs.existsSync(file))throw Error('Save evidence before cleanup')
  const lock=JSON.parse(fs.readFileSync(file,'utf8'))
  if(lock.batch!==batch||lock.project!=='zj-market-b06'||lock.status!=='SAVED_BEFORE_CLEANUP'||!lock.files||Object.keys(lock.files).length<2)throw Error('Invalid evidence identity')
  const expected=f.items.filter(x=>x.purpose==='ACCEPTANCE'&&x.goodsId).map(x=>x.goodsId).sort()
  if(JSON.stringify([...lock.goodsIds].sort())!==JSON.stringify(expected))throw Error('Evidence goods do not match owned sample set')
  for(const [relative,hash]of Object.entries(lock.files)){
   const resolved=path.resolve(work,relative);if(!resolved.startsWith(path.resolve(work)+path.sep)||createHash('sha256').update(fs.readFileSync(resolved)).digest('hex').toUpperCase()!==hash)throw Error('Saved evidence changed')
  }
 }
 return ids.map(id=>f.items.find(x=>x.goodsId===id))
}
