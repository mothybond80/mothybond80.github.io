import { describe, expect, it } from 'vitest';
import { BridgeError } from '../src/errors.js';
import { GoogleMapsClient, PLACES_TEXT_SEARCH_URL, GEOCODE_URL, COMPUTE_ROUTES_URL } from '../src/google/google-maps.client.js';
import {
  buildGoogleMapsLink,
  formatDistance,
  formatDuration,
  normaliseGeocodeResponse,
  normalisePlacesResponse,
  normaliseRoutesResponse,
} from '../src/google/normalise.js';
import {
  TEST_API_KEY,
  fakeFetch,
  geocodeRugby,
  jsonResponse,
  noSleep,
  placesTimBondDental,
  routeKenilworthToRugby,
} from './fixtures.js';

describe('Places response normalisation', () => {
  it('takes the first place', () => {
    expect(normalisePlacesResponse(placesTimBondDental, 'tim bond dental')).toEqual({
      name: 'Tim Bond Dental',
      address: '1 Example Street, Rugby CV21 2AA, UK',
      coordinates: { lat: 52.3712, lng: -1.2614 },
      placeId: 'ChIJTEST_TimBondDental',
      source: 'places',
    });
  });

  it('returns null for an empty result ({} is what Google sends)', () => {
    expect(normalisePlacesResponse({}, 'x')).toBeNull();
  });

  it('rejects malformed coordinates', () => {
    const bad = { places: [{ id: 'a', location: { latitude: 200, longitude: 0 } }] };
    expect(() => normalisePlacesResponse(bad, 'x')).toThrow(BridgeError);
  });

  it('rejects a non-object body', () => {
    expect(() => normalisePlacesResponse('oops', 'x')).toThrow(/unexpected response/);
  });
});

describe('Geocoding response normalisation', () => {
  it('maps OK results', () => {
    expect(normaliseGeocodeResponse(geocodeRugby, 'Rugby')).toMatchObject({
      coordinates: { lat: 52.3709, lng: -1.265 },
      placeId: 'ChIJGEOCODE_Rugby',
      source: 'geocoding',
    });
  });

  it('ZERO_RESULTS is null, not an error', () => {
    expect(normaliseGeocodeResponse({ status: 'ZERO_RESULTS', results: [] }, 'x')).toBeNull();
  });

  it('REQUEST_DENIED is an error that does not leak error_message', () => {
    try {
      normaliseGeocodeResponse({ status: 'REQUEST_DENIED', error_message: `The provided API key ${TEST_API_KEY} is invalid` }, 'x');
      expect.unreachable();
    } catch (err) {
      expect((err as BridgeError).code).toBe('GOOGLE_API_ERROR');
      expect((err as Error).message).not.toContain(TEST_API_KEY);
    }
  });

  it('OVER_QUERY_LIMIT is reported as upstream-unavailable', () => {
    expect(() => normaliseGeocodeResponse({ status: 'OVER_QUERY_LIMIT' }, 'x')).toThrow(
      expect.objectContaining({ code: 'UPSTREAM_UNAVAILABLE' }),
    );
  });
});

describe('Routes response normalisation', () => {
  it('uses localised text, seconds and polyline', () => {
    expect(normaliseRoutesResponse(routeKenilworthToRugby)).toEqual({
      distanceMeters: 24300,
      durationSeconds: 1560,
      distanceText: '15.1 mi',
      durationText: '26 mins',
      encodedPolyline: '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
    });
  });

  it('formats text itself when localizedValues is missing', () => {
    const r = normaliseRoutesResponse({ routes: [{ distanceMeters: 1609.344, duration: '3900s' }] });
    expect(r?.distanceText).toBe('1.0 mi');
    expect(r?.durationText).toBe('1 hr 5 mins');
    expect(r?.encodedPolyline).toBeNull();
  });

  it('returns null when no route exists', () => {
    expect(normaliseRoutesResponse({})).toBeNull();
  });

  it('rejects a malformed duration', () => {
    expect(() => normaliseRoutesResponse({ routes: [{ duration: '26 minutes' }] })).toThrow(BridgeError);
  });

  it('formatters', () => {
    expect(formatDistance(50)).toBe('50 m');
    expect(formatDuration(30)).toBe('1 min');
    expect(formatDuration(7200)).toBe('2 hr');
  });
});

