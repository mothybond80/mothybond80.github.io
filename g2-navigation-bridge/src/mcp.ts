/**
 * MCP stdio server exposing one tool: navigate_to_g2.
 *
 * stdout carries the MCP protocol, so all logging goes to stderr.
 */
import { config as loadDotenv } from 'dotenv';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import pino from 'pino';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadConfig } from './config.js';
import { buildNavigateDeps } from './container.js';
import { BridgeError } from './errors.js';
import { createLogger } from './logger.js';
import { navigateToG2, type NavigateDeps } from './navigate.js';
import { navigateInputShape } from './schemas.js';

export const TOOL_DESCRIPTION =
  'Resolve a destination with Google Maps and send it to the Even Realities G2 glasses for navigation. ' +
  'Returns coordinates, distance, duration, a Google Maps link and the G2 delivery status. ' +
  'Leave origin out (or say "current location") to start from where the user is.';

export function createMcpServer(deps: NavigateDeps): McpServer {
  const server = new McpServer({ name: 'g2-navigation-bridge', version: '0.1.0' });

  server.registerTool(
    'navigate_to_g2',
    { title: 'Navigate to G2', description: TOOL_DESCRIPTION, inputSchema: navigateInputShape },
    async (args) => {
      try {
        const result = await navigateToG2(args, deps);
        return {
          content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }],
          structuredContent: result as unknown as Record<string, unknown>,
          isError: result.status === 'failed',
        };
      } catch (err) {
        const message = err instanceof BridgeError ? err.message : 'Internal error';
        return { content: [{ type: 'text' as const, text: message }], isError: true };
      }
    },
  );

  return server;
}

async function main() {
  // Claude Code may start us from any cwd; load .env from the project root.
  const here = dirname(fileURLToPath(import.meta.url));
  loadDotenv({ path: resolve(here, '..', '.env'), quiet: true });

  const config = loadConfig();
  const logger = createLogger(config.LOG_LEVEL, pino.destination(2));
  const server = createMcpServer(buildNavigateDeps(config, logger));
  await server.connect(new StdioServerTransport());
  logger.info({ g2Mode: config.G2_MODE }, 'navigate_to_g2 MCP server ready on stdio');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((err) => {
    process.stderr.write(`${(err as Error).message}\n`);
    process.exit(1);
  });
}
