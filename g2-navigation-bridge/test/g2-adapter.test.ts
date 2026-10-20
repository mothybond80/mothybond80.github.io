import { describe, expect, it } from 'vitest';
import {
  DeepLinkG2Adapter,
  MockG2Adapter,
  WebhookG2Adapter,
  buildG2DeepLink,
  createG2Adapter,
  mapToG2Payload,
  type G2NavigationTarget,
} from '../src/adapters/g2-navigation.adapter.js';
import { TEST_G2_TOKEN, fakeFetch, jsonResponse, noSleep, testConfig } from './fixtures.js';

const target: G2NavigationTarget = {
  name: 'Tim Bond Dental',
  address: '1 Example Street, Rugby CV21 2AA, UK',
  lat: 52.3712,
  lng: -1.2614,
  placeId: 'ChIJTEST_TimBondDental',
  travelMode: 'driving',
  distanceMeters: 24300,
  durationSeconds: 1560,
  distanceText: '15.1 mi',
  durationText: '26 mins',
  encodedPolyline: 'abc',
  googleMapsLink: 'https://www.google.com/maps/dir/?api=1&destination=Tim+Bond+Dental',
};

const meta = { requestId: 'req-1', now: new Date('2026-10-20T08:00:00Z') };
const HOOK = 'https://g2.example.test/navigation';

describe('G2 payload mapping', () => {
  it('maps every field', () => {
    expect(mapToG2Payload(target, meta)).toEqual({
      type: 'navigation.request',
      version: 1,
      request_id: 'req-1',
      requested_at: '2026-10-20T08:00:00.000Z',
      destination: {
        name: 'Tim Bond Dental',
        address: '1 Example Street, Rugby CV21 2AA, UK',
        lat: 52.3712,
        lng: -1.2614,
        place_id: 'ChIJTEST_TimBondDental',
      },
      route: {
        mode: 'driving',
        distance_m: 24300,
        duration_s: 1560,
        distance_text: '15.1 mi',
        duration_text: '26 mins',
        polyline: 'abc',
      },
      links: { google_maps: target.googleMapsLink },
      display: { lines: ['To: Tim Bond Dental', '15.1 mi · 26 mins (driving)'] },
      notes: null,
    });
  });

  it('keeps display lines short for the 576px display and handles a missing route', () => {
    const p = mapToG2Payload(
      { ...target, name: 'A very long destination name that will not fit', distanceText: null, durationText: null, notes: 'Bring the paperwork please' },
      meta,
    );
    expect(p.display.lines.every((l) => l.length <= 32)).toBe(true);
    expect(p.display.lines[0]!.endsWith('…')).toBe(true);
    expect(p.display.lines[1]).toBe('Mode: driving');
    expect(p.notes).toBe('Bring the paperwork please');
  });
});

describe('G2 deep link', () => {
  it('fills and URL-encodes placeholders', () => {
    expect(buildG2DeepLink('g2nav://go?lat={lat}&lng={lng}&name={name}&m={mode}', target)).toBe(
      'g2nav://go?lat=52.3712&lng=-1.2614&name=Tim%20Bond%20Dental&m=driving',
    );
  });

  it('rejects unknown placeholders', () => {
    expect(() => buildG2DeepLink('g2nav://go?x={token}', target)).toThrow(/unknown placeholder/);
  });

  it('deep_link adapter returns link_created and makes no request', async () => {
    const r = await new DeepLinkG2Adapter('g2nav://go?id={place_id}').deliver(target);
    expect(r).toMatchObject({ status: 'link_created', mode: 'deep_link', deepLink: 'g2nav://go?id=ChIJTEST_TimBondDental' });
  });
});

describe('mock adapter', () => {
  it('is the default and never claims to have sent anything', async () => {
    const adapter = createG2Adapter(testConfig());
    expect(adapter).toBeInstanceOf(MockG2Adapter);
    const r = await adapter.deliver(target);
    expect(r.status).toBe('link_created');
    expect(r.g2Response).toMatch(/^\[MOCK\]/);
    expect(r.payload?.destination.name).toBe('Tim Bond Dental');
  });
});

describe('webhook adapter', () => {
  const make = (fetch: ReturnType<typeof fakeFetch>['fetch'], maxAttempts = 3) =>
    new WebhookG2Adapter(
      { url: HOOK, token: TEST_G2_TOKEN, timeoutMs: 1000, retry: { maxAttempts, baseDelayMs: 1, maxDelayMs: 2 } },
      { fetch, sleep: noSleep, newId: () => 'req-1', now: () => meta.now },
    );

  it('POSTs the mapped payload with bearer auth and an idempotency key', async () => {
    const f = fakeFetch({ [HOOK]: jsonResponse({ accepted: true, id: 'nav-9' }, 202) });
    const r = await make(f.fetch).deliver(target);
    const call = f.calls[0]!;
    const headers = call.init!.headers as Record<string, string>;
    expect(call.init!.method).toBe('POST');
    expect(headers.Authorization).toBe(`Bearer ${TEST_G2_TOKEN}`);
    expect(headers['Idempotency-Key']).toBe('req-1');
    expect(call.body).toEqual(mapToG2Payload(target, meta));
    expect(r).toMatchObject({ status: 'sent', mode: 'webhook', g2Response: '{"accepted":true,"id":"nav-9"}' });
    expect(JSON.stringify(r)).not.toContain(TEST_G2_TOKEN);
  });

  it('retries a 503 with the same idempotency key, then succeeds', async () => {
    const f = fakeFetch({ [HOOK]: [new Response('busy', { status: 503 }), new Response('ok', { status: 200 })] });
    const r = await make(f.fetch).deliver(target);
    expect(f.calls).toHaveLength(2);
    const keys = f.calls.map((c) => (c.init!.headers as Record<string, string>)['Idempotency-Key']);
    expect(new Set(keys).size).toBe(1);
    expect(r.g2Response).toBe('ok');
  });

  it('does not retry a 401 and hints at the token without exposing it', async () => {
    const f = fakeFetch({ [HOOK]: new Response(`bad token ${TEST_G2_TOKEN}`, { status: 401 }) });
    const err = await make(f.fetch).deliver(target).catch((e) => e);
    expect(f.calls).toHaveLength(1);
    expect(err.code).toBe('G2_DELIVERY_FAILED');
    expect(err.message).toContain('G2_NAVIGATION_API_TOKEN');
    expect(err.message).not.toContain(TEST_G2_TOKEN);
  });

  it('truncates long G2 responses', async () => {
    const f = fakeFetch({ [HOOK]: new Response('x'.repeat(2000), { status: 200 }) });
    const r = await make(f.fetch).deliver(target);
    expect(r.g2Response.length).toBe(500);
  });
});
