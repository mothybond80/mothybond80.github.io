import { z } from 'zod';
import { BridgeError } from './errors.js';

const optionalString = z
  .string()
  .optional()
  .transform((v) => (v && v.trim() !== '' ? v.trim() : undefined));

const latLngString = optionalString.refine(
  (v) => v === undefined || /^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$/.test(v),
  'must be "lat,lng"',
);

const intWithDefault = (def: number, min: number, max: number) =>
  z.coerce.number().int().min(min).max(max).default(def);

export const configSchema = z.object({
  GOOGLE_MAPS_API_KEY: z.string().trim().min(1, 'GOOGLE_MAPS_API_KEY is required'),
  GOOGLE_REGION: z.string().trim().default('uk'),
  GOOGLE_LANGUAGE: z.string().trim().default('en-GB'),
  GOOGLE_UNITS: z.enum(['IMPERIAL', 'METRIC']).default('IMPERIAL'),
  GOOGLE_LOCATION_BIAS: latLngString,
  GOOGLE_LOCATION_BIAS_RADIUS_M: intWithDefault(30000, 1, 50000),
  DEFAULT_ORIGIN: optionalString,

  HOST: z.string().trim().default('127.0.0.1'),
  PORT: intWithDefault(3460, 1, 65535),
  MCP_AUTH_TOKEN: optionalString,

  RETRY_MAX_ATTEMPTS: intWithDefault(4, 1, 10),
  RETRY_BASE_DELAY_MS: intWithDefault(300, 1, 10000),
  RETRY_MAX_DELAY_MS: intWithDefault(5000, 1, 60000),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent']).default('info'),
});

export type Config = z.infer<typeof configSchema>;

export function isLoopbackHost(host: string): boolean {
  const h = host.replace(/^\[|\]$/g, '').toLowerCase();
  return h === 'localhost' || h === '::1' || /^127\.\d+\.\d+\.\d+$/.test(h);
}

/**
 * Parse and validate configuration. Error messages name the offending
 * variable but never echo its value, so secrets cannot leak through a
 * startup failure.
 */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const parsed = configSchema.safeParse(env);
  if (!parsed.success) {
    const problems = parsed.error.issues.map((i) => `${i.path.join('.') || 'config'}: ${i.message}`);
    throw new BridgeError('CONFIG_ERROR', `Invalid configuration:\n  ${problems.join('\n  ')}`, 500);
  }
  return parsed.data;
}

/** Extra checks that only apply when the HTTP transport is exposed. */
export function assertHttpServerConfig(config: Config): void {
  if (!isLoopbackHost(config.HOST) && !config.MCP_AUTH_TOKEN) {
    throw new BridgeError(
      'CONFIG_ERROR',
      `MCP_AUTH_TOKEN is required when HOST (${config.HOST}) is not a loopback address`,
      500,
    );
  }
}
