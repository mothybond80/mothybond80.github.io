import request from 'supertest';
import { describe, expect, it } from 'vitest';
import { buildNavigateDeps } from '../src/container.js';
import { COMPUTE_ROUTES_URL, GEOCODE_URL, PLACES_TEXT_SEARCH_URL } from '../src/google/google-maps.client.js';
import { createLogger } from '../src/logger.js';
import { navigateToG2 } from '../src/navigate.js';
import { createApp } from '../src/server.js';
import {
  TEST_API_KEY,
  TEST_G2_TOKEN,
  fakeFetch,
  jsonResponse,
  noSleep,
  placesTimBondDental,
  routeKenilworthToRugby,
  testConfig,
} from './fixtures.js';

const logger = createLogger('silent');
const HOOK = 'https://g2.example.test/navigation';
const fixed = { now: () => new Date('2026-10-20T08:00:00Z'), newId: () => 'req-1' };

/** The example from the brief: "Navigate to Tim Bond Dental from my current location". */
const TIM_BOND_DENTAL = { destination: 'Tim Bond Dental', origin: 'current location', travel_mode: 'driving' };

function setup(env: Record<string, string> = {}, routes: Parameters<typeof fakeFetch>[0] = {}) {
  const f = fakeFetch({
    [PLACES_TEXT_SEARCH_URL]: jsonResponse(placesTimBondDental),
    [COMPUTE_ROUTES_URL]: jsonResponse(routeKenilworthToRugby),
    [HOOK]: jsonResponse({ accepted: true }, 202),
    ...routes,
  });
  const deps = buildNavigateDeps(testConfig(env), logger, { fetch: f.fetch, sleep: noSleep, ...fixed });
  return { deps, calls: f.calls };
}

describe('navigate_to_g2: "Navigate to Tim Bond Dental from my current location"', () => {
  it('mock mode, no known origin: resolves the place and returns a phone-ready link', async () => {
    const { deps, calls } = setup();
    const r = await navigateToG2(TIM_BOND_DENTAL, deps);

    expect(r).toMatchObject({
      status: 'link_created',
      destination: 'Tim Bond Dental',
      coordinates: { lat: 52.3712, lng: -1.2614 },
      distance_text: null,
      duration_text: null,
      g2_deep_link: null,
      place_id: 'ChIJTEST_TimBondDental',
      origin_used: 'current location (device)',
      g2_mode: 'mock',
    });
    expect(r.g2_response).toMatch(/^\[MOCK\]/);
    expect(r.google_maps_link).toBe(
      'https://www.google.com/maps/dir/?api=1&destination=Tim+Bond+Dental&destination_place_id=ChIJTEST_TimBondDental&travelmode=driving',
    );
    expect(r.warnings?.[0]).toMatch(/No origin known/);
    expect(r.g2_payload?.display.lines[0]).toBe('To: Tim Bond Dental');
    // No route call without an origin.
    expect(calls.map((c) => c.url)).toEqual([PLACES_TEXT_SEARCH_URL]);
  });

  it('webhook mode with a GPS fix as origin: routes and sends to G2', async () => {
    const { deps, calls } = setup({ G2_MODE: 'webhook', G2_NAVIGATION_API_URL: HOOK, G2_NAVIGATION_API_TOKEN: TEST_G2_TOKEN });
    const r = await navigateToG2({ ...TIM_BOND_DENTAL, origin: '52.3478,-1.5803' }, deps);

    expect(r).toMatchObject({
      status: 'sent',
      distance_text: '15.1 mi',
      duration_text: '26 mins',
      distance_meters: 24300,
      duration_seconds: 1560,
      polyline: '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
      g2_response: '{"accepted":true}',
      g2_mode: 'webhook',
    });
    expect(r.google_maps_link).toContain('origin=52.3478%2C-1.5803');
    expect(r.g2_payload).toBeUndefined();
    const sent = calls.find((c) => c.url === HOOK)!;
    expect(sent.body.destination.place_id).toBe('ChIJTEST_TimBondDental');
    expect(sent.body.route.duration_text).toBe('26 mins');
  });

  it('uses DEFAULT_ORIGIN for "current location" but leaves it out of the Maps link', async () => {
    const { deps, calls } = setup({ DEFAULT_ORIGIN: 'Kenilworth, UK' });
    const r = await navigateToG2(TIM_BOND_DENTAL, deps);
    expect(r.duration_text).toBe('26 mins');
    expect(r.origin_used).toBe('Kenilworth, UK');
    expect(new URL(r.google_maps_link!).searchParams.get('origin')).toBeNull();
    expect(calls.find((c) => c.url === COMPUTE_ROUTES_URL)!.body.origin).toEqual({ address: 'Kenilworth, UK' });
  });

  it('deep_link mode returns the G2 link', async () => {
    const { deps } = setup({ G2_MODE: 'deep_link', G2_DEEP_LINK_TEMPLATE: 'g2nav://go?lat={lat}&lng={lng}&name={name}' });
    const r = await navigateToG2(TIM_BOND_DENTAL, deps);
    expect(r.status).toBe('link_created');
    expect(r.g2_deep_link).toBe('g2nav://go?lat=52.3712&lng=-1.2614&name=Tim%20Bond%20Dental');
  });
});

