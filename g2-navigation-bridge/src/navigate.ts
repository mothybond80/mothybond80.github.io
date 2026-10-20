import type { G2NavigationAdapter, G2NavigationPayload, G2NavigationTarget } from './adapters/g2-navigation.adapter.js';
import { BridgeError } from './errors.js';
import { GoogleMapsClient } from './google/google-maps.client.js';
import { buildGoogleMapsLink, type ResolvedPlace, type RouteSummary } from './google/normalise.js';
import type { Logger } from './logger.js';
import {
  isCurrentLocation,
  navigateInputSchema,
  type NavigateInput,
  type NavigateResult,
} from './schemas.js';

export interface NavigateDeps {
  google: Pick<GoogleMapsClient, 'resolveDestination' | 'computeRoute'>;
  g2: G2NavigationAdapter;
  logger?: Logger;
  /** Used when the caller gave no origin or said "current location". */
  defaultOrigin?: string;
}

export type NavigateOutcome = NavigateResult & { g2_payload?: G2NavigationPayload };

/**
 * The `navigate_to_g2` flow:
 *   validate input -> resolve destination -> route (if we know the origin)
 *   -> build Google Maps link -> hand to G2 adapter -> clear result.
 *
 * Never throws for expected failures; returns status "failed" with a
 * client-safe error. Validation errors do throw (BridgeError 400) so the
 * HTTP layer can answer 400.
 */
export async function navigateToG2(rawInput: unknown, deps: NavigateDeps): Promise<NavigateOutcome> {
  const parsed = navigateInputSchema.safeParse(rawInput);
  if (!parsed.success) {
    const issues = parsed.error.issues.map((i) => `${i.path.join('.') || 'input'}: ${i.message}`);
    throw new BridgeError('VALIDATION_ERROR', `Invalid request: ${issues.join('; ')}`, 400, { issues });
  }
  const input = parsed.data;
  const log = deps.logger;
  const warnings: string[] = [];

  let place: ResolvedPlace | undefined;
  let route: RouteSummary | null = null;
  let googleMapsLink: string | null = null;
  const origin = resolveOrigin(input, deps.defaultOrigin);

  try {
    place = await deps.google.resolveDestination(input.destination);
    log?.info({ source: place.source, hasPlaceId: Boolean(place.placeId) }, 'destination resolved');

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
        'No origin known for "current location", so distance and duration were not calculated. ' +
          'The Google Maps link will start from your phone\'s live location. Pass origin as "lat,lng" or set DEFAULT_ORIGIN to get them.',
      );
    }
    if ((input.avoid_tolls || input.avoid_highways) && input.travel_mode !== 'driving') {
      warnings.push('avoid_tolls / avoid_highways only apply to driving and were ignored.');
    }

    // When origin is "current location" it is left out of the link on purpose.
    googleMapsLink = buildGoogleMapsLink(place, input.travel_mode, isCurrentLocation(input.origin) ? undefined : origin);

    const target: G2NavigationTarget = {
      name: place.name,
      address: place.address,
      lat: place.coordinates.lat,
      lng: place.coordinates.lng,
      placeId: place.placeId,
      travelMode: input.travel_mode,
      distanceMeters: route?.distanceMeters ?? null,
      durationSeconds: route?.durationSeconds ?? null,
      distanceText: route?.distanceText ?? null,
      durationText: route?.durationText ?? null,
      encodedPolyline: route?.encodedPolyline ?? null,
      googleMapsLink,
      notes: input.notes,
    };

    const delivery = await deps.g2.deliver(target);
    log?.info({ g2Mode: delivery.mode, status: delivery.status }, 'navigate_to_g2 complete');

    return {
      ...baseResult(input, place, route, googleMapsLink, origin, deps.g2.mode, warnings),
      status: delivery.status,
      g2_response: delivery.g2Response,
      g2_deep_link: delivery.deepLink,
      ...(delivery.mode === 'mock' && delivery.payload ? { g2_payload: delivery.payload } : {}),
    };
  } catch (err) {
    const safe =
      err instanceof BridgeError ? err : new BridgeError('GOOGLE_API_ERROR', 'Unexpected error while navigating', 500);
    log?.error({ code: safe.code, httpStatus: safe.httpStatus, errName: (err as Error)?.name }, 'navigate_to_g2 failed');
    return {
      ...baseResult(input, place, route, googleMapsLink, origin, deps.g2.mode, warnings),
      status: 'failed',
      g2_response: null,
      g2_deep_link: null,
      error: { code: safe.code, message: safe.message },
    };
  }
}

function resolveOrigin(input: NavigateInput, defaultOrigin?: string): string | undefined {
  return isCurrentLocation(input.origin) ? defaultOrigin : input.origin;
}

function baseResult(
  input: NavigateInput,
  place: ResolvedPlace | undefined,
  route: RouteSummary | null,
  googleMapsLink: string | null,
  origin: string | undefined,
  g2Mode: G2NavigationAdapter['mode'],
  warnings: string[],
): Omit<NavigateResult, 'status' | 'g2_response' | 'g2_deep_link'> {
  return {
    destination: place?.name ?? input.destination,
    coordinates: place ? place.coordinates : null,
    distance_text: route?.distanceText ?? null,
    duration_text: route?.durationText ?? null,
    google_maps_link: googleMapsLink,
    address: place?.address ?? null,
    place_id: place?.placeId ?? null,
    travel_mode: input.travel_mode,
    origin_used: origin ?? (isCurrentLocation(input.origin) ? 'current location (device)' : null),
    distance_meters: route?.distanceMeters ?? null,
    duration_seconds: route?.durationSeconds ?? null,
    polyline: route?.encodedPolyline ?? null,
    g2_mode: g2Mode,
    ...(warnings.length ? { warnings } : {}),
  };
}
