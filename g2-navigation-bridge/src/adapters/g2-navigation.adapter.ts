/**
 * G2 Navigation adapter.
 *
 * Everything G2-specific lives in this file: delivery method, endpoint,
 * authentication, payload shape and deep-link format. Nothing else in the
 * bridge knows how G2 is reached.
 *
 * ┌────────────────────────────────────────────────────────────────────────┐
 * │ STATUS: PROVISIONAL / MOCK                                             │
 * │                                                                        │
 * │ Even Realities does not publish an API, webhook or deep-link scheme    │
 * │ for the G2's built-in Navigation feature (checked Oct 2026 against     │
 * │ hub.evenrealities.com/docs). The only third-party surface is Even Hub  │
 * │ plugins: web apps that run inside the Even app on the phone.           │
 * │                                                                        │
 * │ So:                                                                    │
 * │  - `mock` (default) sends nothing and returns the payload it would     │
 * │    have sent.                                                          │
 * │  - `webhook` POSTs `mapToG2Payload()` to G2_NAVIGATION_API_URL. The    │
 * │    payload shape is OUR proposal, intended for a receiver you control  │
 * │    (an Even Hub plugin backend, or a relay on the Mac mini). Replace   │
 * │    `mapToG2Payload()` if the real receiver expects something else.    │
 * │  - `deep_link` fills G2_DEEP_LINK_TEMPLATE. No real G2 scheme is       │
 * │    known, so there is no default template.                             │
 * │                                                                        │
 * │ See README "Completing the G2 integration" for what is needed.         │
 * └────────────────────────────────────────────────────────────────────────┘
 */
import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import type { Config } from '../config.js';
import { BridgeError } from '../errors.js';
import { fetchWithRetry, type FetchFn } from '../http/retry.js';
import { safeUrl, type Logger } from '../logger.js';
import type { TravelMode } from '../schemas.js';

export type G2Mode = Config['G2_MODE'];

/** Bridge-side description of a navigation target. Input to every adapter. */
export interface G2NavigationTarget {
  name: string;
  address: string | null;
  lat: number;
  lng: number;
  placeId: string | null;
  travelMode: TravelMode;
  distanceMeters: number | null;
  durationSeconds: number | null;
  distanceText: string | null;
  durationText: string | null;
  encodedPolyline: string | null;
  googleMapsLink: string;
  notes?: string;
}

export interface G2DeliveryResult {
  status: 'sent' | 'link_created';
  mode: G2Mode;
  /** Human-readable summary of what G2 said (or what the mock did). Never contains secrets. */
  g2Response: string;
  deepLink: string | null;
  /** The payload that was (or, for mock, would have been) sent. */
  payload: G2NavigationPayload | null;
}

export interface G2NavigationAdapter {
  readonly mode: G2Mode;
  deliver(target: G2NavigationTarget): Promise<G2DeliveryResult>;
}

// ---------------------------------------------------------------------------
// Payload mapping (PROVISIONAL)
// ---------------------------------------------------------------------------

/** G2 display: 576 x 288 px, monochrome. Keep each line short. */
const MAX_DISPLAY_LINE = 32;

export interface G2NavigationPayload {
  type: 'navigation.request';
  version: 1;
  request_id: string;
  requested_at: string;
  destination: {
    name: string;
    address: string | null;
    lat: number;
    lng: number;
    place_id: string | null;
  };
  route: {
    mode: TravelMode;
    distance_m: number | null;
    duration_s: number | null;
    distance_text: string | null;
    duration_text: string | null;
    /** Google encoded polyline (overview quality). */
    polyline: string | null;
  };
  links: { google_maps: string };
  /** Pre-formatted lines a G2 plugin can render as-is. */
  display: { lines: string[] };
  notes: string | null;
}

function truncate(s: string, max: number): string {
  return s.length <= max ? s : `${s.slice(0, max - 1)}…`;
}

/**
 * Bridge target -> G2 payload. PROVISIONAL: this is the one function to
 * change once the real G2 receiver's schema is known.
 */
export function mapToG2Payload(
  target: G2NavigationTarget,
  meta: { requestId: string; now: Date },
): G2NavigationPayload {
  const summary = [target.distanceText, target.durationText].filter(Boolean).join(' · ');
  const lines = [
    truncate(`To: ${target.name}`, MAX_DISPLAY_LINE),
    summary ? truncate(`${summary} (${target.travelMode})`, MAX_DISPLAY_LINE) : truncate(`Mode: ${target.travelMode}`, MAX_DISPLAY_LINE),
  ];
  if (target.notes) lines.push(truncate(target.notes, MAX_DISPLAY_LINE));

  return {
    type: 'navigation.request',
    version: 1,
    request_id: meta.requestId,
    requested_at: meta.now.toISOString(),
    destination: {
      name: target.name,
      address: target.address,
      lat: target.lat,
      lng: target.lng,
      place_id: target.placeId,
    },
    route: {
      mode: target.travelMode,
      distance_m: target.distanceMeters,
      duration_s: target.durationSeconds,
      distance_text: target.distanceText,
      duration_text: target.durationText,
      polyline: target.encodedPolyline,
    },
    links: { google_maps: target.googleMapsLink },
    display: { lines },
    notes: target.notes ?? null,
  };
}

// ---------------------------------------------------------------------------
// Deep link
// ---------------------------------------------------------------------------

const DEEP_LINK_FIELDS: Record<string, (t: G2NavigationTarget) => string> = {
  lat: (t) => String(t.lat),
  lng: (t) => String(t.lng),
  name: (t) => t.name,
  address: (t) => t.address ?? '',
  place_id: (t) => t.placeId ?? '',
  mode: (t) => t.travelMode,
  google_maps_link: (t) => t.googleMapsLink,
};

