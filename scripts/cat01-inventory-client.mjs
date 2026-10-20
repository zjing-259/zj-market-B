// CAT-01.1: strict TLS, paginated GETs; only identity login may POST.
import fs from 'node:fs'
import path from 'node:path'
import https from 'node:https'
const root=path.resolve(import.meta.dirname,'..'),batch=process.argv[2]
if(path.basename(root)!=='zj-market-ux'||!/^cat01-1-[0-9]{8}-[0-9]{2}$/.test(batch))throw Error('Owned inventory batch required')
const work=path.join(root,'.local/cat',batch,'main')
fs.mkdirSync(work,{recursive:true})
const stable='D:/Java/zj-market-stable',receipt=JSON.parse(fs.readFileSync(stable+'/state/adoption.json','utf8'))
if(!/^ux05-stable-[0-9]{8}-[0-9]{2}$/.test(receipt.release))throw Error('Review current stable identity before collecting')
const privateRoot=path.join(stable,'private',receipt.release),manifest=JSON.parse(fs.readFileSync(path.join(privateRoot,'files-manifest.json'),'utf8'))
function privateFile(name){const file=path.resolve(privateRoot,manifest.probe[name].relativePath);if(!file.startsWith(path.resolve(privateRoot)+path.sep))throw Error('Private input escaped');return file}
const ca=fs.readFileSync(privateFile('web-ca.pem')),operator=JSON.parse(fs.readFileSync(privateFile('demo-accounts.json'),'utf8')).b06operator
let access;const cookies=new Map(),requests=[]
async function api(route,method='GET',body,extra={}){
 if(method!=='GET'&&!(method==='POST'&&route==='/auth/login'))throw Error('Resource writes forbidden')
 return new Promise((resolve,reject)=>{
  const req=https.request({hostname:'zj-market.test',port:443,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:'https://zj-market.test','Content-Type':'application/json',Cookie:[...cookies].map(([k,v])=>k+'='+v).join('; '),...(access?{Authorization:'Bearer '+access}:{}),...extra}},res=>{
   const authorized=res.socket.authorized
   for(const c of res.headers['set-cookie']??[]){const pair=c.split(';')[0],i=pair.indexOf('=');cookies.set(pair.slice(0,i),pair.slice(i+1))}
   let raw='';res.on('data',x=>raw+=x);res.on('end',()=>{try{const envelope=JSON.parse(raw);requests.push({route,method,status:res.statusCode,code:envelope.code,tlsAuthorized:authorized});if(!authorized||res.statusCode!==200||envelope.code!=='0000')throw Error('Read failed '+route+' '+res.statusCode);resolve(envelope.data)}catch(e){reject(e)}})
  });req.on('error',()=>reject(Error('Read-only HTTPS request failed')));req.setTimeout(15000,()=>req.destroy());if(body!==undefined)req.write(JSON.stringify(body));req.end()
 })
}
async function pages(route){
 const items=[],pageRecords=[];let total
 for(let page=1;page<=10000;page++){
  const data=await api(route+'?page='+page+'&size=20')
  if(total===undefined)total=data.total
  if(data.total!==total||data.page!==page||data.size!==20)throw Error('Unstable pagination')
  pageRecords.push({page,size:data.size,total:data.total,count:data.items.length});items.push(...data.items)
  if(items.length>=total){if(items.length!==total||new Set(items.map(x=>x.goodsId)).size!==total)throw Error('Duplicate or missing goods');return {items,pages:pageRecords,total}}
  if(!data.items.length)throw Error('Truncated pagination')
 }
 throw Error('Pagination exceeded guard')
}
const publicListing=await pages('/products')
const csrf=await api('/auth/csrf'),tokens=await api('/auth/login','POST',{loginName:operator.loginName,password:operator.password},{[csrf.headerName]:csrf.token});access=tokens.accessToken
const adminListing=await pages('/admin/products'),details=[]
for(const p of adminListing.items){if(!/^[a-f0-9-]{36}$/.test(p.goodsId))throw Error('Unexpected goods ID');details.push({product:await api('/admin/products/'+p.goodsId),inventory:await api('/admin/inventory/'+p.goodsId),sync:await api('/admin/products/'+p.goodsId+'/sync')})}
fs.writeFileSync(path.join(work,'api-inventory.json'),JSON.stringify({status:'PASS',origin:'https://zj-market.test',operatorLoginName:operator.loginName,strictTLS:true,resourceWrites:0,publicListing,adminListing,details,requests},null,2)+'\n')
console.log('CAT01_API_INVENTORY_PASS products='+adminListing.total+' public='+publicListing.total+' adminPages='+adminListing.pages.length+' publicPages='+publicListing.pages.length+' resourceWrites=0')
