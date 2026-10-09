export type Envelope<T> = { code: string; message: string; data: T; requestId: string }
