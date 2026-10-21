/**
 * MCP stdio server, for Claude Code / Claude Desktop.
 *
 * stdout carries the MCP protocol, so all logging goes to stderr.
 */
import { config as loadDotenv } from 'dotenv';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import pino from 'pino';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadConfig } from './config.js';
import { createLogger } from './logger.js';
import { buildToolDeps, createMcpServer } from './tools.js';

async function main() {
  // Claude Code may start us from any cwd; load .env from the project root.
  const here = dirname(fileURLToPath(import.meta.url));
  loadDotenv({ path: resolve(here, '..', '.env'), quiet: true });

  const config = loadConfig();
  const logger = createLogger(config.LOG_LEVEL, pino.destination(2));
  const server = createMcpServer(buildToolDeps(config, logger));
  await server.connect(new StdioServerTransport());
  logger.info('google-maps-mcp ready on stdio');
}

main().catch((err) => {
  process.stderr.write(`${(err as Error).message}\n`);
  process.exit(1);
});
