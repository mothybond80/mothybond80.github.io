import request from 'supertest';
import { describe, expect, it } from 'vitest';
import { COMPUTE_ROUTES_URL, GEOCODE_URL, PLACES_TEXT_SEARCH_URL } from '../src/google/google-maps.client.js';
import { createHttpApp } from '../src/http.js';
import { createLogger } from '../src/logger.js';
import { buildToolDeps, findPlace, geocode, getDirections, navigationLink } from '../src/tools.js';
import {
  TEST_API_KEY,
  TEST_AUTH_TOKEN,
  fakeFetch,
  geocodeRugby,
  jsonResponse,
  noSleep,
  placesRugbySmiles,
  routeKenilworthToRugby,
  testConfig,
} from './fixtures.js';

const logger = createLogger('silent');

function setup(env: Record<string, string> = {}, routes: Parameters<typeof fakeFetch>[0] = {}) {
  const f = fakeFetch({
    [PLACES_TEXT_SEARCH_URL]: jsonResponse(placesRugbySmiles),
    [GEOCODE_URL]: jsonResponse(geocodeRugby),
    [COMPUTE_ROUTES_URL]: jsonResponse(routeKenilworthToRugby),
    ...routes,
  });
  const deps = buildToolDeps(testConfig(env), logger, { fetch: f.fetch, sleep: noSleep });
  return { deps, calls: f.calls };
}

describe('find_place', () => {
  it('returns the places with chat-friendly fields', async () => {
    const { deps } = setup();
    const r = await findPlace({ query: 'Rugby Smiles', max_results: 3 }, deps);
    expect(r.results).toHaveLength(2);
    expect(r.results[0]).toEqual({
      name: 'Rugby Smiles',
      address: 'Church Street, Rugby CV21 3PU, UK',
      coordinates: { lat: 52.3728, lng: -1.2598 },
      place_id: 'ChIJTEST_RugbySmiles',
      type: 'Dentist',
      rating: 4.9,
      rating_count: 120,
      phone: '01788 000000',
      website: 'https://rugbysmiles.co.uk/',
      open_now: true,
      google_maps_link: 'https://maps.google.com/?cid=1',
    });
  });

  it('rejects a malformed near', async () => {
    const { deps } = setup();
    await expect(findPlace({ query: 'x', near: 'Rugby', max_results: 1 }, deps)).rejects.toMatchObject({ code: 'VALIDATION_ERROR' });
  });
});

describe('geocode', () => {
  it('returns coordinates and a search link', async () => {
    const { deps } = setup();
    const r = await geocode({ address: 'Rugby' }, deps);
    expect(r).toEqual({
      query: 'Rugby',
      address: 'Rugby, UK',
      coordinates: { lat: 52.3709, lng: -1.265 },
      place_id: 'ChIJGEOCODE_Rugby',
      google_maps_link: 'https://www.google.com/maps/search/?api=1&query=52.3709%2C-1.265',
    });
  });

  it('DESTINATION_NOT_FOUND on zero results', async () => {
    const { deps } = setup({}, { [GEOCODE_URL]: jsonResponse({ status: 'ZERO_RESULTS', results: [] }) });
    await expect(geocode({ address: 'nowhere' }, deps)).rejects.toMatchObject({ code: 'DESTINATION_NOT_FOUND' });
  });
});

describe('get_directions', () => {
  const base = { destination: 'Rugby Smiles', travel_mode: 'driving' as const, avoid_tolls: false, avoid_highways: false, include_polyline: false };

  it('no origin and no DEFAULT_ORIGIN: resolves the place, link starts from the phone', async () => {
    const { deps, calls } = setup();
    const r = await getDirections({ ...base, origin: 'current location' }, deps);
    expect(r.destination.name).toBe('Rugby Smiles');
    expect(r.distance_text).toBeNull();
    expect(r.origin_used).toBe('current location (device)');
    expect(r.google_maps_link).toBe(
      'https://www.google.com/maps/dir/?api=1&destination=Rugby+Smiles&destination_place_id=ChIJTEST_RugbySmiles&travelmode=driving',
    );
    expect(r.warnings?.[0]).toMatch(/No origin given/);
    expect(calls.map((c) => c.url)).toEqual([PLACES_TEXT_SEARCH_URL]);
  });

  it('with a GPS origin: distance, duration and origin in the link', async () => {
    const { deps } = setup();
    const r = await getDirections({ ...base, origin: '52.3478,-1.5803' }, deps);
    expect(r).toMatchObject({ distance_text: '15.1 mi', duration_text: '26 mins', distance_meters: 24300, duration_seconds: 1560 });
    expect(r.google_maps_link).toContain('origin=52.3478%2C-1.5803');
    expect('polyline' in r).toBe(false);
  });

  it('DEFAULT_ORIGIN fills in for "current location" but stays out of the link', async () => {
    const { deps, calls } = setup({ DEFAULT_ORIGIN: 'Kenilworth, UK' });
    const r = await getDirections({ ...base, include_polyline: true }, deps);
    expect(r.duration_text).toBe('26 mins');
    expect(r.origin_used).toBe('Kenilworth, UK');
    expect(r.polyline).toBe('_p~iF~ps|U_ulLnnqC_mqNvxq`@');
    expect(new URL(r.google_maps_link).searchParams.get('origin')).toBeNull();
    expect(calls.find((c) => c.url === COMPUTE_ROUTES_URL)!.body.origin).toEqual({ address: 'Kenilworth, UK' });
  });

  it('propagates DESTINATION_NOT_FOUND', async () => {
    const { deps } = setup({}, {
      [PLACES_TEXT_SEARCH_URL]: jsonResponse({}),
      [GEOCODE_URL]: jsonResponse({ status: 'ZERO_RESULTS', results: [] }),
    });
    await expect(getDirections({ ...base, destination: 'Nowhere Qwxyz' }, deps)).rejects.toMatchObject({ code: 'DESTINATION_NOT_FOUND' });
  });
});

