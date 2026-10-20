import { z } from 'zod';

export const TRAVEL_MODES = ['driving', 'walking', 'cycling', 'transit'] as const;
export type TravelMode = (typeof TRAVEL_MODES)[number];

/** Input to the `navigate_to_g2` tool / endpoint. Kept as a raw shape so MCP can reuse it. */
export const navigateInputShape = {
  destination: z
    .string()
    .trim()
    .min(1, 'destination is required')
    .max(300, 'destination is too long')
    .describe('Place name, business name or address, e.g. "Tim Bond Dental, Rugby"'),
  origin: z
    .string()
    .trim()
    .max(300, 'origin is too long')
    .optional()
    .describe('Start address or "lat,lng". Omit, or say "current location", to start from where you are.'),
  travel_mode: z.enum(TRAVEL_MODES).default('driving'),
  avoid_tolls: z.boolean().default(false),
  avoid_highways: z.boolean().default(false),
  notes: z.string().trim().max(500, 'notes is too long').optional(),
};

export const navigateInputSchema = z.object(navigateInputShape).strict();

export type NavigateInput = z.infer<typeof navigateInputSchema>;
/** What callers may send (defaults not yet applied). */
export type NavigateInputRaw = z.input<typeof navigateInputSchema>;

export interface Coordinates {
  lat: number;
  lng: number;
}

export interface NavigateResult {
  status: 'sent' | 'link_created' | 'failed';
  destination: string | null;
  coordinates: Coordinates | null;
  distance_text: string | null;
  duration_text: string | null;
  g2_response: string | null;
  g2_deep_link: string | null;
  google_maps_link: string | null;
  // Extras beyond the minimum contract, useful to callers and for debugging.
  address?: string | null;
  place_id?: string | null;
  travel_mode?: TravelMode;
  origin_used?: string | null;
  distance_meters?: number | null;
  duration_seconds?: number | null;
  polyline?: string | null;
  g2_mode?: 'mock' | 'webhook' | 'deep_link';
  warnings?: string[];
  error?: { code: string; message: string };
}

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
