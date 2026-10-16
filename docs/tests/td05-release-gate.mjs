import fs from 'node:fs';
import https from 'node:https';
import path from 'node:path';

const work=path.resolve(process.argv[2]??'');
const mode=process.argv[3];
if(!work.includes('td05_')||!['off','on','old-a'].includes(mode))throw Error('TD05 work and off/on/old-a required');
const ca=fs.readFileSync(path.join(work,'private/runtime/web-ca.pem'));
const accounts=JSON.parse(fs.readFileSync(path.join(work,'private/control/demo-accounts.json')));
const fixture=JSON.parse(fs.readFileSync(path.join(work,'browser/fixture.json')));
const origin='https://zj-market.test:8445';
let cookie='';
async function request(route,method='GET',body,token,csrf){return await new Promise((resolve,reject)=>{
 const req=https.request({hostname:'zj-market.test',port:8445,path:'/api/v1'+route,method,ca,rejectUnauthorized:true,family:4,autoSelectFamily:false,
  lookup:(_h,_o,cb)=>cb(null,'127.0.0.1',4),headers:{Origin:origin,'Content-Type':'application/json',Cookie:cookie,
   ...(token?{Authorization:'Bearer '+token}:{}),...(csrf?{[csrf.headerName]:csrf.token}:{})}},res=>{
  const cookies=res.headers['set-cookie'];if(cookies?.length)cookie=cookies.map(c=>c.split(';')[0]).join('; ');
  let data='';res.on('data',b=>data+=b);res.on('end',()=>resolve({status:res.statusCode,body:JSON.parse(data)}));
 });req.on('error',reject);if(body)req.write(JSON.stringify(body));req.end();
});}
const csrf=(await request('/auth/csrf')).body.data;
const login=await request('/auth/login','POST',accounts.b06buyer,undefined,csrf);
if(login.status!==200||login.body.code!=='0000')throw Error('TD05 buyer login failed');
const result=await request('/products/'+fixture.goods.success+'/joinable-teams','GET',undefined,login.body.data.accessToken);
if(mode==='off'&&result.status!==404)throw Error('Discovery-off route must be absent: '+result.status);
if(mode==='on'&&(result.status!==200||result.body.code!=='0000'))throw Error('Real A discovery RPC not ready: '+result.status+'/'+result.body.code);
if(mode==='old-a'&&(result.status!==503||result.body.code!=='DEPENDENCY_UNAVAILABLE'))throw Error('Old A must explicitly fail: '+result.status+'/'+result.body.code);
console.log('PASS td05-discovery-'+mode+'-'+result.status);