describe('navigation_link', () => {
  it('builds a link without touching Google', () => {
    const { deps, calls } = setup();
    const r = navigationLink({ destination: 'Rugby Smiles, Rugby', travel_mode: 'walking' }, deps);
    expect(r.google_maps_link).toBe('https://www.google.com/maps/dir/?api=1&destination=Rugby+Smiles%2C+Rugby&travelmode=walking');
    expect(calls).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Streamable HTTP transport, end to end with JSON-RPC
// ---------------------------------------------------------------------------

const MCP_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' };

/** Parses either a plain JSON body or an SSE body carrying one JSON-RPC message. */
function parseMcpBody(res: request.Response): any {
  const text = res.text;
  if (res.headers['content-type']?.includes('text/event-stream')) {
    const data = text.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim());
    return JSON.parse(data[data.length - 1]!);
  }
  return JSON.parse(text);
}

describe('Streamable HTTP endpoint', () => {
  const app = (env: Record<string, string> = {}, routes: Parameters<typeof fakeFetch>[0] = {}) => {
    const { deps } = setup(env, routes);
    return createHttpApp({ deps, logger, authToken: testConfig(env).MCP_AUTH_TOKEN });
  };

  const initialize = {
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'test', version: '1' } },
  };

  it('answers initialize and lists the four tools', async () => {
    const a = app();
    const init = await request(a).post('/mcp').set(MCP_HEADERS).send(initialize);
    expect(init.status).toBe(200);
    expect(parseMcpBody(init).result.serverInfo.name).toBe('google-maps-mcp');

    const list = await request(a).post('/mcp').set(MCP_HEADERS).send({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
    const names = parseMcpBody(list).result.tools.map((t: { name: string }) => t.name).sort();
    expect(names).toEqual(['find_place', 'geocode', 'get_directions', 'navigation_link']);
  });

  it('calls a tool at the root path too', async () => {
    const res = await request(app())
      .post('/')
      .set(MCP_HEADERS)
      .send({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'find_place', arguments: { query: 'Rugby Smiles' } } });
    const body = parseMcpBody(res);
    expect(body.result.isError).toBeFalsy();
    expect(body.result.structuredContent.results[0].name).toBe('Rugby Smiles');
  });

  it('reports a tool failure as isError without secrets', async () => {
    const res = await request(app({}, { [PLACES_TEXT_SEARCH_URL]: jsonResponse({ error: `key ${TEST_API_KEY}` }, 403) }))
      .post('/mcp')
      .set(MCP_HEADERS)
      .send({ jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'find_place', arguments: { query: 'x' } } });
    const body = parseMcpBody(res);
    expect(body.result.isError).toBe(true);
    expect(res.text).not.toContain(TEST_API_KEY);
    expect(body.result.content[0].text).toMatch(/GOOGLE_API_ERROR/);
  });

  it('enforces the bearer token when configured', async () => {
    const a = app({ MCP_AUTH_TOKEN: TEST_AUTH_TOKEN });
    expect((await request(a).post('/mcp').set(MCP_HEADERS).send(initialize)).status).toBe(401);
    expect((await request(a).post('/mcp').set(MCP_HEADERS).set('Authorization', 'Bearer wrong').send(initialize)).status).toBe(401);
    const ok = await request(a).post('/mcp').set(MCP_HEADERS).set('Authorization', `Bearer ${TEST_AUTH_TOKEN}`).send(initialize);
    expect(ok.status).toBe(200);
  });

  it('GET and DELETE are 405 (stateless), /healthz is open', async () => {
    const a = app({ MCP_AUTH_TOKEN: TEST_AUTH_TOKEN });
    expect((await request(a).get('/mcp').set('Authorization', `Bearer ${TEST_AUTH_TOKEN}`)).status).toBe(405);
    expect((await request(a).delete('/mcp').set('Authorization', `Bearer ${TEST_AUTH_TOKEN}`)).status).toBe(405);
    const health = await request(a).get('/healthz');
    expect(health.body).toEqual({ ok: true, server: 'google-maps-mcp', version: '0.2.0' });
    expect(health.headers['x-powered-by']).toBeUndefined();
  });
});
