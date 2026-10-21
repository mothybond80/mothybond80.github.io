import { BridgeError } from '../errors.js';
import { fetchWithRetry, type FetchFn } from '../http/retry.js';
import type { Logger } from '../logger.js';
import { parseLatLng, type Coordinates, type TravelMode } from '../schemas.js';
import {
  normaliseGeocodeResponse,
  normalisePlacesResponse,
  normaliseRoutesResponse,
  toRoutesTravelMode,
  type ResolvedPlace,
  type RouteSummary,
} from './normalise.js';

export const PLACES_TEXT_SEARCH_URL = 'https://places.googleapis.com/v1/places:searchText';
export const GEOCODE_URL = 'https://maps.googleapis.com/maps/api/geocode/json';
export const COMPUTE_ROUTES_URL = 'https://routes.googleapis.com/directions/v2:computeRoutes';

/** Field mask for text search. Keep this list short: each extra field group costs more per call. */
export const PLACES_FIELD_MASK = [
  'places.id',
  'places.displayName',
  'places.formattedAddress',
  'places.location',
  'places.primaryTypeDisplayName',
  'places.rating',
  'places.userRatingCount',
  'places.nationalPhoneNumber',
  'places.websiteUri',
  'places.googleMapsUri',
  'places.currentOpeningHours.openNow',
];

export interface GoogleMapsClientOptions {
  apiKey: string;
  region: string;
  language: string;
  units: 'IMPERIAL' | 'METRIC';
  locationBias?: Coordinates;
  locationBiasRadiusM?: number;
  retry: { maxAttempts: number; baseDelayMs: number; maxDelayMs: number; timeoutMs?: number };
  fetch?: FetchFn;
  logger?: Logger;
  sleep?: (ms: number) => Promise<void>;
}

export interface RouteRequest {
  origin: string;
  destination: ResolvedPlace;
  travelMode: TravelMode;
  avoidTolls: boolean;
  avoidHighways: boolean;
}

/**
 * Thin Google Maps Platform client: Places (New) text search, Geocoding, and
 * Routes. Every response is validated before use.
 *
 * The API key travels in the X-Goog-Api-Key header where the API allows it.
 * Geocoding only accepts `key=` in the query string, so its URL is never logged.
 */
export class GoogleMapsClient {
  constructor(private readonly opts: GoogleMapsClientOptions) {}

  private retryOpts(label: string) {
    return {
      label,
      ...this.opts.retry,
      fetch: this.opts.fetch,
      logger: this.opts.logger,
      sleep: this.opts.sleep,
    };
  }

  /**
   * Resolve one destination: "lat,lng" as-is, otherwise Places text search
   * first (handles business names), Geocoding second (handles bare addresses).
   */
  async resolveDestination(query: string): Promise<ResolvedPlace> {
    const ll = parseLatLng(query);
    if (ll) return { name: query, address: null, coordinates: ll, placeId: null, source: 'geocoding' };
    const place = (await this.searchPlaces(query, { maxResults: 1 }))[0] ?? (await this.geocode(query));
    if (!place) {
      throw new BridgeError('DESTINATION_NOT_FOUND', `Could not find "${query}" on Google Maps`, 404);
    }
    return place;
  }

  async searchPlaces(
    query: string,
    opts: { maxResults?: number; near?: Coordinates } = {},
  ): Promise<ResolvedPlace[]> {
    const bias = opts.near ?? this.opts.locationBias;
    const body: Record<string, unknown> = {
      textQuery: query,
      languageCode: this.opts.language,
      regionCode: this.opts.region,
      pageSize: opts.maxResults ?? 3,
    };
    if (bias) {
      body.locationBias = {
        circle: {
          center: { latitude: bias.lat, longitude: bias.lng },
          radius: this.opts.locationBiasRadiusM ?? 30000,
        },
      };
    }
    const json = await this.postJson(PLACES_TEXT_SEARCH_URL, body, 'Google Places', PLACES_FIELD_MASK);
    return normalisePlacesResponse(json, query);
  }

  /** Forward geocoding for an address, or reverse geocoding for "lat,lng". */
  async geocode(query: string): Promise<ResolvedPlace | null> {
    const ll = parseLatLng(query);
    const params = new URLSearchParams({
      ...(ll ? { latlng: `${ll.lat},${ll.lng}` } : { address: query }),
      region: this.opts.region,
      language: this.opts.language,
      key: this.opts.apiKey,
    });
    const res = await fetchWithRetry(`${GEOCODE_URL}?${params}`, { method: 'GET' }, this.retryOpts('Google Geocoding'));
    const json = await this.readJson(res, 'Google Geocoding');
    return normaliseGeocodeResponse(json, query);
  }

  async computeRoute(req: RouteRequest): Promise<RouteSummary | null> {
    const mode = toRoutesTravelMode(req.travelMode);
    const body: Record<string, unknown> = {
      origin: toWaypoint(req.origin),
      destination: req.destination.placeId
        ? { placeId: req.destination.placeId }
        : { location: { latLng: { latitude: req.destination.coordinates.lat, longitude: req.destination.coordinates.lng } } },
      travelMode: mode,
      units: this.opts.units,
      languageCode: this.opts.language,
      regionCode: this.opts.region,
      polylineQuality: 'OVERVIEW',
    };
    if (mode === 'DRIVE') {
      body.routingPreference = 'TRAFFIC_AWARE';
      body.routeModifiers = { avoidTolls: req.avoidTolls, avoidHighways: req.avoidHighways };
    }
    const json = await this.postJson(COMPUTE_ROUTES_URL, body, 'Google Routes', [
      'routes.distanceMeters',
      'routes.duration',
      'routes.polyline.encodedPolyline',
      'routes.localizedValues',
    ]);
    return normaliseRoutesResponse(json);
  }

  private async postJson(url: string, body: unknown, label: string, fieldMask: string[]): Promise<unknown> {
    const res = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': this.opts.apiKey,
          'X-Goog-FieldMask': fieldMask.join(','),
        },
        body: JSON.stringify(body),
      },
      this.retryOpts(label),
    );
    return this.readJson(res, label);
  }

  private async readJson(res: Response, label: string): Promise<unknown> {
    if (!res.ok) {
      // Body is not logged or returned: Google error bodies can echo request details.
      this.opts.logger?.error({ upstream: label, status: res.status }, 'Google API error');
      // Google answers an invalid key with 400, a disabled API or restricted key with 403.
      const hint = [400, 401, 403].includes(res.status) ? ' (check the API key and that the API is enabled)' : '';
      throw new BridgeError('GOOGLE_API_ERROR', `${label} request failed with status ${res.status}${hint}`, 502, {
        status: res.status,
      });
    }
    try {
      return await res.json();
    } catch {
      throw new BridgeError('GOOGLE_API_ERROR', `${label} returned invalid JSON`, 502);
    }
  }
}

function toWaypoint(origin: string): Record<string, unknown> {
  const ll = parseLatLng(origin);
  return ll ? { location: { latLng: { latitude: ll.lat, longitude: ll.lng } } } : { address: origin };
}
