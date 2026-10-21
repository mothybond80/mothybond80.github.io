import { describe, expect, it, vi } from 'vitest';
import { RetryExhaustedError } from '../src/errors.js';
import { backoffDelay, fetchWithRetry, isRetryableStatus } from '../src/http/retry.js';
import { createLogger } from '../src/logger.js';
import { TEST_API_KEY, fakeFetch } from './fixtures.js';

const URL_ = 'https://api.example.test/thing';
const base = { label: 'Test API', maxAttempts: 4, baseDelayMs: 100, maxDelayMs: 1000, random: () => 1 };

describe('retry policy', () => {
  it('classifies statuses', () => {
    expect([429, 500, 502, 503, 504].every(isRetryableStatus)).toBe(true);
    expect([200, 301, 400, 401, 403, 404, 422].some(isRetryableStatus)).toBe(false);
  });

  it('backs off exponentially and caps at maxDelayMs', () => {
    expect([1, 2, 3, 4, 5].map((n) => backoffDelay(n, base))).toEqual([100, 200, 400, 800, 1000]);
  });

  it('applies jitter between 50% and 100%', () => {
    expect(backoffDelay(3, { ...base, random: () => 0 })).toBe(200);
  });

  it('honours Retry-After seconds, capped', () => {
    expect(backoffDelay(1, base, '0.5')).toBe(500);
    expect(backoffDelay(1, base, '120')).toBe(1000);
  });
});

describe('fetchWithRetry', () => {
  it('retries 429 and 5xx then returns the success', async () => {
    const sleep = vi.fn(async () => undefined);
    const f = fakeFetch({
      [URL_]: [
        new Response('', { status: 429, headers: { 'Retry-After': '0' } }),
        new Response('', { status: 502 }),
        new Response('done', { status: 200 }),
      ],
    });
    const res = await fetchWithRetry(URL_, {}, { ...base, fetch: f.fetch, sleep });
    expect(await res.text()).toBe('done');
    expect(f.calls).toHaveLength(3);
    expect(sleep.mock.calls.map((c) => (c as unknown[])[0])).toEqual([0, 200]);
  });

  it('retries network errors', async () => {
    const f = fakeFetch({ [URL_]: [new TypeError('fetch failed'), new Response('ok')] });
    const res = await fetchWithRetry(URL_, {}, { ...base, fetch: f.fetch, sleep: async () => undefined });
    expect(res.status).toBe(200);
  });

  it('does not retry 4xx', async () => {
    const f = fakeFetch({ [URL_]: new Response('', { status: 400 }) });
    const res = await fetchWithRetry(URL_, {}, { ...base, fetch: f.fetch, sleep: async () => undefined });
    expect(res.status).toBe(400);
    expect(f.calls).toHaveLength(1);
  });

  it('gives up after maxAttempts with RetryExhaustedError', async () => {
    const sleep = vi.fn(async () => undefined);
    const f = fakeFetch({ [URL_]: new Response('', { status: 503 }) });
    const err = await fetchWithRetry(URL_, {}, { ...base, fetch: f.fetch, sleep }).catch((e) => e);
    expect(err).toBeInstanceOf(RetryExhaustedError);
    expect(err.code).toBe('UPSTREAM_UNAVAILABLE');
    expect(err.message).toBe('Test API unavailable after 4 attempt(s) (last status 503)');
    expect(f.calls).toHaveLength(4);
    expect(sleep).toHaveBeenCalledTimes(3);
  });

  it('times out a hung attempt and retries', async () => {
    let n = 0;
    const fetch = async (_u: string, init?: RequestInit) => {
      if (n++ === 0) {
        return new Promise<Response>((_, reject) => init?.signal?.addEventListener('abort', () => reject(init.signal!.reason)));
      }
      return new Response('ok');
    };
    const res = await fetchWithRetry(URL_, {}, { ...base, timeoutMs: 20, fetch, sleep: async () => undefined });
    expect(res.status).toBe(200);
  });

  it('never logs the query string (where Geocoding puts the key) or headers', async () => {
    const lines: string[] = [];
    const logger = createLogger('warn', { write: (s: string) => void lines.push(s) } as never);
    const f = fakeFetch({ [URL_]: [new Response('', { status: 500 }), new Response('ok')] });
    await fetchWithRetry(
      `${URL_}?address=x&key=${TEST_API_KEY}`,
      { headers: { 'X-Goog-Api-Key': TEST_API_KEY } },
      { ...base, fetch: f.fetch, logger, sleep: async () => undefined },
    );
    expect(lines.length).toBeGreaterThan(0);
    expect(lines.join('')).not.toContain(TEST_API_KEY);
    expect(lines.join('')).toContain('https://api.example.test/thing');
  });
});

describe('logger redaction', () => {
  it('redacts secret-looking keys even if something logs them by mistake', () => {
    const lines: string[] = [];
    const logger = createLogger('info', { write: (s: string) => void lines.push(s) } as never);
    logger.info({ headers: { authorization: 'Bearer x' }, apiKey: TEST_API_KEY, nested: { token: 'abc' } }, 'oops');
    const out = lines.join('');
    expect(out).not.toContain(TEST_API_KEY);
    expect(out).not.toContain('Bearer x');
    expect(out).not.toContain('"abc"');
    expect(out).toContain('[REDACTED]');
  });
});
