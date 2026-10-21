import { z } from 'zod';

export const TRAVEL_MODES = ['driving', 'walking', 'cycling', 'transit'] as const;
export type TravelMode = (typeof TRAVEL_MODES)[number];

export interface Coordinates {
  lat: number;
  lng: number;
}

const destination = z
  .string()
  .trim()
  .min(1, 'destination is required')
  .max(300, 'destination is too long')
  .describe('Place name, business name, address or "lat,lng", e.g. "Rugby Smiles, Rugby"');

const origin = z
  .string()
  .trim()
  .max(300, 'origin is too long')
  .optional()
  .describe('Start address or "lat,lng". Omit, or say "current location", to use the configured default origin.');

const travelMode = z.enum(TRAVEL_MODES).default('driving');

/** Raw zod shapes: the MCP SDK turns these into JSON Schema for the tool listing. */
export const findPlaceShape = {
  query: z
    .string()
    .trim()
    .min(1, 'query is required')
    .max(300, 'query is too long')
    .describe('What to look for: a business name, "dentist near Rugby", a landmark or an address'),
  near: z
    .string()
    .trim()
    .max(100)
    .optional()
    .describe('Optional "lat,lng" to search around. Defaults to the configured location bias.'),
  max_results: z.number().int().min(1).max(5).default(3),
};

export const geocodeShape = {
  address: z
    .string()
    .trim()
    .min(1, 'address is required')
    .max(300, 'address is too long')
    .describe('A postal address or postcode, or "lat,lng" to reverse-geocode'),
};

export const directionsShape = {
  destination,
  origin,
  travel_mode: travelMode,
  avoid_tolls: z.boolean().default(false),
  avoid_highways: z.boolean().default(false),
  include_polyline: z
    .boolean()
    .default(false)
    .describe('Include the encoded overview polyline (large; only useful for drawing the route)'),
};

export const navigationLinkShape = {
  destination,
  origin,
  travel_mode: travelMode,
};

export const findPlaceInput = z.object(findPlaceShape).strict();
export const geocodeInput = z.object(geocodeShape).strict();
export const directionsInput = z.object(directionsShape).strict();
export const navigationLinkInput = z.object(navigationLinkShape).strict();

export type FindPlaceInput = z.infer<typeof findPlaceInput>;
export type GeocodeInput = z.infer<typeof geocodeInput>;
export type DirectionsInput = z.infer<typeof directionsInput>;
export type NavigationLinkInput = z.infer<typeof navigationLinkInput>;

const CURRENT_LOCATION = /^\s*(my\s+)?(current\s+location|location|position|here|where\s+i\s+am)\s*$/i;

/** True when the caller means "from wherever I am now". */
export function isCurrentLocation(origin: string | undefined): boolean {
  return origin === undefined || origin.trim() === '' || CURRENT_LOCATION.test(origin);
}

const LAT_LNG = /^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$/;

/** Parses "52.37,-1.26". Returns undefined for anything else or out-of-range values. */
export function parseLatLng(value: string): Coordinates | undefined {
  const m = LAT_LNG.exec(value);
  if (!m) return undefined;
  const lat = Number(m[1]);
  const lng = Number(m[2]);
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return undefined;
  return { lat, lng };
}
