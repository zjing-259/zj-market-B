import { request } from './auth'
import type { TeamDiscovery } from '../types/team-discovery'

export function joinableTeams(goodsId: string, owner: string, cursor?: string): Promise<TeamDiscovery> {
  const query = new URLSearchParams({ limit: cursor ? '10' : '3' })
  if (cursor) query.set('cursor', cursor)
  return request<TeamDiscovery>(`/products/${encodeURIComponent(goodsId)}/joinable-teams?${query}`, owner)
}
