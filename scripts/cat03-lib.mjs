// UX-only owned preparation. Never accepts a main-site target or arbitrary cleanup IDs.
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import { randomUUID, createHash } from 'node:crypto'
export const root=path.resolve(import.meta.dirname,'..'),origin='https://zj-market-ux.test:8446'
export const batch='cat01-3-20261020-01',work=path.join(root,'.local/cat',batch),fixtureFile=path.join(work,'fixture.json')
if(path.basename(root)!=='zj-market-ux')throw Error('UX worktree required')
fs.mkdirSync(work,{recursive:true})
export const content=JSON.parse(fs.readFileSync(path.join(root,'docs/catalog-products.json'),'utf8'))
const lock=JSON.parse(fs.readFileSync(path.join(root,'docs/tests/cat01-2-acceptance.json'),'utf8'))
if(createHash('sha256').update(fs.readFileSync(path.join(root,'docs/catalog-products.json'))).digest('hex').toUpperCase()!==lock.contentSha256)throw Error('Frozen content changed')
export function save(file,value){const tmp=file+'.tmp';fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n');fs.renameSync(tmp,file)}
export function fixture(){const f=JSON.parse(fs.readFileSync(fixtureFile,'utf8'));if(f.project!=='zj-market-ux'||f.origin!==origin||f.batch!==batch)throw Error('Fixture ownership mismatch');return f}
export function persist(f){save(fixtureFile,f)}
export const pause=ms=>new Promise(r=>setTimeout(r,ms))
export async function until(fn,predicate,name,seconds=120){const end=Date.now()+seconds*1000;let v;do{v=await fn();if(predicate(v))return v;await pause(1000)}while(Date.now()<end);throw Error('Timeout '+name)}
export class Client {
 constructor(){this.access=null;this.cookies=new Map();this.trace=[]}
 async request(route,method='GET',body,extra={}){
  if(method!=='GET'&&!route.startsWith('/auth/')){
   const f=fixture(),owned=new Set(f.items.map(x=>x.goodsId).filter(Boolean)),match=route.match(/^\/(?:admin\/products|admin\/inventory|products)\/([^/]+)/)
   const negative=route==='/purchase-confirmations'&&f.items.some(x=>x.key==='stockout'&&x.purpose==='ACCEPTANCE'&&x.goodsId===body?.goodsId)||route==='/orders'&&!!f.stockoutCheck?.confirmationId&&body?.confirmationId===f.stockoutCheck.confirmationId&&body?.purchaseIntentId===f.stockoutCheck.purchaseIntentId
   if(route!=='/admin/products'&&!negative&&(!match||!owned.has(decodeURIComponent(match[1]))))throw Error('Write is not owned by this UX batch')
   if(!['POST','PUT'].includes(method))throw Error('Unsupported write')
  }
  return new Promise((resolve,reject)=>{
   const q=https.request({hostname:'zj-market-ux.test',port:8446,path:'/api/v1'+route,method,ca:fs.readFileSync(path.join(root,'.local/b06/runtime/web-ca.pem')),rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:[...this.cookies].map(([k,v])=>k+'='+v).join('; '),...(this.access?{Authorization:'Bearer '+this.access}:{}),...extra}},res=>{
    for(const c of res.headers['set-cookie']??[]){const p=c.split(';')[0],i=p.indexOf('=');this.cookies.set(p.slice(0,i),p.slice(i+1))}
    let raw='';res.on('data',x=>raw+=x);res.on('end',()=>{try{const payload=JSON.parse(raw);this.trace.push({route,method,status:res.statusCode,code:payload.code});resolve({status:res.statusCode,...payload})}catch{reject(Error('Untrusted response; retain original operation'))}})
   });q.on('error',()=>reject(Error('Outcome unknown; retain original operation')));q.setTimeout(15000,()=>q.destroy());if(body!==undefined)q.write(JSON.stringify(body));q.end()
  })
 }
 async api(route,method='GET',body,extra){const r=await this.request(route,method,body,extra);if(r.code!=='0000')throw Error('API rejected '+route+' '+r.status+' '+r.code);return r.data}
 async login(name='b06operator'){this.access=null;this.cookies.clear();const a=JSON.parse(fs.readFileSync(path.join(root,'.local/b06/control/demo-accounts.json'),'utf8'))[name],csrf=await this.api('/auth/csrf');this.access=(await this.api('/auth/login','POST',{loginName:a.loginName,password:a.password},{[csrf.headerName]:csrf.token})).accessToken}
 async listing(){const items=[];let total;for(let page=1;page<1000;page++){const r=await this.api('/admin/products?page='+page+'&size=20');total??=r.total;if(r.total!==total)throw Error('Catalogue changed during recovery');items.push(...r.items);if(items.length>=total){if(items.length!==total||new Set(items.map(x=>x.goodsId)).size!==total)throw Error('Incomplete catalogue');return items}}throw Error('Pagination guard')}
}
export function initialize(){
 if(fs.existsSync(fixtureFile))return fixture()
 const items=content.products.map(p=>({key:'showcase-'+p.key,purpose:'SHOWCASE',contentId:p.contentId,price:p.originalPrice,payPrice:p.payPrice,stock:p.initialStock,minutes:p.activity.validMinutes,activity:true,fields:{goodsName:p.goodsName,description:p.description,imageUrl:origin+p.imagePath,originalPrice:p.originalPrice,currency:'CNY',saleStatus:'OFF_SALE'}}))
 for(const key of ['success','expiry','cancel','offpaid','stockout','noactivity','badimage','sync'])items.push({key,purpose:'ACCEPTANCE',price:'100.00',payPrice:'90.00',stock:key==='stockout'?'0':'10',minutes:['expiry','offpaid'].includes(key)?2:30,activity:key!=='noactivity',fields:{goodsName:'CAT 专用验收 '+batch+' '+key,description:'本批专用功能验收样本；演示资金，不真实发货。归属：'+batch+'/'+key,imageUrl:origin+(key==='badimage'?'/catalog/intentionally-missing.svg':'/catalog/cup.svg'),originalPrice:'100.00',currency:'CNY',saleStatus:'OFF_SALE'}})
 const f={batch,project:'zj-market-ux',origin,contentVersion:content.version,items,goods:{},createdAt:new Date().toISOString()};persist(f);return f
}
export const fields=p=>({goodsName:p.goodsName,description:p.description,imageUrl:p.imageUrl,originalPrice:p.originalPrice,currency:p.currency,saleStatus:p.saleStatus})
export function sameFields(a,b){return Object.keys(b).every(k=>a[k]===b[k])}
export async function waitSync(c,id){return until(()=>c.api('/admin/products/'+id),p=>p.syncReady&&p.sync?.confirmedVersion===p.productVersion,'current product sync '+id)}
export async function setSale(c,key,status){
 const f=fixture(),item=f.items.find(x=>x.key===key);if(!item?.goodsId)throw Error('Unknown batch item')
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
  if(lock.batch!==batch||lock.project!=='zj-market-ux'||lock.status!=='SAVED_BEFORE_CLEANUP'||!lock.files||Object.keys(lock.files).length<2)throw Error('Invalid evidence identity')
  const expected=f.items.filter(x=>x.purpose==='ACCEPTANCE').map(x=>x.goodsId).sort()
  if(JSON.stringify([...lock.goodsIds].sort())!==JSON.stringify(expected))throw Error('Evidence goods do not match owned sample set')
  for(const [relative,hash]of Object.entries(lock.files)){
   const resolved=path.resolve(work,relative);if(!resolved.startsWith(path.resolve(work)+path.sep)||createHash('sha256').update(fs.readFileSync(resolved)).digest('hex').toUpperCase()!==hash)throw Error('Saved evidence changed')
  }
 }
 return ids.map(id=>f.items.find(x=>x.goodsId===id))
}
