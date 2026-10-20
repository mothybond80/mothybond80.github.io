import { timingSafeEqual } from 'node:crypto';
import express, { type NextFunction, type Request, type Response } from 'express';
import { BridgeError } from './errors.js';
import type { Logger } from './logger.js';
import { navigateToG2, type NavigateDeps } from './navigate.js';

export interface AppOptions {
  deps: NavigateDeps;
  logger: Logger;
  /** When set, POST /navigate_to_g2 requires `Authorization: Bearer <token>`. */
  apiToken?: string;
}

function tokenMatches(header: string | undefined, expected: string): boolean {
  const presented = header?.startsWith('Bearer ') ? header.slice(7) : '';
  const a = Buffer.from(presented);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function createApp({ deps, logger, apiToken }: AppOptions) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '16kb' }));

  app.get('/healthz', (_req, res) => {
    res.json({ ok: true, g2_mode: deps.g2.mode });
  });

  app.post('/navigate_to_g2', async (req: Request, res: Response, next: NextFunction) => {
    if (apiToken && !tokenMatches(req.get('authorization'), apiToken)) {
      logger.warn({ ip: req.ip }, 'rejected unauthenticated request');
      res.status(401).json({ status: 'failed', error: { code: 'UNAUTHORIZED', message: 'Missing or invalid bearer token' } });
      return;
    }
    try {
      const result = await navigateToG2(req.body, { ...deps, logger });
      res.status(result.status === 'failed' ? httpStatusFor(result.error?.code) : 200).json(result);
    } catch (err) {
      next(err);
    }
  });

  app.use((_req, res) => {
    res.status(404).json({ status: 'failed', error: { code: 'NOT_FOUND', message: 'Not found' } });
  });

  // Never echoes stacks or raw errors to the client.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof BridgeError) {
      res.status(err.httpStatus).json({ status: 'failed', error: { code: err.code, message: err.message } });
      return;
    }
    const isJsonError = (err as { type?: string })?.type === 'entity.parse.failed';
    if (isJsonError) {
      res.status(400).json({ status: 'failed', error: { code: 'VALIDATION_ERROR', message: 'Body must be valid JSON' } });
      return;
    }
    logger.error({ errName: (err as Error)?.name }, 'unhandled error');
    res.status(500).json({ status: 'failed', error: { code: 'INTERNAL', message: 'Internal error' } });
  });

  return app;
}

function httpStatusFor(code?: string): number {
  switch (code) {
    case 'DESTINATION_NOT_FOUND':
      return 404;
    case 'UPSTREAM_UNAVAILABLE':
      return 503;
    case 'CONFIG_ERROR':
      return 500;
    default:
      return 502;
  }
}