/** Fills {placeholders} in the template with URL-encoded values. Unknown placeholders are an error. */
export function buildG2DeepLink(template: string, target: G2NavigationTarget): string {
  return template.replace(/\{([a-z_]+)\}/g, (_, key: string) => {
    const get = DEEP_LINK_FIELDS[key];
    if (!get) throw new BridgeError('CONFIG_ERROR', `G2_DEEP_LINK_TEMPLATE has unknown placeholder {${key}}`, 500);
    return encodeURIComponent(get(target));
  });
}

// ---------------------------------------------------------------------------
// Adapters
// ---------------------------------------------------------------------------

export interface G2AdapterDeps {
  fetch?: FetchFn;
  logger?: Logger;
  sleep?: (ms: number) => Promise<void>;
  now?: () => Date;
  newId?: () => string;
}

/** MOCK: sends nothing. Returns the payload so it can be inspected. */
export class MockG2Adapter implements G2NavigationAdapter {
  readonly mode = 'mock' as const;
  constructor(private readonly deps: G2AdapterDeps = {}) {}

  async deliver(target: G2NavigationTarget): Promise<G2DeliveryResult> {
    const payload = mapToG2Payload(target, {
      requestId: (this.deps.newId ?? randomUUID)(),
      now: (this.deps.now ?? (() => new Date()))(),
    });
    this.deps.logger?.info({ g2Mode: 'mock', requestId: payload.request_id }, 'G2 mock adapter: payload built, not sent');
    return {
      status: 'link_created',
      mode: 'mock',
      g2Response:
        '[MOCK] G2 Navigation is not connected, so nothing was sent to the glasses. ' +
        'Open google_maps_link on your phone. Set G2_MODE=webhook or deep_link once a G2 target exists.',
      deepLink: null,
      payload,
    };
  }
}

export class DeepLinkG2Adapter implements G2NavigationAdapter {
  readonly mode = 'deep_link' as const;
  constructor(private readonly template: string) {}

  async deliver(target: G2NavigationTarget): Promise<G2DeliveryResult> {
    const deepLink = buildG2DeepLink(this.template, target);
    return {
      status: 'link_created',
      mode: 'deep_link',
      g2Response: 'Deep link created. Open it on the phone paired with the G2.',
      deepLink,
      payload: null,
    };
  }
}

/** Accepts any JSON object or text; anything beyond 500 chars is cut. */
const webhookResponseSchema = z.union([z.record(z.string(), z.unknown()), z.array(z.unknown())]);

export class WebhookG2Adapter implements G2NavigationAdapter {
  readonly mode = 'webhook' as const;

  constructor(
    private readonly opts: {
      url: string;
      token?: string;
      timeoutMs: number;
      retry: { maxAttempts: number; baseDelayMs: number; maxDelayMs: number };
    },
    private readonly deps: G2AdapterDeps = {},
  ) {}

  async deliver(target: G2NavigationTarget): Promise<G2DeliveryResult> {
    const requestId = (this.deps.newId ?? randomUUID)();
    const payload = mapToG2Payload(target, { requestId, now: (this.deps.now ?? (() => new Date()))() });

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/plain;q=0.9',
      // Same key on every retry so the receiver can de-duplicate.
      'Idempotency-Key': requestId,
    };
    if (this.opts.token) headers.Authorization = `Bearer ${this.opts.token}`;

    const res = await fetchWithRetry(
      this.opts.url,
      { method: 'POST', headers, body: JSON.stringify(payload) },
      {
        label: 'G2 Navigation',
        ...this.opts.retry,
        timeoutMs: this.opts.timeoutMs,
        fetch: this.deps.fetch,
        logger: this.deps.logger,
        sleep: this.deps.sleep,
      },
    );

    const text = await res.text().catch(() => '');
    if (!res.ok) {
      this.deps.logger?.error({ upstream: 'G2 Navigation', target: safeUrl(this.opts.url), status: res.status, requestId }, 'G2 rejected request');
      const hint = res.status === 401 || res.status === 403 ? ' (check G2_NAVIGATION_API_TOKEN)' : '';
      throw new BridgeError('G2_DELIVERY_FAILED', `G2 Navigation returned status ${res.status}${hint}`, 502, {
        status: res.status,
      });
    }

    this.deps.logger?.info({ upstream: 'G2 Navigation', status: res.status, requestId }, 'G2 accepted request');
    return {
      status: 'sent',
      mode: 'webhook',
      g2Response: summariseWebhookBody(text, res.status),
      deepLink: null,
      payload,
    };
  }
}

function summariseWebhookBody(text: string, status: number): string {
  if (!text.trim()) return `HTTP ${status}`;
  let body: string = text;
  try {
    const parsed = webhookResponseSchema.safeParse(JSON.parse(text));
    if (parsed.success) body = JSON.stringify(parsed.data);
  } catch {
    // Not JSON: keep text.
  }
  return truncate(body, 500);
}

export function createG2Adapter(config: Config, deps: G2AdapterDeps = {}): G2NavigationAdapter {
  switch (config.G2_MODE) {
    case 'webhook':
      return new WebhookG2Adapter(
        {
          url: config.G2_NAVIGATION_API_URL!,
          token: config.G2_NAVIGATION_API_TOKEN,
          timeoutMs: config.G2_REQUEST_TIMEOUT_MS,
          retry: {
            maxAttempts: config.RETRY_MAX_ATTEMPTS,
            baseDelayMs: config.RETRY_BASE_DELAY_MS,
            maxDelayMs: config.RETRY_MAX_DELAY_MS,
          },
        },
        deps,
      );
    case 'deep_link':
      return new DeepLinkG2Adapter(config.G2_DEEP_LINK_TEMPLATE!);
    case 'mock':
    default:
      return new MockG2Adapter(deps);
  }
}
