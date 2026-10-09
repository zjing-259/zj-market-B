export class ApiError extends Error {
  constructor(readonly code: string, readonly status: number, readonly requestId: string) { super(code) }
}
