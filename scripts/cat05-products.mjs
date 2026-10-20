import fs from 'node:fs'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import {Client,initialize,fixture,persist,work,save,fixtureFile,fields,sameFields,waitSync,setSale,validateCleanupIds,until} from './cat05-lib.mjs'
const action=process.argv[2],c=new Client();initialize();await c.login()
try{
 if(action==='prepare'){
  let f=fixture()
  for(const item of f.items){
   if(!item.goodsId){
    if(item.createStarted){
     const recovered=(await c.listing()).filter(p=>!item.beforeCreateIds.includes(p.goodsId)&&sameFields(p,item.fields))
     if(recovered.length!==1)throw Error('Unknown create needs manual exact-field reconciliation; no new POST')
     item.goodsId=recovered[0].goodsId;item.recoveredCreate=true;persist(f)
    }else{
     item.beforeCreateIds=(await c.listing()).map(p=>p.goodsId);item.createStarted=true;persist(f)
     const product=await c.api('/admin/products','POST',item.fields)
     if(item.key==='success'&&process.argv.includes('--lose-create-response')){item.createOutcomeUnknown=true;persist(f);throw Error('INJECTED_CREATE_RESPONSE_LOSS original create retained')}
     item.goodsId=product.goodsId;persist(f)
    }
   }
   if(item.purpose==='ACCEPTANCE')f.goods[item.key]=item.goodsId
   persist(f)
   if(item.stock!=='0'){
    if(!item.stockRequest){const inv=await c.api('/admin/inventory/'+item.goodsId);item.stockRequest={operationId:randomUUID(),quantity:item.stock,expectedVersion:inv.version,reason:'CAT MAIN owned '+f.batch+' '+item.key};persist(f)}
    const previous=await c.request('/admin/inventory/operations/'+item.stockRequest.operationId)
    if(previous.status!==404&&previous.code!=='0000')throw Error('Original stock query failed; do not change operation key')
    const result=previous.status===404?await c.api('/admin/inventory/'+item.goodsId+'/inbounds','POST',item.stockRequest):previous.data
    if(item.key==='success'&&process.argv.includes('--lose-stock-response')){item.stockOutcomeUnknown=true;persist(f);throw Error('INJECTED_STOCK_RESPONSE_LOSS original operation retained')}
    if(!result||result.outcome!=='SUCCEEDED'||result.operationId!==item.stockRequest.operationId)throw Error('Original stock not confirmed')
    item.stockConfirmed=true;persist(f)
   }
   const actual=await c.api('/admin/products/'+item.goodsId)
   if(!sameFields(actual,item.fields))throw Error('Existing product differs; refusing overwrite')
  }
  console.log('CAT05_PREPARED 7-owned-main-acceptance/6-readonly-showcase/original-stock-keys')
 }else if(action==='publish'){
  if(fs.existsSync(path.join(work,'evidence-lock.json'))||fixture().phase==='CLEANED')throw Error('Closed or evidenced batch cannot be republished')
  if(fixture().phase==='PUBLISHED'||fs.existsSync(path.join(work,'products-verified.json')))console.log('CAT05_PUBLICATION_ALREADY_RECORDED no-reopening')
  else for(const item of fixture().items){if(item.activity&&!item.activityId)throw Error('A binding not recorded');await setSale(c,item.key,'ON_SALE')}
  const published=fixture();published.phase='PUBLISHED';persist(published)
  console.log('CAT05_PUBLISHED final-versions-confirmed')
 }else if(action==='verify'){
  let f=fixture()
  for(const item of f.items){const p=await waitSync(c,item.goodsId),inv=await c.api('/admin/inventory/'+item.goodsId);if(!sameFields(p,item.fields))throw Error('Product mismatch');if(item.purpose==='SHOWCASE'&&(inv.available!==item.stock||inv.reserved!=='0'||inv.sold!=='0'))throw Error('Showcase stock changed')}
  await c.login('b06buyer')
  const reads=[]
  for(const item of f.items){if(item.fields.saleStatus!=='ON_SALE')continue;const response=await until(()=>c.request('/products/'+item.goodsId+'/trial','POST',{}),r=>r.code==='0000','read-only offer recovery '+item.key);const trial=response.data;if(item.activity){if(trial.state!=='AVAILABLE'||trial.offer.payPrice!==item.payPrice||trial.offer.productVersion!==item.version)throw Error('Actual quote/version differs '+item.key)}else if(trial.state==='AVAILABLE')throw Error('No activity reported purchasable');reads.push({key:item.key,state:trial.state,payPrice:trial.offer?.payPrice??null})}
  save(path.join(work,'products-verified.json'),{status:'PASS',reads});console.log('CAT05_PRODUCTS_VERIFIED current-sync/quotes/stock')
 }else if(action==='guards'){
  const f=fixture(),show=f.showcase[0],sample=f.items.find(x=>x.purpose==='ACCEPTANCE');let rejected=0
  const current=await c.api('/admin/products/'+sample.goodsId)
  const stale=await c.request('/admin/products/'+sample.goodsId,'PUT',{...fields(current),expectedVersion:String(BigInt(current.productVersion)-1n)})
  if(stale.status!==409||stale.code!=='PRODUCT_EDIT_CONFLICT')throw Error('Stale version was not rejected')
  for(const ids of [[show.goodsId],['d6fe5415-53da-4d1d-b147-b873f554208a'],[sample.goodsId]]){try{validateCleanupIds(ids)}catch{rejected++}}
  if(rejected!==3)throw Error('Unsafe or unsealed cleanup accepted')
  await c.login('b06buyer');const product=await c.request('/admin/products','POST',{}),inv=await c.request('/admin/inventory/'+sample.goodsId+'/inbounds','POST',{operationId:randomUUID(),quantity:'1',expectedVersion:'1',reason:'permission boundary'})
  if(product.status!==403||inv.status!==403)throw Error('Buyer write permission failed')
  save(path.join(work,'guards.json'),{status:'PASS',rejectedCleanupSelections:3,buyerProductWrite:403,buyerStockWrite:403,staleEditCode:stale.code});console.log('CAT05_OWNERSHIP_AND_PERMISSION_GUARDS_PASS')
 }else if(action==='stockout'){
  const f=fixture(),item=f.items.find(x=>x.key==='stockout');await c.login('b06buyer')
  if(f.stockoutCheck?.status==='PASS'){console.log('CAT05_STOCKOUT_ALREADY_VERIFIED');process.exit(0)}
  if(f.stockoutCheck)throw Error('Original negative purchase outcome needs inspection; do not create replacement intent')
  const offer=(await c.api('/products/'+item.goodsId+'/trial','POST',{})).offer
  const confirmation=await c.request('/purchase-confirmations','POST',{goodsId:item.goodsId,mode:'OPEN',expectedOffer:offer})
  if(confirmation.code!=='0000'){
   if(confirmation.status!==409||confirmation.code!=='STOCK_INSUFFICIENT')throw Error('Unexpected shortage confirmation result')
   f.stockoutCheck={status:'PASS',at:'confirmation',code:confirmation.code};persist(f)
  }else{
   f.stockoutCheck={confirmationId:confirmation.data.confirmationId,purchaseIntentId:randomUUID(),status:'STARTED'};persist(f)
   const result=await c.request('/orders','POST',{confirmationId:f.stockoutCheck.confirmationId,purchaseIntentId:f.stockoutCheck.purchaseIntentId})
   f.stockoutCheck.response={status:result.status,code:result.code};persist(f)
   if(result.status!==409||result.code!=='STOCK_INSUFFICIENT')throw Error('Stockout created or did not definitely reject original order')
   const original=await c.request('/orders/by-intent/'+f.stockoutCheck.purchaseIntentId)
   if(original.status!==404)throw Error('Stockout has an unexpected original order')
   f.stockoutCheck.status='PASS';persist(f)
  }
  save(path.join(work,'stockout.json'),f.stockoutCheck);console.log('CAT05_BACKEND_STOCKOUT_REJECTED no-valid-order')
 }else if(action==='cleanup'){
  const items=validateCleanupIds(fixture().items.filter(x=>x.purpose==='ACCEPTANCE'&&x.goodsId).map(x=>x.goodsId)),results=[]
  for(const item of items){const result=await setSale(c,item.key,'OFF_SALE');results.push({key:item.key,goodsId:item.goodsId,skipped:result.skipped,version:result.product.productVersion})}
  const previous=fs.existsSync(path.join(work,'cleanup.json'))?JSON.parse(fs.readFileSync(path.join(work,'cleanup.json'),'utf8')):null
  if(previous)save(path.join(work,'cleanup-repeat.json'),{status:'PASS',results})
  else save(path.join(work,'cleanup.json'),{status:'PASS',results})
  const done=fixture();done.phase='CLEANED';persist(done)
  console.log('CAT05_CLEANUP_PASS owned-samples-only/writes='+results.filter(x=>!x.skipped).length)
 }else throw Error('Explicit action required')
}finally{save(path.join(work,'api-trace-'+action+'-'+Date.now()+'.json'),c.trace)}
