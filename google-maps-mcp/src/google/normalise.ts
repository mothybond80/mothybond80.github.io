import { z } from 'zod';
import { BridgeError } from '../errors.js';
import type { Coordinates, TravelMode } from '../schemas.js';

/** A place resolved by Google, independent of which API found it. */
export interface ResolvedPlace {
  name: string;
  address: string | null;
  coordinates: Coordinates;
  placeId: string | null;
  source: 'places' | 'geocoding';
  type?: string | null;
  rating?: number | null;
  ratingCount?: number | null;
  phone?: string | null;
  website?: string | null;
  openNow?: boolean | null;
  googleMapsLink?: string | null;
}

export interface RouteSummary {
  distanceMeters: number | null;
  durationSeconds: number | null;
  distanceText: string | null;
  durationText: string | null;
  encodedPolyline: string | null;
}

// ---------------------------------------------------------------------------
// Response schemas. Only the fields we use are validated; anything else is
// ignored. A response that fails validation is treated as an upstream error,
// never passed through.
// ---------------------------------------------------------------------------

const latitude = z.number().min(-90).max(90);
const longitude = z.number().min(-180).max(180);

/** Places API (New) – places:searchText */
export const placesTextSearchResponseSchema = z.object({
  places: z
    .array(
      z.object({
        id: z.string().min(1).optional(),
        displayName: z.object({ text: z.string().min(1) }).optional(),
        formattedAddress: z.string().optional(),
        location: z.object({ latitude, longitude }),
        primaryTypeDisplayName: z.object({ text: z.string() }).optional(),
        rating: z.number().min(0).max(5).optional(),
        userRatingCount: z.number().int().nonnegative().optional(),
        nationalPhoneNumber: z.string().optional(),
        websiteUri: z.string().optional(),
        googleMapsUri: z.string().optional(),
        currentOpeningHours: z.object({ openNow: z.boolean().optional() }).optional(),
      }),
    )
    .optional(),
});

/** Geocoding API – /maps/api/geocode/json */
export const geocodeResponseSchema = z.object({
  status: z.string(),
  error_message: z.string().optional(),
  results: z
    .array(
      z.object({
        place_id: z.string().optional(),
        formatted_address: z.string().optional(),
        geometry: z.object({ location: z.object({ lat: latitude, lng: longitude }) }),
      }),
    )
    .default([]),
});

/** Routes API – directions/v2:computeRoutes */
export const computeRoutesResponseSchema = z.object({
  routes: z
    .array(
      z.object({
        distanceMeters: z.number().nonnegative().optional(),
        duration: z
          .string()
          .regex(/^\d+(\.\d+)?s$/)
          .optional(),
        polyline: z.object({ encodedPolyline: z.string() }).optional(),
        localizedValues: z
          .object({
            distance: z.object({ text: z.string() }).optional(),
            duration: z.object({ text: z.string() }).optional(),
          })
          .optional(),
      }),
    )
    .optional(),
});

function invalid(api: string, err: z.ZodError): BridgeError {
  const where = err.issues[0]?.path.join('.') || 'body';
  return new BridgeError('GOOGLE_API_ERROR', `${api} returned an unexpected response (${where})`, 502);
}

/** All places from a Text Search response (empty when there were no results). */
export function normalisePlacesResponse(raw: unknown, query: string): ResolvedPlace[] {
  const parsed = placesTextSearchResponseSchema.safeParse(raw);
  if (!parsed.success) throw invalid('Google Places', parsed.error);
  return (parsed.data.places ?? []).map((p) => ({
    name: p.displayName?.text ?? query,
    address: p.formattedAddress ?? null,
    coordinates: { lat: p.location.latitude, lng: p.location.longitude },
    placeId: p.id ?? null,
    source: 'places' as const,
    type: p.primaryTypeDisplayName?.text ?? null,
    rating: p.rating ?? null,
    ratingCount: p.userRatingCount ?? null,
    phone: p.nationalPhoneNumber ?? null,
    website: p.websiteUri ?? null,
    openNow: p.currentOpeningHours?.openNow ?? null,
    googleMapsLink: p.googleMapsUri ?? null,
  }));
}