describe('navigate_to_g2 failures', () => {
  it('destination not found', async () => {
    const { deps } = setup({}, {
      [PLACES_TEXT_SEARCH_URL]: jsonResponse({}),
      [GEOCODE_URL]: jsonResponse({ status: 'ZERO_RESULTS', results: [] }),
    });
    const r = await navigateToG2({ destination: 'Nowhere Qwxyz' }, deps);
    expect(r).toMatchObject({ status: 'failed', coordinates: null, error: { code: 'DESTINATION_NOT_FOUND' } });
  });

  it('G2 down after retries: failed, but the place and Maps link are still returned', async () => {
    const { deps, calls } = setup(
      { G2_MODE: 'webhook', G2_NAVIGATION_API_URL: HOOK, RETRY_MAX_ATTEMPTS: '3' },
      { [HOOK]: new Response('', { status: 503 }) },
    );
    const r = await navigateToG2(TIM_BOND_DENTAL, deps);
    expect(r.status).toBe('failed');
    expect(r.error).toEqual({ code: 'UPSTREAM_UNAVAILABLE', message: 'G2 Navigation unavailable after 3 attempt(s) (last status 503)' });
    expect(r.coordinates).toEqual({ lat: 52.3712, lng: -1.2614 });
    expect(r.google_maps_link).toContain('destination_place_id=');
    expect(calls.filter((c) => c.url === HOOK)).toHaveLength(3);
  });

  it('rejects invalid input', async () => {
    const { deps } = setup();
    await expect(navigateToG2({ destination: '' }, deps)).rejects.toMatchObject({ code: 'VALIDATION_ERROR', httpStatus: 400 });
  });
});

describe('HTTP endpoint POST /navigate_to_g2', () => {
  const app = (env: Record<string, string> = {}) => {
    const { deps } = setup(env);
    return createApp({ deps, logger, apiToken: testConfig(env).BRIDGE_API_TOKEN });
  };

  it('returns the result as JSON', async () => {
    const res = await request(app()).post('/navigate_to_g2').send(TIM_BOND_DENTAL);
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('link_created');
    expect(res.body.coordinates).toEqual({ lat: 52.3712, lng: -1.2614 });
  });

  it('400 on invalid input or bad JSON', async () => {
    const a = app();
    expect((await request(a).post('/navigate_to_g2').send({ travel_mode: 'driving' })).status).toBe(400);
    const bad = await request(a).post('/navigate_to_g2').set('Content-Type', 'application/json').send('{nope');
    expect(bad.status).toBe(400);
    expect(bad.body.error.code).toBe('VALIDATION_ERROR');
  });

  it('enforces the bearer token when configured', async () => {
    const a = app({ BRIDGE_API_TOKEN: 'bridge-token' });
    expect((await request(a).post('/navigate_to_g2').send(TIM_BOND_DENTAL)).status).toBe(401);
    expect((await request(a).post('/navigate_to_g2').set('Authorization', 'Bearer wrong').send(TIM_BOND_DENTAL)).status).toBe(401);
    const ok = await request(a).post('/navigate_to_g2').set('Authorization', 'Bearer bridge-token').send(TIM_BOND_DENTAL);
    expect(ok.status).toBe(200);
  });

  it('never returns secrets to the client', async () => {
    const res = await request(app({ G2_MODE: 'webhook', G2_NAVIGATION_API_URL: HOOK, G2_NAVIGATION_API_TOKEN: TEST_G2_TOKEN }))
      .post('/navigate_to_g2')
      .send(TIM_BOND_DENTAL);
    expect(res.text).not.toContain(TEST_API_KEY);
    expect(res.text).not.toContain(TEST_G2_TOKEN);
    expect(res.headers['x-powered-by']).toBeUndefined();
  });

  it('health check', async () => {
    const res = await request(app()).get('/healthz');
    expect(res.body).toEqual({ ok: true, g2_mode: 'mock' });
  });
});
