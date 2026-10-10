export type Inventory = { goodsId: string; available: string; reserved: string; sold: string; version: string; updatedAt: string }
export type InventoryRequest = { kind: 'INBOUND' | 'ADJUST'; goodsId: string; delta: string; expectedVersion: string; reason: string }
export type InventoryResult = { operationId: string; request: InventoryRequest; outcome: 'SUCCEEDED' | 'REJECTED'; code: string; message: string; completedAt: string; inventory: Inventory }
export type PendingInventory = { userId: string; operationId: string; request: InventoryRequest; createdAt: number }
export type InventoryPage = { items: Inventory[]; page: number; size: number; total: number }
export type Ledger = { ledgerId: string; actorId: string; operationId: string; kind: string; before: {available:string}; after: {available:string}; delta: {available:string}; reason: string; createdAt: string }
