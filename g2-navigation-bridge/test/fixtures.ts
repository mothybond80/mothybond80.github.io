import type { FetchFn } from '../src/http/retry.js';
import { loadConfig, type Config } from '../src/config.js';

export const TEST_API_KEY = 'AIza-TEST-KEY-should-never-appear';
export const TEST_G2_TOKEN = 'g2-secret-token-should-never-appear';

export function testConfig(overrides: Record<string, string> = {}): Config {
  return loadConfig({
    GOOGLE_MAPS_API_KEY: TEST_API_KEY,
    GOOGLE_LOCATION_BIAS: '52.3709,-1.2650',
    RETRY_BASE_DELAY_MS: '1',
    RETRY_MAX_DELAY_MS: '5',
    LOG_LEVEL: 'silent',
    ...overrides,
  });
}

/** Shapes taken from the Places (New), Geocoding and Routes API docs. */
export const placesTimBondDental = {
  places: [
    {
      id: 'ChIJTEST_TimBondDental',
      displayName: { text: 'Tim Bond Dental', languageCode: 'en' },
      formattedAddress: '1 Example Street, Rugby CV21 2AA, UK',
      location: { latitude: 52.3712, longitude: -1.2614 },
    },
  ],
};

export const geocodeRugby = {
  status: 'OK',
  results: [
    {
      place_id: 'ChIJGEOCODE_Rugby',
      formatted_address: 'Rugby, UK',
      geometry: { location: { lat: 52.3709, lng: -1.265 } },
    },
  ],
};

export const routeKenilworthToRugby = {
  routes: [
    {
      distanceMeters: 24300,
      duration: '1560s',
      polyline: { encodedPolyline: '_p~iF~ps|U_ulLnnqC_mqNvxq`@' },
      localizedValues: {
        distance: { text: '15.1 mi' },
        duration: { text: '26 mins' },
        staticDuration: { text: '24 mins' },
      },
    },
  ],
};

export function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

export interface RecordedCall {
  url: string;
  init?: RequestInit;
  body?: any;
}

/**
 * Fake fetch routing by URL prefix. Each handler may be a value or a list of
 * values consumed in order (last one repeats), to script retries.
 */
export function fakeFetch(routes: Record<string, Response | Error | Array<Response | Error> | (() => Response)>) {
  const calls: RecordedCall[] = [];
  const counters = new Map<string, number>();
  const fetch: FetchFn = async (url, init) => {
    calls.push({ url, init, body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined });
    const key = Object.keys(routes).find((k) => url.startsWith(k));
    if (!key) throw new Error(`unexpected fetch ${url}`);
    const handler = routes[key]!;
    let out: Response | Error;
    if (typeof handler === 'function') out = handler();
    else if (Array.isArray(handler)) {
      const i = counters.get(key) ?? 0;
      counters.set(key, i + 1);
      out = handler[Math.min(i, handler.length - 1)]!;
      if (out instanceof Response) out = out.clone();
    } else out = handler instanceof Response ? handler.clone() : handler;
    if (out instanceof Error) throw out;
    return out;
  };
  return { fetch, calls };
}

export const noSleep = async () => undefined;
