// Two explicitly reviewed legacy goods only. No create, stock, order, payment or refund writes.
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
import {createHash} from 'node:crypto'
export const root=path.resolve(import.meta.dirname,'..'),batch='cat02-closeout-20261021-01',work=path.join(root,'.local/cat',batch),origin='https://zj-market.test'
export const targets=['5a4d973a-4d83-4f7b-9155-4c331b436fc4','db7100d5-12ad-4b24-b7b3-dc773b0f33b8']
export const load=p=>JSON.parse(fs.readFileSync(p,'utf8'))
export const hash=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex').toUpperCase()
export function save(p,v){fs.writeFileSync(p+'.tmp',JSON.stringify(v,null,2)+'\n');fs.renameSync(p+'.tmp',p)}
const stable='D:/Java/zj-market-stable',receipt=load(stable+'/state/adoption.json')
if(path.basename(root)!=='zj-market-ux'||receipt.release!=='cat02-stable-20261021-01'||receipt.project!=='zj-market-b06')throw Error('Expected independent CAT02 main release')
const privateRoot=path.join(stable,'private',receipt.release),manifest=load(path.join(privateRoot,'files-manifest.json'))
function privateFile(name){const p=path.resolve(privateRoot,manifest.probe[name].relativePath);if(!p.startsWith(path.resolve(privateRoot)+path.sep))throw Error('Unsafe private path');return p}
export const accounts=load(privateFile('demo-accounts.json')),ca=fs.readFileSync(privateFile('web-ca.pem'))
if('seed-goods-id.txt' in manifest.probe)throw Error('Active probe still depends on goods seed')
const journalFile=path.join(work,'retirement-journal.json')
export const fields=p=>({goodsName:p.goodsName,description:p.description,imageUrl:p.imageUrl,originalPrice:p.originalPrice,currency:p.currency,saleStatus:p.saleStatus})
const same=(a,b)=>Object.keys(b).every(k=>a[k]===b[k])
export class Client{
 constructor(){this.cookies=new Map();this.trace=[]}
 async request(route,method='GET',body,extra={}){
  if(method!=='GET'&&!(method==='POST'&&route==='/auth/login')){
   const match=route.match(/^\/admin\/products\/([^/]+)$/),journal=load(journalFile),item=journal.items.find(x=>x.goodsId===match?.[1])
   if(method!=='PUT'||!match||!targets.includes(match[1])||body?.saleStatus!=='OFF_SALE'||!item?.pending||JSON.stringify(item.pending)!==JSON.stringify(body))throw Error('Only the two journaled off-sale edits are permitted')
  }
  return new Promise((resolve,reject)=>{
   const req=https.request({hostname:'zj-market.test',port:443,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:[...this.cookies].map(([k,v])=>k+'='+v).join('; '),...(this.access?{Authorization:'Bearer '+this.access}:{}),...extra}},res=>{
    const authorized=res.socket.authorized
    for(const c of res.headers['set-cookie']??[]){const p=c.split(';')[0],i=p.indexOf('=');this.cookies.set(p.slice(0,i),p.slice(i+1))}
    let raw='';res.on('data',x=>raw+=x);res.on('end',()=>{try{if(!authorized)throw Error();const p=JSON.parse(raw);this.trace.push({route,method,status:res.statusCode,code:p.code,requestId:p.requestId});resolve({status:res.statusCode,...p})}catch{reject(Error('Unknown response; preserve original edit'))}})
   });req.on('error',()=>reject(Error('Unknown HTTPS outcome; preserve original edit')));req.setTimeout(15000,()=>req.destroy());if(body!==undefined)req.write(JSON.stringify(body));req.end()
  })
 }
 async api(route,method='GET',body,extra){const r=await this.request(route,method,body,extra);if(r.code!=='0000')throw Error('API rejected '+r.status+' '+r.code);return r.data}
 async login(key='b06operator'){this.cookies.clear();this.access=null;const csrf=await this.api('/auth/csrf'),a=accounts[key];this.access=(await this.api('/auth/login','POST',{loginName:a.loginName,password:a.password},{[csrf.headerName]:csrf.token})).accessToken}
 async pages(route){const items=[];let total;for(let page=1;page<100;page++){const r=await this.api(route+'?page='+page+'&size=20');total??=r.total;if(total!==r.total)throw Error('Concurrent catalogue change');items.push(...r.items);if(items.length>=total){if(items.length!==total||new Set(items.map(x=>x.goodsId)).size!==total)throw Error('Incomplete pagination');return items}}throw Error('Pagination guard')}
}
async function synced(c,id){for(let n=0;n<150;n++){const p=await c.api('/admin/products/'+id);if(p.syncReady&&p.sync?.confirmedVersion===p.productVersion)return p;await new Promise(r=>setTimeout(r,1000))}throw Error('Final version sync timeout')}
async function main(){
 if(process.argv[2]!=='retire')throw Error('Explicit retire action required')
 const evidence=load(path.join(work,'ownership-review.json'))
 if(evidence.status!=='REVIEWED'||JSON.stringify(evidence.goodsIds)!==JSON.stringify(targets))throw Error('Exact ownership review required')
 for(const[p,h]of Object.entries(evidence.sourceHashes))if(hash(p)!==h)throw Error('Ownership source evidence changed')
 if(load(path.join(work,'main-upgrade.json')).status!=='PASS')throw Error('New probe release must be ready first')
 const seal=load(path.join(work,'evidence-before-retirement.json'))
 if(seal.status!=='SAVED_BEFORE_RETIREMENT'||JSON.stringify(seal.goodsIds)!==JSON.stringify(targets))throw Error('Save exact evidence before retirement')
 for(const[name,digest]of Object.entries(seal.files)){const p=path.resolve(work,name);if(!p.startsWith(path.resolve(work)+path.sep)||hash(p)!==digest)throw Error('Sealed pre-retirement evidence changed')}
 const baseline=load(path.join(work,'main-before.json')),c=new Client();await c.login()
 let journal
 if(fs.existsSync(journalFile))journal=load(journalFile)
 else{
  journal={batch,project:'zj-market-b06',operator:accounts.b06operator.loginName,reason:'User-authorized exact legacy storefront closeout after probe dependency removal',items:[]}
  for(const id of targets){const p=await c.api('/admin/products/'+id),b=baseline.products.find(x=>x.goods_id===id);if(!b||!same(p,{goodsName:b.goods_name,description:b.description,imageUrl:b.image_url,originalPrice:Number(b.original_price).toFixed(2),currency:b.currency,saleStatus:b.sale_status})||p.productVersion!==String(b.product_version))throw Error('Reviewed product changed');journal.items.push({goodsId:id,reviewed:fields(p),beforeVersion:p.productVersion})}
  save(journalFile,journal)
 }
 if(journal.batch!==batch||journal.project!=='zj-market-b06'||JSON.stringify(journal.items.map(x=>x.goodsId))!==JSON.stringify(targets))throw Error('Retirement journal ownership changed')
 const rows=[]
 try{
  for(const item of journal.items){
   let current=await c.api('/admin/products/'+item.goodsId)
   if(item.pending&&same(current,fields(item.pending))){item.final=fields(current);item.finalVersion=current.productVersion;item.pending=null;item.recovered=true;save(journalFile,journal)}
   if(!same(current,item.final??item.reviewed))throw Error('Concurrent fields edit; review required')
   if(current.saleStatus==='OFF_SALE'){await synced(c,item.goodsId);rows.push({goodsId:item.goodsId,skipped:true,version:current.productVersion});continue}
   item.pending={...fields(current),saleStatus:'OFF_SALE',expectedVersion:current.productVersion};save(journalFile,journal)
   const next=await c.api('/admin/products/'+item.goodsId,'PUT',item.pending);item.final=fields(next);item.finalVersion=next.productVersion;item.pending=null;save(journalFile,journal);await synced(c,item.goodsId);rows.push({goodsId:item.goodsId,skipped:false,version:next.productVersion})
  }
  const file=path.join(work,'retirement.json');save(fs.existsSync(file)?path.join(work,'retirement-repeat.json'):file,{status:'PASS',rows});console.log('CAT02_EXACT_RETIREMENT_PASS writes='+rows.filter(x=>!x.skipped).length)
 }finally{save(path.join(work,'api-retire-'+Date.now()+'.json'),c.trace)}
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(import.meta.filename))await main()
