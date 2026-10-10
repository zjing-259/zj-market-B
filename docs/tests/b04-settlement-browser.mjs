import {createRequire} from 'node:module';
import fs from 'node:fs';import path from 'node:path';
const require=createRequire(path.resolve('target/b02-browser-runtime/package.json'));const {chromium}=require('playwright');
const work=process.env.B_PAYMENT_BROWSER_WORK;if(!work)throw new Error('Missing browser work');
const fixture=JSON.parse(fs.readFileSync(path.join(work,'browser-private.json'),'utf8'));
const browser=await chromium.launch({headless:true,executablePath:process.env.B_BROWSER_EXECUTABLE??'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});const context=await browser.newContext({viewport:{width:1280,height:900}});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));const samples={},captures=[];page.on('response',res=>{if(res.status()===200&&/\/api\/v1\/(?:orders\/[^/]+\/payment|payments\/[^/]+)$/.test(res.url()))captures.push((async()=>{const body=await res.json(),p=body.data.payment??body.data;const schema=res.url().includes('/orders/')?'OrderPaymentViewResponse':'PaymentViewResponse';samples[schema+'-'+(p.fundsState??'NONE')+'-'+(p.aAcceptance??'NONE')]={schema,body};})());});
try{
 await page.goto('http://127.0.0.1:5173/login?returnTo='+encodeURIComponent('/orders/'+fixture.orderId+'/payment'));
 await page.getByLabel('登录名').fill(fixture.loginName);await page.getByLabel('密码',{exact:true}).fill(fixture.password);await page.locator('form button[type="submit"]').click();
 await page.getByRole('button',{name:'创建模拟支付尝试',exact:true}).click();await page.getByRole('button',{name:'选择模拟成功',exact:true}).click();
 await page.getByRole('status').filter({hasText:'已支付，营销确认中'}).waitFor({timeout:30000});await page.screenshot({path:path.join(work,'settlement-pending-desktop.png'),fullPage:true});
 fs.writeFileSync(path.join(work,'browser-accept.txt'),'owned verification phase');
 await page.getByRole('status').filter({hasText:'营销已确认'}).waitFor({timeout:30000});
 let writes=0;page.on('request',r=>{if(r.method()==='POST'&&/payment/.test(r.url()))writes++});await page.reload();await page.getByRole('status').filter({hasText:'营销已确认'}).waitFor();if(writes!==0)throw new Error('Reload wrote payment');
 await page.evaluate(async()=>{const auth=await import('/src/services/auth.ts');const data=await auth.request('/orders/'+location.pathname.split('/')[2]+'/payment',auth.user.value.userId);await auth.request('/payments/'+data.payment.paymentId,auth.user.value.userId)});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(work,'settlement-accepted-mobile.png'),fullPage:true});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');if(errors.length)throw new Error('Page errors');
 await Promise.all(captures);if(!Object.keys(samples).some(k=>k.endsWith('SUCCEEDED-ACCEPTED'))||!Object.keys(samples).some(k=>k.endsWith('SUCCEEDED-PENDING')))throw new Error('Missing actual payment contract states');fs.writeFileSync(path.join(work,'http-contract-samples.json'),JSON.stringify(samples,null,2));
 fs.writeFileSync(path.join(work,'browser.json'),JSON.stringify({status:'PASSED',scenario:'real B HTTP/MySQL/channel, controlled A acceptance only in verification',marketPending:true,marketAccepted:true,reloadPaymentWrites:writes,mobileOverflow:false,pageErrors:errors},null,2));
}finally{await browser.close()}
