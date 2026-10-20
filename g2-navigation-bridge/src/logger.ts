import pino, { type DestinationStream, type Logger } from 'pino';

/**
 * Any of these keys, at the top level or one/two levels deep, is replaced
 * with "[REDACTED]". The code also avoids logging headers, URLs with query
 * strings and upstream bodies in the first place; this is the safety net.
 */
export const REDACT_PATHS = [
  'headers',
  'authorization',
  'Authorization',
  'apiKey',
  'api_key',
  'key',
  'token',
  'accessToken',
  'password',
  'secret',
  'GOOGLE_MAPS_API_KEY',
  'G2_NAVIGATION_API_TOKEN',
  'BRIDGE_API_TOKEN',
  'X-Goog-Api-Key',
  'x-goog-api-key',
].flatMap((k) => [k, `*.${k}`, `*.*.${k}`]);

export type { Logger };

/**
 * @param destination pino destination. The MCP stdio server MUST pass
 *   pino.destination(2) so logs go to stderr and never corrupt the protocol
 *   stream on stdout.
 */
export function createLogger(level = 'info', destination?: DestinationStream): Logger {
  return pino(
    {
      name: 'g2-navigation-bridge',
      level,
      redact: { paths: REDACT_PATHS, censor: '[REDACTED]' },
      base: undefined,
    },
    destination,
  );
}

/** Host + path only: strips query strings, which can carry `key=`. */
export function safeUrl(raw: string): string {
  try {
    const u = new URL(raw);
    return `${u.protocol}//${u.host}${u.pathname}`;
  } catch {
    return '[invalid-url]';
  }
}
