import { createG2Adapter, type G2AdapterDeps } from './adapters/g2-navigation.adapter.js';
import type { Config } from './config.js';
import { GoogleMapsClient } from './google/google-maps.client.js';
import type { FetchFn } from './http/retry.js';
import type { Logger } from './logger.js';
import type { NavigateDeps } from './navigate.js';
import { parseLatLng } from './schemas.js';

/** Wires config into the Google client and G2 adapter. Tests pass a fake fetch. */
export function buildNavigateDeps(
  config: Config,
  logger: Logger,
  overrides: { fetch?: FetchFn; sleep?: (ms: number) => Promise<void> } & Pick<G2AdapterDeps, 'now' | 'newId'> = {},
): NavigateDeps {
  const retry = {
    maxAttempts: config.RETRY_MAX_ATTEMPTS,
    baseDelayMs: config.RETRY_BASE_DELAY_MS,
    maxDelayMs: config.RETRY_MAX_DELAY_MS,
    timeoutMs: 10000,
  };
  const google = new GoogleMapsClient({
    apiKey: config.GOOGLE_MAPS_API_KEY,
    region: config.GOOGLE_REGION,
    language: config.GOOGLE_LANGUAGE,
    units: config.GOOGLE_UNITS,
    locationBias: config.GOOGLE_LOCATION_BIAS ? parseLatLng(config.GOOGLE_LOCATION_BIAS) : undefined,
    locationBiasRadiusM: config.GOOGLE_LOCATION_BIAS_RADIUS_M,
    retry,
    fetch: overrides.fetch,
    sleep: overrides.sleep,
    logger,
  });
  const g2 = createG2Adapter(config, { ...overrides, logger });
  return { google, g2, logger, defaultOrigin: config.DEFAULT_ORIGIN };
}
