import { describe, expect, it } from 'vitest';
import { loadConfig, assertHttpServerConfig } from '../src/config.js';
import { BridgeError } from '../src/errors.js';
import { isCurrentLocation, navigateInputSchema, parseLatLng } from '../src/schemas.js';
import { TEST_API_KEY, TEST_G2_TOKEN } from './fixtures.js';

describe('navigate_to_g2 input validation', () => {
  it('accepts a minimal request and applies defaults', () => {
    const r = navigateInputSchema.parse({ destination: 'Tim Bond Dental' });
    expect(r).toEqual({ destination: 'Tim Bond Dental', travel_mode: 'driving', avoid_tolls: false, avoid_highways: false });
  });

  it('accepts a full request', () => {
    const r = navigateInputSchema.parse({
      destination: 'Rugby Station',
      origin: 'Kenilworth',
      travel_mode: 'cycling',
      avoid_tolls: true,
      avoid_highways: true,
      notes: 'Pick up parcel',
    });
    expect(r.travel_mode).toBe('cycling');
    expect(r.notes).toBe('Pick up parcel');
  });

  it.each([
    [{}, 'destination'],
    [{ destination: '   ' }, 'destination'],
    [{ destination: 'x'.repeat(301) }, 'destination'],
    [{ destination: 'A', travel_mode: 'flying' }, 'travel_mode'],
    [{ destination: 'A', avoid_tolls: 'yes' }, 'avoid_tolls'],
    [{ destination: 'A', notes: 'n'.repeat(501) }, 'notes'],
    [{ destination: 'A', extra: 1 }, ''],
  ])('rejects %j', (input, path) => {
    const r = navigateInputSchema.safeParse(input);
    expect(r.success).toBe(false);
    if (!r.success && path) expect(r.error.issues.some((i) => i.path.join('.') === path)).toBe(true);
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

  it('defaults to mock mode', () => {
    expect(loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY }).G2_MODE).toBe('mock');
  });

  it('requires a URL for webhook mode, and https for non-local hosts', () => {
    expect(() => loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, G2_MODE: 'webhook' })).toThrow(/G2_NAVIGATION_API_URL/);
    expect(() =>
      loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, G2_MODE: 'webhook', G2_NAVIGATION_API_URL: 'http://example.com/hook' }),
    ).toThrow(/https/);
    expect(
      loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, G2_MODE: 'webhook', G2_NAVIGATION_API_URL: 'http://127.0.0.1:3456/nav' })
        .G2_MODE,
    ).toBe('webhook');
  });

  it('rejects unsafe deep-link schemes', () => {
    expect(() =>
      loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, G2_MODE: 'deep_link', G2_DEEP_LINK_TEMPLATE: 'javascript:alert({name})' }),
    ).toThrow(/unsafe/);
  });

  it('never echoes secret values in config errors', () => {
    try {
      loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, G2_NAVIGATION_API_TOKEN: TEST_G2_TOKEN, PORT: 'abc' });
      expect.unreachable();
    } catch (err) {
      expect((err as Error).message).not.toContain(TEST_API_KEY);
      expect((err as Error).message).not.toContain(TEST_G2_TOKEN);
    }
  });

  it('requires BRIDGE_API_TOKEN when binding beyond loopback', () => {
    const open = loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY, HOST: '0.0.0.0' });
    expect(() => assertHttpServerConfig(open)).toThrow(BridgeError);
    expect(() => assertHttpServerConfig(loadConfig({ GOOGLE_MAPS_API_KEY: TEST_API_KEY }))).not.toThrow();
  });
});
