import https from 'node:https';import fs from 'node:fs';import path from 'node:path';
const ca=fs.readFileSync(path.join(process.argv[2],'web-ca.pem'));
for(const route of ['/orders','/orders/unknown/payment-attempts','/payments/unknown/attempts/unknown/simulated-results','/unknown-new-write']){
 const status=await new Promise((resolve,reject)=>{const req=https.request({hostname:'zj-market.test',port:443,path:'/api/v1'+route,method:'POST',ca,rejectUnauthorized:true,family:4,lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:'https://zj-market.test','Content-Type':'application/json'}},res=>{if(!res.socket.authorized){reject(Error('TLS_UNAUTHORIZED'));return}res.resume();res.on('end',()=>resolve(res.statusCode));});req.on('error',reject);req.setTimeout(10000,()=>req.destroy(Error('GATE_TIMEOUT')));req.end('{}');});
 if(status!==503)throw Error('GATE_MUST_REJECT '+route+' '+status);
}
console.log('RECOVERY_GATE_PASS strict TLS; all new mutations 503');
