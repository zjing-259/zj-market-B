export type JoinableTeam = {
  teamId: string
  targetCount: number
  reservedCount: number
  paidCount: number
  availableSlots: number
  remainingPaidCount: number
  validEndTime: string
}

export type TeamDiscovery = {
  state: 'AVAILABLE' | 'ACTIVE_PURCHASE' | 'UNAVAILABLE'
  reason: 'NO_OFFER' | 'INELIGIBLE' | 'PRODUCT_SYNC_PENDING' | 'OUT_OF_STOCK' | null
  goodsId: string
  productVersion: string
  activityId: string | null
  serverTime: string | null
  items: JoinableTeam[]
  activeOrderId: string | null
  nextCursor: string | null
  hasMore: boolean
}
