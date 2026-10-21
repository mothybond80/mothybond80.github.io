/**
 * The four tools, registered on an McpServer. Transport-agnostic: both the
 * stdio entry point and the Streamable HTTP entry point call registerTools().
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type { Config } from './config.js';
import { BridgeError } from './errors.js';
import { GoogleMapsClient } from './google/google-maps.client.js';
import { buildGoogleMapsLink, type ResolvedPlace, type RouteSummary } from './google/normalise.js';
import type { FetchFn } from './http/retry.js';
import type { Logger } from './logger.js';
import {
  directionsInput,
  directionsShape,
  findPlaceInput,
  findPlaceShape,
  geocodeInput,
  geocodeShape,
  isCurrentLocation,
  navigationLinkInput,
  navigationLinkShape,
  parseLatLng,
  type DirectionsInput,
  type FindPlaceInput,
  type GeocodeInput,
  type NavigationLinkInput,
} from './schemas.js';

export interface ToolDeps {
  google: Pick<GoogleMapsClient, 'resolveDestination' | 'searchPlaces' | 'geocode' | 'computeRoute'>;
  logger?: Logger;
  /** Used when the caller gave no origin or said "current location". */
  defaultOrigin?: string;
}

export const SERVER_INFO = { name: 'google-maps-mcp', version: '0.2.0' };

/** Wires config into a Google client. Tests pass a fake fetch. */
export function buildToolDeps(
  config: Config,
  logger: Logger,
  overrides: { fetch?: FetchFn; sleep?: (ms: number) => Promise<void> } = {},
): ToolDeps {
  const google = new GoogleMapsClient({
    apiKey: config.GOOGLE_MAPS_API_KEY,
    region: config.GOOGLE_REGION,
    language: config.GOOGLE_LANGUAGE,
    units: config.GOOGLE_UNITS,
    locationBias: config.GOOGLE_LOCATION_BIAS ? parseLatLng(config.GOOGLE_LOCATION_BIAS) : undefined,
    locationBiasRadiusM: config.GOOGLE_LOCATION_BIAS_RADIUS_M,
    retry: {
      maxAttempts: config.RETRY_MAX_ATTEMPTS,
      baseDelayMs: config.RETRY_BASE_DELAY_MS,
      maxDelayMs: config.RETRY_MAX_DELAY_MS,
      timeoutMs: 10000,
    },
    fetch: overrides.fetch,
    sleep: overrides.sleep,
    logger,
  });
  return { google, logger, defaultOrigin: config.DEFAULT_ORIGIN };
}

// ---------------------------------------------------------------------------
// Tool implementations (pure functions, easy to test)
// ---------------------------------------------------------------------------

export interface PlaceResult {
  name: string;
  address: string | null;
  coordinates: { lat: number; lng: number };
  place_id: string | null;
  type?: string | null;
  rating?: number | null;
  rating_count?: number | null;
  phone?: string | null;
  website?: string | null;
  open_now?: boolean | null;
  google_maps_link: string;
}

function toPlaceResult(p: ResolvedPlace): PlaceResult {
  return {
    name: p.name,
    address: p.address,
    coordinates: p.coordinates,
    place_id: p.placeId,
    ...(p.source === 'places'
      ? {
          type: p.type ?? null,
          rating: p.rating ?? null,
          rating_count: p.ratingCount ?? null,
          phone: p.phone ?? null,
          website: p.website ?? null,
          open_now: p.openNow ?? null,
        }
      : {}),
    google_maps_link: p.googleMapsLink ?? buildGoogleMapsLink(p, 'driving'),
  };
}

export async function findPlace(input: FindPlaceInput, deps: ToolDeps) {
  const near = input.near ? parseLatLng(input.near) : undefined;
  if (input.near && !near) {
    throw new BridgeError('VALIDATION_ERROR', 'near must be "lat,lng"', 400);
  }
  const places = await deps.google.searchPlaces(input.query, { maxResults: input.max_results, near });
  return { query: input.query, results: places.map(toPlaceResult) };
}

export async function geocode(input: GeocodeInput, deps: ToolDeps) {
  const place = await deps.google.geocode(input.address);
  if (!place) throw new BridgeError('DESTINATION_NOT_FOUND', `Could not geocode "${input.address}"`, 404);
  return {
    query: input.address,
    address: place.address,
    coordinates: place.coordinates,
    place_id: place.placeId,
    google_maps_link: `https://www.google.com/maps/search/?api=1&query=${place.coordinates.lat}%2C${place.coordinates.lng}`,
  };
}

