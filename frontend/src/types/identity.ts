export type User = { userId: string; loginName: string; displayName: string; roles: string[] }
export type Tokens = { accessToken: string; tokenType: 'Bearer'; expiresIn: number; user: User }
