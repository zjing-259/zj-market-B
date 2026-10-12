import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'../..');
const ca=fs.readFileSync(path.join(root,'.local/b06/runtime/web-ca.pem'));
const marker='DO_NOT_LOG_'+randomUUID().replaceAll('-','');
const rows=[];
const upstream=process.argv[2]==='upstream';
for(const [route,headers] of (upstream ? [['/api/v1/products?private='+marker,{}]] : [
 ['/api/v1/products?private='+marker,{}],
 ['/api/v1/products',{Authorization:'Bearer '+marker,Cookie:'private='+marker}],
 ['/api/v1/unmapped/'+marker,{}],
 ['/api/v1/products',{}]
])){
 rows.push(await new Promise((resolve,reject)=>{
  const req=https.request({hostname:'zj-market.test',family:4,autoSelectFamily:false,port:443,path:route,method:'GET',ca,rejectUnauthorized:true,lookup:(h,o,cb)=>cb(null,'127.0.0.1',4),headers},res=>{
   if(!res.socket.authorized)return reject(new Error('Untrusted TLS'));
   res.resume();res.on('end',()=>resolve({status:res.statusCode,requestId:res.headers['x-request-id']}));
  });req.on('error',reject);req.setTimeout(10000,()=>req.destroy(new Error('timeout')));req.end();
 }));
}
if(upstream ? rows[0].status!==502 : (rows[0].status!==400||rows[1].status!==401||rows[2].status!==404||rows[3].status!==200||rows.some(r=>!r.requestId)))throw new Error('Unexpected observation probe results');
console.log(JSON.stringify({trustedTls:true,marker,rows}));