export async function getDirections(input: DirectionsInput, deps: ToolDeps) {
  const origin = isCurrentLocation(input.origin) ? deps.defaultOrigin : input.origin;
  const place = await deps.google.resolveDestination(input.destination);
  const warnings: string[] = [];

  let route: RouteSummary | null = null;
  if (origin) {
    route = await deps.google.computeRoute({
      origin,
      destination: place,
      travelMode: input.travel_mode,
      avoidTolls: input.avoid_tolls,
      avoidHighways: input.avoid_highways,
    });
    if (!route) warnings.push(`Google found no ${input.travel_mode} route from the origin.`);
  } else {
    warnings.push(
      'No origin given and DEFAULT_ORIGIN is not set, so distance and duration were not calculated. ' +
        'The Google Maps link will start from the phone\'s live location.',
    );
  }
  if ((input.avoid_tolls || input.avoid_highways) && input.travel_mode !== 'driving') {
    warnings.push('avoid_tolls / avoid_highways only apply to driving and were ignored.');
  }

  return {
    destination: toPlaceResult(place),
    origin_used: origin ?? 'current location (device)',
    travel_mode: input.travel_mode,
    distance_text: route?.distanceText ?? null,
    duration_text: route?.durationText ?? null,
    distance_meters: route?.distanceMeters ?? null,
    duration_seconds: route?.durationSeconds ?? null,
    ...(input.include_polyline ? { polyline: route?.encodedPolyline ?? null } : {}),
    // When origin is "current location" it is left out of the link on purpose.
    google_maps_link: buildGoogleMapsLink(place, input.travel_mode, isCurrentLocation(input.origin) ? undefined : origin),
    ...(warnings.length ? { warnings } : {}),
  };
}

/** No Google API call: just a Maps URL the phone can open. */
export function navigationLink(input: NavigationLinkInput, deps: ToolDeps) {
  const origin = isCurrentLocation(input.origin) ? undefined : input.origin;
  void deps;
  return {
    destination: input.destination,
    origin_used: origin ?? 'current location (device)',
    travel_mode: input.travel_mode,
    google_maps_link: buildGoogleMapsLink(input.destination, input.travel_mode, origin),
  };
}

// ---------------------------------------------------------------------------
// MCP registration
// ---------------------------------------------------------------------------

function ok(result: unknown): CallToolResult {
  return {
    content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
    structuredContent: result as Record<string, unknown>,
  };
}

function fail(err: unknown, logger?: Logger): CallToolResult {
  const safe = err instanceof BridgeError ? err : new BridgeError('GOOGLE_API_ERROR', 'Unexpected error', 500);
  logger?.error({ code: safe.code, errName: (err as Error)?.name }, 'tool call failed');
  return {
    content: [{ type: 'text', text: `${safe.code}: ${safe.message}` }],
    structuredContent: { error: { code: safe.code, message: safe.message } },
    isError: true,
  };
}

export function createMcpServer(deps: ToolDeps): McpServer {
  const server = new McpServer(SERVER_INFO);
  registerTools(server, deps);
  return server;
}

export function registerTools(server: McpServer, deps: ToolDeps): void {
  const run = async (fn: () => Promise<unknown> | unknown) => {
    try {
      return ok(await fn());
    } catch (err) {
      return fail(err, deps.logger);
    }
  };

  server.registerTool(
    'find_place',
    {
      title: 'Find a place',
      description:
        'Search Google Maps for a business, landmark or address. Returns name, address, coordinates, place ID, ' +
        'rating, phone, website, whether it is open now, and a Google Maps link. Results are biased to the configured area.',
      inputSchema: findPlaceShape,
    },
    (args) => run(() => findPlace(findPlaceInput.parse(args), deps)),
  );

  server.registerTool(
    'geocode',
    {
      title: 'Geocode an address',
      description: 'Turn a postal address or postcode into coordinates, or "lat,lng" into an address.',
      inputSchema: geocodeShape,
    },
    (args) => run(() => geocode(geocodeInput.parse(args), deps)),
  );

  server.registerTool(
    'get_directions',
    {
      title: 'Get directions',
      description:
        'Distance and travel time from an origin to a destination by driving, walking, cycling or transit, ' +
        'plus a Google Maps link that opens turn-by-turn navigation on the phone. ' +
        'Omit origin (or say "current location") to use the configured default origin; the link then starts from the phone\'s live location.',
      inputSchema: directionsShape,
    },
    (args) => run(() => getDirections(directionsInput.parse(args), deps)),
  );

  server.registerTool(
    'navigation_link',
    {
      title: 'Navigation link',
      description:
        'Build a Google Maps directions link to a destination without calling the Google API. ' +
        'Opening it on the phone starts navigation from the current location.',
      inputSchema: navigationLinkShape,
    },
    (args) => run(() => navigationLink(navigationLinkInput.parse(args), deps)),
  );
}
