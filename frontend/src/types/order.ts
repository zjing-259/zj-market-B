import type { Trial } from './product'
export type Offer = NonNullable<Trial['offer']>
export type Confirmation = { confirmationId:string; mode:'OPEN'|'JOIN'; teamId:string|null; offer:Offer; quantity:1; issuedAt:string; expiresAt:string }
export type Order = { orderId:string; purchaseIntentId:string; confirmationId:string; version:string; status:'PROCESSING'|'WAITING_PAYMENT'|'CLOSING'|'CLOSED'; product:{goodsId:string;productVersion:string;name:string;imageUrl:string|null}; offer:Offer; quantity:1; mode:'OPEN'|'JOIN'; requestedTeamId:string|null; createdAt:string; reserveWaitDeadline:string; paymentEnabled:false; canCancel:boolean;updatedAt:string;reviewRequired:boolean;errorCode:string|null;teamId:string|null;aOrderId:string|null;aRecordVersion:string|null;aTeamVersion:string|null;aOrderStatus:string|null;aTeamStatus:string|null;paymentDeadline:string|null;closedAt:string|null;closeBasis:string|null }
export type OrderPage = {items:Order[];page:number;size:number;total:number}
export type PendingPurchase = {userId:string;goodsId:string;purchaseIntentId:string;confirmationId:string}

export type Team = {teamId:string;goodsId:string;activityId:string;status:string;version:string;targetCount:number;reservedCount:number;paidCount:number;validStartTime:string;validEndTime:string;serverTime:string;joinable:boolean;myOrderId:string|null}