const GEOCODE_RETRYABLE = new Set(['OVER_QUERY_LIMIT', 'UNKNOWN_ERROR']);

/**
 * First geocoding result, or null for ZERO_RESULTS.
 * Geocoding reports errors in a 200 body, so status is checked here.
 */
export function normaliseGeocodeResponse(raw: unknown, query: string): ResolvedPlace | null {
  const parsed = geocodeResponseSchema.safeParse(raw);
  if (!parsed.success) throw invalid('Google Geocoding', parsed.error);
  const { status, results } = parsed.data;

  if (status === 'ZERO_RESULTS') return null;
  if (status !== 'OK') {
    // error_message can quote the request; it is deliberately not surfaced.
    throw new BridgeError(
      GEOCODE_RETRYABLE.has(status) ? 'UPSTREAM_UNAVAILABLE' : 'GOOGLE_API_ERROR',
      `Google Geocoding failed with status ${status}`,
      GEOCODE_RETRYABLE.has(status) ? 503 : 502,
      { googleStatus: status },
    );
  }
  const first = results[0];
  if (!first) return null;
  return {
    name: first.formatted_address ?? query,
    address: first.formatted_address ?? null,
    coordinates: first.geometry.location,
    placeId: first.place_id ?? null,
    source: 'geocoding',
  };
}

/** First route, or null when Google found no route (e.g. walking across the sea). */
export function normaliseRoutesResponse(raw: unknown): RouteSummary | null {
  const parsed = computeRoutesResponseSchema.safeParse(raw);
  if (!parsed.success) throw invalid('Google Routes', parsed.error);
  const route = parsed.data.routes?.[0];
  if (!route) return null;

  const durationSeconds = route.duration ? Math.round(parseFloat(route.duration)) : null;
  const distanceMeters = route.distanceMeters ?? null;
  return {
    distanceMeters,
    durationSeconds,
    distanceText: route.localizedValues?.distance?.text ?? (distanceMeters !== null ? formatDistance(distanceMeters) : null),
    durationText: route.localizedValues?.duration?.text ?? (durationSeconds !== null ? formatDuration(durationSeconds) : null),
    encodedPolyline: route.polyline?.encodedPolyline ?? null,
  };
}

/** Fallback formatting when Google omits localizedValues. UK-style miles. */
export function formatDistance(meters: number): string {
  const miles = meters / 1609.344;
  return miles < 0.1 ? `${Math.round(meters)} m` : `${miles.toFixed(1)} mi`;
}

export function formatDuration(seconds: number): string {
  const mins = Math.max(1, Math.round(seconds / 60));
  if (mins < 60) return `${mins} min${mins === 1 ? '' : 's'}`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h} hr ${m} min${m === 1 ? '' : 's'}` : `${h} hr`;
}

const ROUTES_TRAVEL_MODE: Record<TravelMode, string> = {
  driving: 'DRIVE',
  walking: 'WALK',
  cycling: 'BICYCLE',
  transit: 'TRANSIT',
};
export const toRoutesTravelMode = (m: TravelMode) => ROUTES_TRAVEL_MODE[m];

const MAPS_URL_TRAVEL_MODE: Record<TravelMode, string> = {
  driving: 'driving',
  walking: 'walking',
  cycling: 'bicycling',
  transit: 'transit',
};

/**
 * Google Maps "Maps URLs" directions link. With no origin, Google Maps uses
 * the device's current location, which is exactly what "from my current
 * location" needs. Accepts a resolved place (uses its place ID) or a plain
 * destination string.
 */
export function buildGoogleMapsLink(
  place: ResolvedPlace | string,
  travelMode: TravelMode,
  origin?: string,
): string {
  const params = new URLSearchParams({ api: '1' });
  if (origin) params.set('origin', origin);
  if (typeof place === 'string') {
    params.set('destination', place);
  } else {
    params.set('destination', place.placeId ? place.name : `${place.coordinates.lat},${place.coordinates.lng}`);
    if (place.placeId) params.set('destination_place_id', place.placeId);
  }
  params.set('travelmode', MAPS_URL_TRAVEL_MODE[travelMode]);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}
