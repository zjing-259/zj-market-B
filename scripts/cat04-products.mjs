// MAIN only. Frozen content, exact retirement ownership, durable original operation keys.
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import {randomUUID,createHash} from 'node:crypto'
export const root=path.resolve(import.meta.dirname,'..'),origin='https://zj-market.test',batch='cat01-4-20261020-01',work=path.join(root,'.local/cat',batch)
if(path.basename(root)!=='zj-market-ux')throw Error('Expected UX source worktree')
export const load=p=>JSON.parse(fs.readFileSync(p,'utf8'))
export function save(p,v){fs.writeFileSync(p+'.tmp',JSON.stringify(v,null,2)+'\n');fs.renameSync(p+'.tmp',p)}
export const hash=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex').toUpperCase()
export const content=load(path.join(root,'docs/catalog-products.json'))
if(hash(path.join(root,'docs/catalog-products.json'))!==load(path.join(root,'docs/tests/cat01-2-acceptance.json')).contentSha256)throw Error('Frozen content changed')
const stable='D:/Java/zj-market-stable',receipt=load(stable+'/state/adoption.json')
if(receipt.release!=='cat04-stable-20261020-01')throw Error('Accepted main resource release required')
const privateRoot=path.join(stable,'private',receipt.release),manifest=load(path.join(privateRoot,'files-manifest.json'))
function privateFile(name){const p=path.resolve(privateRoot,manifest.probe[name].relativePath);if(!p.startsWith(path.resolve(privateRoot)+path.sep))throw Error('Private path escaped');return p}
export const accounts=load(privateFile('demo-accounts.json')),ca=fs.readFileSync(privateFile('web-ca.pem'))
export const fields=p=>({goodsName:p.goodsName,description:p.description,imageUrl:p.imageUrl,originalPrice:p.originalPrice,currency:p.currency,saleStatus:p.saleStatus})
const same=(a,b)=>Object.keys(b).every(k=>a[k]===b[k])
const file=path.join(work,'fixture.json')
export function fixture(){const f=load(file);if(f.batch!==batch||f.origin!==origin||f.project!=='zj-market-b06')throw Error('Main batch identity mismatch');return f}
function persist(f){save(file,f)}
export const pause=ms=>new Promise(r=>setTimeout(r,ms))
export async function until(fn,pred,label){for(let n=0;n<150;n++){const r=await fn();if(pred(r))return r;await pause(1000)}throw Error('Timeout '+label)}
export class Client{
 constructor(){this.cookies=new Map();this.trace=[]}
 async request(route,method='GET',body,extra={}){
  if(method!=='GET'&&!route.startsWith('/auth/')){
   const f=fixture(),owned=new Set(f.items.map(x=>x.goodsId)),retired=new Set(f.retire.map(x=>x.goodsId));let ok=false
   if(method==='POST'&&route==='/admin/products')ok=f.items.some(x=>x.createStarted&&!x.goodsId&&same(body,x.fields))
   const put=route.match(/^\/admin\/products\/([^/]+)$/),inbound=route.match(/^\/admin\/inventory\/([^/]+)\/inbounds$/),trial=route.match(/^\/products\/([^/]+)\/trial$/)
   if(method==='PUT'&&put){const item=[...f.items,...f.retire].find(x=>x.goodsId===put[1]);ok=!!item?.editStarted&&same(body,item.editStarted.body)&&(owned.has(put[1])||retired.has(put[1])&&body.saleStatus==='OFF_SALE')}
   if(method==='POST'&&inbound)ok=f.items.some(x=>x.goodsId===inbound[1]&&x.stockRequest&&same(body,x.stockRequest))
   if(method==='POST'&&trial)ok=owned.has(trial[1])&&JSON.stringify(body)==='{}'
   if(!ok)throw Error('Write outside explicit main batch contract')
  }
  return new Promise((resolve,reject)=>{
   const q=https.request({hostname:'zj-market.test',port:443,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:[...this.cookies].map(([k,v])=>k+'='+v).join('; '),...(this.access?{Authorization:'Bearer '+this.access}:{}),...extra}},res=>{
    const authorized=res.socket.authorized;for(const c of res.headers['set-cookie']??[]){const p=c.split(';')[0],i=p.indexOf('=');this.cookies.set(p.slice(0,i),p.slice(i+1))}
    let raw='';res.on('data',x=>raw+=x);res.on('end',()=>{try{if(!authorized)throw Error('TLS untrusted');const value=JSON.parse(raw);this.trace.push({route,method,status:res.statusCode,code:value.code});resolve({status:res.statusCode,...value})}catch{reject(Error('Unknown response; retain original operation'))}})
   });q.on('error',()=>reject(Error('Outcome unknown; retain original operation')));q.setTimeout(15000,()=>q.destroy());if(body!==undefined)q.write(JSON.stringify(body));q.end()
  })
 }
 async api(route,method='GET',body,extra){const r=await this.request(route,method,body,extra);if(r.code!=='0000')throw Error('Rejected '+route+' '+r.status+' '+r.code);return r.data}
 async login(key='b06operator'){this.access=null;this.cookies.clear();const csrf=await this.api('/auth/csrf'),a=accounts[key];this.access=(await this.api('/auth/login','POST',{loginName:a.loginName,password:a.password},{[csrf.headerName]:csrf.token})).accessToken}
 async listing(route='/admin/products'){const items=[];let total;for(let page=1;page<100;page++){const p=await this.api(route+'?page='+page+'&size=20');total??=p.total;if(total!==p.total)throw Error('Concurrent catalogue change');items.push(...p.items);if(items.length>=total){if(items.length!==total||new Set(items.map(x=>x.goodsId)).size!==total)throw Error('Incomplete pagination');return items}}throw Error('Pagination guard')}
}
async function synced(c,id){return until(()=>c.api('/admin/products/'+id),p=>p.syncReady&&p.sync?.confirmedVersion===p.productVersion,'final sync')}
function ownership(){const o=load(path.join(work,'ownership.json'));if(o.censusSha256!==hash(path.join(root,'docs/cat01-product-inventory.json'))||o.candidateIds.length!==52||new Set(o.candidateIds).size!==52||o.candidateIds.includes(o.seed.goodsId))throw Error('Invalid retirement ownership');for(const id of o.candidateIds){if(!o.products[id]?.length)throw Error('No exact evidence');for(const e of o.products[id])if(hash(e.path)!==e.sha256)throw Error('Ownership evidence drift')}return o}
async function initialize(c){
 if(fs.existsSync(file))return fixture()
 const o=ownership(),current=await c.listing(),retire=[]
 for(const id of o.candidateIds){const p=await c.api('/admin/products/'+id);if(!p.syncReady||p.saleStatus!=='ON_SALE')throw Error('Review current candidate state');retire.push({goodsId:id,fields:fields(p),baselineVersion:p.productVersion})}
 const f={batch,project:'zj-market-b06',origin,contentVersion:content.version,phase:'PREPARING',beforeIds:current.map(x=>x.goodsId),retire,items:content.products.map(p=>({key:p.key,contentId:p.contentId,payPrice:p.payPrice,stock:p.initialStock,minutes:p.activity.validMinutes,activity:true,fields:{goodsName:p.goodsName,description:p.description,imageUrl:origin+p.imagePath,originalPrice:p.originalPrice,currency:p.currency,saleStatus:'OFF_SALE'}}))};persist(f);return f
}
async function sale(c,key,status,retirement=false){
 const f=fixture(),item=(retirement?f.retire:f.items).find(x=>retirement?x.goodsId===key:x.key===key),p=await c.api('/admin/products/'+item.goodsId)
 if(item.editStarted&&same(p,fields(item.editStarted.body))){item.fields=fields(p);item.version=p.productVersion;item.editStarted=null;persist(f)}
 if(!same(p,item.fields))throw Error('Concurrent fields edit; review before continuation')
 if(p.saleStatus===status){await synced(c,item.goodsId);return {goodsId:item.goodsId,skipped:true,version:p.productVersion}}
 const body={...item.fields,saleStatus:status,expectedVersion:p.productVersion};item.editStarted={body};persist(f)
 const next=await c.api('/admin/products/'+item.goodsId,'PUT',body);item.fields=fields(next);item.version=next.productVersion;item.editStarted=null;persist(f);await synced(c,item.goodsId)
 return {goodsId:item.goodsId,skipped:false,version:next.productVersion}
}
async function verify(c){
 const f=fixture(),rows=[]
 for(const item of f.items){const p=await synced(c,item.goodsId),inv=await c.api('/admin/inventory/'+item.goodsId);if(p.saleStatus!=='ON_SALE'||!same(p,item.fields)||inv.available!==item.stock||inv.reserved!=='0'||inv.sold!=='0')throw Error('Showcase product/stock differs');rows.push({key:item.key,goodsId:item.goodsId,version:p.productVersion,inventory:inv})}
 await c.login('b06buyer')
 for(const row of rows){const item=f.items.find(x=>x.key===row.key),t=(await until(()=>c.request('/products/'+item.goodsId+'/trial','POST',{}),r=>r.code==='0000','read-only main trial')).data;if(t.state!=='AVAILABLE'||t.offer.payPrice!==item.payPrice||t.offer.productVersion!==row.version)throw Error('Offer/version invalid');row.trial=t}
 save(path.join(work,'new-products-ready.json'),{status:'PASS',batch,rows,at:new Date().toISOString()})
}
async function main(){
 const action=process.argv[2],c=new Client();await c.login()
 try{
  if(action==='prepare'){
   let f=fs.existsSync(file)?fixture():null
   // login must work before a fixture exists; only identity requests precede initialize.
   f??=await initialize(c)
   for(const item of f.items){
    if(!item.goodsId){if(item.createStarted){const found=(await c.listing()).filter(p=>!item.beforeCreateIds.includes(p.goodsId)&&same(p,item.fields));if(found.length!==1)throw Error('Ambiguous create outcome; no replacement POST');item.goodsId=found[0].goodsId;persist(f)}else{item.beforeCreateIds=(await c.listing()).map(p=>p.goodsId);item.createStarted=true;persist(f);item.goodsId=(await c.api('/admin/products','POST',item.fields)).goodsId;persist(f)}}
    if(!item.stockRequest){const inv=await c.api('/admin/inventory/'+item.goodsId);item.stockRequest={operationId:randomUUID(),quantity:item.stock,expectedVersion:inv.version,reason:'CAT main '+batch+' '+item.key};persist(f)}
    const prior=await c.request('/admin/inventory/operations/'+item.stockRequest.operationId)
    if(prior.status!==404&&prior.code!=='0000')throw Error('Unknown original operation')
    const op=prior.status===404?await c.api('/admin/inventory/'+item.goodsId+'/inbounds','POST',item.stockRequest):prior.data
    if(op?.outcome!=='SUCCEEDED'||op.operationId!==item.stockRequest.operationId)throw Error('Inbound original key not confirmed')
    item.stockConfirmed=true;persist(f);const p=await synced(c,item.goodsId);if(!same(p,item.fields))throw Error('Product fields changed')
   }
   console.log('CAT04_PREPARED 6-main-new-IDs/6-original-stock-keys')
  }else if(action==='publish'){
   const f=fixture();if(f.items.some(x=>!x.activityConfigured))throw Error('Activity configuration required');for(const item of f.items)await sale(c,item.key,'ON_SALE');await verify(c);const done=fixture();if(done.phase!=='RETIRED')done.phase='NEW_READY';persist(done);console.log('CAT04_NEW_SHOWCASE_READY six-final-versions/actual-offers')
  }else if(action==='verify'){await verify(c);console.log('CAT04_NEW_PRODUCTS_VERIFIED')}
  else if(action==='retire'){
   ownership();if(load(path.join(work,'new-products-ready.json')).status!=='PASS')throw Error('New goods must be ready before retiring old goods')
   await verify(c);await c.login();const f=fixture(),rows=[]
   const evidence=path.join(work,'before-retirement-evidence.json')
   if(!fs.existsSync(evidence))save(evidence,{status:'SAVED_BEFORE_RETIREMENT',at:new Date().toISOString(),batch,goodsIds:f.retire.map(x=>x.goodsId),newGoodsIds:f.items.map(x=>x.goodsId),files:Object.fromEntries(['main-before.json','ux-before.json','ownership.json','new-products-ready.json','main-upgrade.json','fixture.json'].map(name=>{const frozen='saved-before-retirement-'+name;fs.copyFileSync(path.join(work,name),path.join(work,frozen));return[frozen,hash(path.join(work,frozen))]}))})
   for(const item of f.retire)rows.push(await sale(c,item.goodsId,'OFF_SALE',true))
   const first=path.join(work,'retirement.json');save(fs.existsSync(first)?path.join(work,'retirement-repeat.json'):first,{status:'PASS',rows});const done=fixture();done.phase='RETIRED';persist(done);console.log('CAT04_RETIREMENT_PASS selected=52 writes='+rows.filter(x=>!x.skipped).length)
  }else throw Error('Explicit prepare/publish/verify/retire action required')
 }finally{save(path.join(work,'api-'+action+'-'+Date.now()+'.json'),c.trace)}
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(import.meta.filename))await main()
