export type BridgeErrorCode =
  | 'VALIDATION_ERROR'
  | 'CONFIG_ERROR'
  | 'DESTINATION_NOT_FOUND'
  | 'GOOGLE_API_ERROR'
  | 'G2_DELIVERY_FAILED'
  | 'UPSTREAM_UNAVAILABLE';

/**
 * Error whose `message` is safe to return to a client: it never contains
 * keys, tokens, request headers or raw upstream bodies.
 */
export class BridgeError extends Error {
  constructor(
    readonly code: BridgeErrorCode,
    message: string,
    readonly httpStatus = 502,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'BridgeError';
  }
}

/** Thrown by fetchWithRetry when every attempt failed with a retryable outcome. */
export class RetryExhaustedError extends BridgeError {
  constructor(
    readonly label: string,
    readonly attempts: number,
    readonly lastStatus?: number,
  ) {
    super(
      'UPSTREAM_UNAVAILABLE',
      `${label} unavailable after ${attempts} attempt(s)${lastStatus ? ` (last status ${lastStatus})` : ''}`,
      503,
      { attempts, lastStatus },
    );
    this.name = 'RetryExhaustedError';
  }
}
