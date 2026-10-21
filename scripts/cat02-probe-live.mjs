// UX only: real signed peer queries, with an explicit empty-catalogue response drill.
import fs from 'node:fs'
import path from 'node:path'
import {transport,checkReadiness} from './cat02-stable-probe.mjs'
const root=path.resolve(import.meta.dirname,'..'),work=path.join(root,'.local/cat/cat02-closeout-20261021-01'),mode=process.argv[2]
if(path.basename(root)!=='zj-market-ux'||!['normal','empty','down','recovery'].includes(mode))throw Error('Explicit UX probe drill required')
const origin='https://zj-market-ux.test:8446',raw=transport({ca:fs.readFileSync(path.join(root,'.local/b06/runtime/web-ca.pem')),origin}),accounts=JSON.parse(fs.readFileSync(path.join(root,'.local/b06/control/demo-accounts.json'),'utf8')),trace=[]
let login
async function request(route,...args){
 if(route==='/auth/login'&&login)return login
 let r=await raw(route,...args);trace.push({route,method:args[0]??'GET',status:r.status,code:r.payload.code,tls:r.tlsAuthorized,requestId:r.payload.requestId})
 if(route==='/auth/login'&&r.status===200)login=r
 if(mode==='empty'&&route.startsWith('/products?'))r={...r,payload:{...r.payload,data:{items:[],page:1,size:20,total:0}}}
 return r
}
let result,error
const deadline=Date.now()+(mode==='recovery'?120000:1)
do{
 try{result=await checkReadiness(request,accounts.b06buyer);error=null;break}catch(e){error=e.message;if(mode!=='recovery')break;await new Promise(r=>setTimeout(r,2000))}
}while(Date.now()<deadline)
const passed=mode==='down'?!!error&&trace.some(x=>x.route.startsWith('/teams/')&&[502,503].includes(x.status)):!error&&result?.status==='STABLE_PROBE_PASS'
fs.writeFileSync(path.join(work,'probe-ux-'+mode+'.json'),JSON.stringify({status:passed?'PASS':'FAIL',mode,origin,result:result??null,error:error??null,catalogueResponseControlledEmpty:mode==='empty',actualCatalogueDataModified:false,trace},null,2)+'\n')
if(!passed)throw Error('UX probe drill failed; sanitized details in private evidence')
console.log('CAT02_UX_PROBE_'+mode.toUpperCase()+'_PASS')