describe('Google Maps link', () => {
  const place = normalisePlacesResponse(placesTimBondDental, 'x')!;

  it('omits origin so the phone starts from its live location', () => {
    const url = new URL(buildGoogleMapsLink(place, 'driving'));
    expect(url.origin + url.pathname).toBe('https://www.google.com/maps/dir/');
    expect(url.searchParams.get('api')).toBe('1');
    expect(url.searchParams.get('origin')).toBeNull();
    expect(url.searchParams.get('destination')).toBe('Tim Bond Dental');
    expect(url.searchParams.get('destination_place_id')).toBe('ChIJTEST_TimBondDental');
    expect(url.searchParams.get('travelmode')).toBe('driving');
  });

  it('uses lat,lng without a place id and maps cycling to bicycling', () => {
    const url = new URL(buildGoogleMapsLink({ ...place, placeId: null }, 'cycling', 'Kenilworth'));
    expect(url.searchParams.get('destination')).toBe('52.3712,-1.2614');
    expect(url.searchParams.get('origin')).toBe('Kenilworth');
    expect(url.searchParams.get('travelmode')).toBe('bicycling');
  });

  it('never contains the API key', () => {
    expect(buildGoogleMapsLink(place, 'driving')).not.toContain(TEST_API_KEY);
  });
});

describe('GoogleMapsClient requests', () => {
  const client = (fetch: ReturnType<typeof fakeFetch>['fetch']) =>
    new GoogleMapsClient({
      apiKey: TEST_API_KEY,
      region: 'uk',
      language: 'en-GB',
      units: 'IMPERIAL',
      locationBias: { lat: 52.37, lng: -1.26 },
      retry: { maxAttempts: 3, baseDelayMs: 1, maxDelayMs: 2 },
      fetch,
      sleep: noSleep,
    });

  it('sends the key in a header, with a field mask and location bias', async () => {
    const f = fakeFetch({ [PLACES_TEXT_SEARCH_URL]: jsonResponse(placesTimBondDental) });
    await client(f.fetch).resolveDestination('Tim Bond Dental');
    const call = f.calls[0]!;
    const headers = call.init!.headers as Record<string, string>;
    expect(headers['X-Goog-Api-Key']).toBe(TEST_API_KEY);
    expect(headers['X-Goog-FieldMask']).toContain('places.location');
    expect(call.url).not.toContain(TEST_API_KEY);
    expect(call.body.locationBias.circle.center).toEqual({ latitude: 52.37, longitude: -1.26 });
  });

  it('falls back to Geocoding when Places finds nothing', async () => {
    const f = fakeFetch({ [PLACES_TEXT_SEARCH_URL]: jsonResponse({}), [GEOCODE_URL]: jsonResponse(geocodeRugby) });
    const place = await client(f.fetch).resolveDestination('Rugby');
    expect(place.source).toBe('geocoding');
  });

  it('throws DESTINATION_NOT_FOUND when nothing matches', async () => {
    const f = fakeFetch({
      [PLACES_TEXT_SEARCH_URL]: jsonResponse({}),
      [GEOCODE_URL]: jsonResponse({ status: 'ZERO_RESULTS', results: [] }),
    });
    await expect(client(f.fetch).resolveDestination('nowhere-xyz')).rejects.toMatchObject({ code: 'DESTINATION_NOT_FOUND' });
  });

  it('turns a 403 into a clear error without the body', async () => {
    const f = fakeFetch({ [PLACES_TEXT_SEARCH_URL]: jsonResponse({ error: { message: `key ${TEST_API_KEY}` } }, 403) });
    const err = await client(f.fetch).searchPlace('x').catch((e) => e);
    expect(err.code).toBe('GOOGLE_API_ERROR');
    expect(err.message).toMatch(/403.*API key/);
    expect(err.message).not.toContain(TEST_API_KEY);
  });

  it('builds a DRIVE route with modifiers and a placeId destination', async () => {
    const f = fakeFetch({ [COMPUTE_ROUTES_URL]: jsonResponse(routeKenilworthToRugby) });
    const place = normalisePlacesResponse(placesTimBondDental, 'x')!;
    await client(f.fetch).computeRoute({ origin: '52.34,-1.58', destination: place, travelMode: 'driving', avoidTolls: true, avoidHighways: false });
    const body = f.calls[0]!.body;
    expect(body.origin).toEqual({ location: { latLng: { latitude: 52.34, longitude: -1.58 } } });
    expect(body.destination).toEqual({ placeId: 'ChIJTEST_TimBondDental' });
    expect(body.travelMode).toBe('DRIVE');
    expect(body.routeModifiers).toEqual({ avoidTolls: true, avoidHighways: false });
    expect(body.routingPreference).toBe('TRAFFIC_AWARE');
  });

  it('omits driving-only fields for transit', async () => {
    const f = fakeFetch({ [COMPUTE_ROUTES_URL]: jsonResponse(routeKenilworthToRugby) });
    const place = normalisePlacesResponse(placesTimBondDental, 'x')!;
    await client(f.fetch).computeRoute({ origin: 'Coventry', destination: place, travelMode: 'transit', avoidTolls: true, avoidHighways: true });
    const body = f.calls[0]!.body;
    expect(body.travelMode).toBe('TRANSIT');
    expect(body.origin).toEqual({ address: 'Coventry' });
    expect(body.routeModifiers).toBeUndefined();
    expect(body.routingPreference).toBeUndefined();
  });
});
