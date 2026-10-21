import { describe, expect, it } from 'vitest';
import { loadConfig, assertHttpServerConfig } from '../src/config.js';
import { BridgeError } from '../src/errors.js';
import {
  directionsInput,
  findPlaceInput,
  geocodeInput,
  isCurrentLocation,
  navigationLinkInput,
  parseLatLng,
} from '../src/schemas.js';
import { TEST_API_KEY, TEST_AUTH_TOKEN } from './fixtures.js';

describe('tool input validation', () => {
  it('find_place: minimal request gets defaults', () => {
    expect(findPlaceInput.parse({ query: 'Rugby Smiles' })).toEqual({ query: 'Rugby Smiles', max_results: 3 });
  });

  it('find_place: rejects bad inputs', () => {
    expect(findPlaceInput.safeParse({}).success).toBe(false);
    expect(findPlaceInput.safeParse({ query: '  ' }).success).toBe(false);
    expect(findPlaceInput.safeParse({ query: 'x', max_results: 9 }).success).toBe(false);
    expect(findPlaceInput.safeParse({ query: 'x', extra: 1 }).success).toBe(false);
  });

  it('geocode: requires address', () => {
    expect(geocodeInput.parse({ address: 'CV21 3PU' })).toEqual({ address: 'CV21 3PU' });
    expect(geocodeInput.safeParse({ address: '' }).success).toBe(false);
  });

  it('get_directions: defaults and full request', () => {
    expect(directionsInput.parse({ destination: 'Rugby Smiles' })).toEqual({
      destination: 'Rugby Smiles',
      travel_mode: 'driving',
      avoid_tolls: false,
      avoid_highways: false,
      include_polyline: false,
    });
    const full = directionsInput.parse({
      destination: 'Rugby Station',
      origin: 'Kenilworth',
      travel_mode: 'cycling',
      avoid_tolls: true,
      avoid_highways: true,
      include_polyline: true,
    });
    expect(full.travel_mode).toBe('cycling');
  });

  it.each([
    [{}, 'destination'],
    [{ destination: '   ' }, 'destination'],
    [{ destination: 'x'.repeat(301) }, 'destination'],
    [{ destination: 'A', travel_mode: 'flying' }, 'travel_mode'],
    [{ destination: 'A', avoid_tolls: 'yes' }, 'avoid_tolls'],
    [{ destination: 'A', extra: 1 }, ''],
  ])('get_directions rejects %j', (input, path) => {
    const r = directionsInput.safeParse(input);
    expect(r.success).toBe(false);
    if (!r.success && path) expect(r.error.issues.some((i) => i.path.join('.') === path)).toBe(true);
  });

  it('navigation_link: defaults', () => {
    expect(navigationLinkInput.parse({ destination: 'Rugby Smiles' })).toEqual({
      destination: 'Rugby Smiles',
      travel_mode: 'driving',
    });
  });

  it('recognises "current location" phrasings', () => {
    for (const o of [undefined, '', 'current location', 'My current location', 'here', 'where I am']) {
      expect(isCurrentLocation(o)).toBe(true);
    }
    expect(isCurrentLocation('Kenilworth')).toBe(false);
  });

  it('parses lat,lng and rejects out-of-range values', () => {
    expect(parseLatLng('52.37, -1.26')).toEqual({ lat: 52.37, lng: -1.26 });
    expect(parseLatLng('95,0')).toBeUndefined();
    expect(parseLatLng('Rugby')).toBeUndefined();
  });
});

describe('config validation', () => {
  it('requires GOOGLE_MAPS_API_KEY', () => {
    expect(() => loadConfig({})).toThrow(/GOOGLE_MAPS_API_KEY/);
  });

  it('applies defaults', () => {
    const c = loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY });
    expect(c.HOST).toBe('127.0.0.1');
    expect(c.PORT).toBe(3460);
    expect(c.GOOGLE_UNITS).toBe('IMPERIAL');
    expect(c.MCP_AUTH_TOKEN).toBeUndefined();
  });

  it('validates GOOGLE_LOCATION_BIAS format', () => {
    expect(() => loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, GOOGLE_LOCATION_BIAS: 'Rugby' })).toThrow(/lat,lng/);
  });

  it('never echoes secret values in config errors', () => {
    try {
      loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, MCP_AUTH_TOKEN: TEST_AUTH_TOKEN, PORT: 'abc' });
      expect.unreachable();
    } catch (err) {
      expect((err as Error).message).not.toContain(TEST_API_KEY);
      expect((err as Error).message).not.toContain(TEST_AUTH_TOKEN);
    }
  });

  it('requires MCP_AUTH_TOKEN when binding beyond loopback', () => {
    const open = loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, HOST: '0.0.0.0' });
    expect(() => assertHttpServerConfig(open)).toThrow(BridgeError);
    expect(() => assertHttpServerConfig(loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY }))).not.toThrow();
    expect(() =>
      assertHttpServerConfig(loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, HOST: '0.0.0.0', MCP_AUTH_TOKEN: TEST_AUTH_TOKEN })),
    ).not.toThrow();
  });
});
