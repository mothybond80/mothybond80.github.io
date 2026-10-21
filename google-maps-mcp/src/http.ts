/**
 * MCP over Streamable HTTP, for claude.ai connectors (via the Mac mini gateway)
 * and any other remote MCP client.
 *
 * Stateless: every POST gets a fresh server + transport, so there is no session
 * table to leak and the gateway can restart us freely.
 */
import { timingSafeEqual } from 'node:crypto';
import { config as loadDotenv } from 'dotenv';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import express, { type NextFunction, type Request, type Response } from 'express';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { assertHttpServerConfig, loadConfig } from './config.js';
import { createLogger, type Logger } from './logger.js';
import { createMcpServer, SERVER_INFO, type ToolDeps, buildToolDeps } from './tools.js';

export interface HttpAppOptions {
  deps: ToolDeps;
  logger: Logger;
  /** When set, every MCP request must carry `Authorization: Bearer <token>`. */
  authToken?: string;
}

function tokenMatches(header: string | undefined, expected: string): boolean {
  const presented = header?.startsWith('Bearer ') ? header.slice(7) : '';
  const a = Buffer.from(presented);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function createHttpApp({ deps, logger, authToken }: HttpAppOptions) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '64kb' }));

  app.get('/healthz', (_req, res) => {
    res.json({ ok: true, server: SERVER_INFO.name, version: SERVER_INFO.version });
  });

  const requireAuth = (req: Request, res: Response, next: NextFunction) => {
    if (authToken && !tokenMatches(req.get('authorization'), authToken)) {
      logger.warn({ ip: req.ip, path: req.path }, 'rejected unauthenticated MCP request');
      res.status(401).json({
        jsonrpc: '2.0',
        error: { code: -32001, message: 'Unauthorized' },
        id: null,
      });
      return;
    }
    next();
  };

  // Served at /mcp and at / so the gateway can strip or keep the prefix.
  for (const path of ['/mcp', '/']) {
    app.post(path, requireAuth, async (req, res) => {
      const server = createMcpServer(deps);
      const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      res.on('close', () => {
        transport.close().catch(() => undefined);
        server.close().catch(() => undefined);
      });
      try {
        await server.connect(transport);
        await transport.handleRequest(req, res, req.body);
      } catch (err) {
        logger.error({ errName: (err as Error)?.name }, 'MCP request failed');
        if (!res.headersSent) {
          res.status(500).json({ jsonrpc: '2.0', error: { code: -32603, message: 'Internal error' }, id: null });
        }
      }
    });

    // Stateless servers have no SSE stream to resume and no session to delete.
    app.get(path, requireAuth, (_req, res) => {
      res.status(405).json({ jsonrpc: '2.0', error: { code: -32000, message: 'Method not allowed' }, id: null });
    });
    app.delete(path, requireAuth, (_req, res) => {
      res.status(405).json({ jsonrpc: '2.0', error: { code: -32000, message: 'Method not allowed' }, id: null });
    });
  }

  // Never echoes stacks or raw errors to the client.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const isJsonError = (err as { type?: string })?.type === 'entity.parse.failed';
    if (isJsonError) {
      res.status(400).json({ jsonrpc: '2.0', error: { code: -32700, message: 'Parse error' }, id: null });
      return;
    }
    logger.error({ errName: (err as Error)?.name }, 'unhandled error');
    res.status(500).json({ jsonrpc: '2.0', error: { code: -32603, message: 'Internal error' }, id: null });
  });

  return app;
}

function main() {
  const here = dirname(fileURLToPath(import.meta.url));
  loadDotenv({ path: resolve(here, '..', '.env'), quiet: true });

  const config = loadConfig();
  assertHttpServerConfig(config);
  const logger = createLogger(config.LOG_LEVEL);
  const deps = buildToolDeps(config, logger);

  if (!config.MCP_AUTH_TOKEN) {
    logger.warn('MCP_AUTH_TOKEN is not set: anything that can reach this port can use the Google key');
  }

  const app = createHttpApp({ deps, logger, authToken: config.MCP_AUTH_TOKEN });
  app.listen(config.PORT, config.HOST, () => {
    logger.info({ host: config.HOST, port: config.PORT }, 'google-maps-mcp listening (Streamable HTTP)');
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (err) {
    // Config errors name variables, never values.
    console.error((err as Error).message);
    process.exit(1);
  }
}
