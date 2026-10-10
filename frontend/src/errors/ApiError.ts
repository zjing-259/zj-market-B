export class ApiError extends Error {
  constructor(readonly code: string, readonly status: number, readonly requestId: string, readonly data?: unknown) { super(code) }
}
