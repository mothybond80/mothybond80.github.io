import { RetryExhaustedError } from '../errors.js';
import { safeUrl, type Logger } from '../logger.js';

export type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

export interface RetryOptions {
  /** Short name for logs and errors, e.g. "Google Places". */
  label: string;
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
  /** Per-attempt timeout. */
  timeoutMs?: number;
  fetch?: FetchFn;
  logger?: Logger;
  /** Injected for tests. */
  sleep?: (ms: number) => Promise<void>;
  /** Injected for tests; returns [0, 1). */
  random?: () => number;
}

export const defaultSleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function isRetryableStatus(status: number): boolean {
  return status === 429 || (status >= 500 && status <= 599);
}

/**
 * Full-jitter exponential backoff: random(0.5..1) * min(max, base * 2^(n-1)).
 * A Retry-After header (seconds or HTTP date) wins when present, capped at maxDelayMs.
 */
export function backoffDelay(
  attempt: number,
  opts: Pick<RetryOptions, 'baseDelayMs' | 'maxDelayMs' | 'random'>,
  retryAfter?: string | null,
): number {
  const fromHeader = parseRetryAfter(retryAfter);
  if (fromHeader !== undefined) return Math.min(fromHeader, opts.maxDelayMs);
  const exp = Math.min(opts.maxDelayMs, opts.baseDelayMs * 2 ** (attempt - 1));
  const rnd = (opts.random ?? Math.random)();
  return Math.round(exp * (0.5 + rnd / 2));
}

function parseRetryAfter(value?: string | null): number | undefined {
  if (!value) return undefined;
  const secs = Number(value);
  if (Number.isFinite(secs) && secs >= 0) return secs * 1000;
  const date = Date.parse(value);
  if (!Number.isNaN(date)) return Math.max(0, date - Date.now());
  return undefined;
}

/**
 * fetch with retries on 429, 5xx, network errors and timeouts.
 *
 * - Non-retryable responses (2xx, 3xx, 4xx other than 429) are returned as-is
 *   for the caller to interpret.
 * - When every attempt fails retryably, throws RetryExhaustedError.
 * - Logs only the host+path of the URL, never headers or query strings.
 */
export async function fetchWithRetry(url: string, init: RequestInit, opts: RetryOptions): Promise<Response> {
  const doFetch = opts.fetch ?? (globalThis.fetch as FetchFn);
  const sleep = opts.sleep ?? defaultSleep;
  const target = safeUrl(url);
  let lastStatus: number | undefined;

  for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
    let retryAfter: string | null = null;
    try {
      const signal = opts.timeoutMs ? AbortSignal.timeout(opts.timeoutMs) : undefined;
      const res = await doFetch(url, signal ? { ...init, signal } : init);
      if (!isRetryableStatus(res.status)) return res;

      lastStatus = res.status;
      retryAfter = res.headers.get('retry-after');
      // Release the body so the connection can be reused. Not awaited: a
      // cancel can stay pending (e.g. on a tee'd stream) and must not stall retries.
      res.body?.cancel().catch(() => undefined);
      opts.logger?.warn({ upstream: opts.label, target, status: res.status, attempt }, 'retryable upstream status');
    } catch (err) {
      lastStatus = undefined;
      const reason = err instanceof Error ? err.name : 'unknown';
      opts.logger?.warn({ upstream: opts.label, target, attempt, reason }, 'upstream request failed');
    }

    if (attempt < opts.maxAttempts) {
      await sleep(backoffDelay(attempt, opts, retryAfter));
    }
  }

  throw new RetryExhaustedError(opts.label, opts.maxAttempts, lastStatus);
}
