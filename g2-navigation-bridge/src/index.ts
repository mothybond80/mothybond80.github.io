import 'dotenv/config';
import { assertHttpServerConfig, loadConfig } from './config.js';
import { buildNavigateDeps } from './container.js';
import { createLogger } from './logger.js';
import { createApp } from './server.js';

function main() {
  const config = loadConfig();
  assertHttpServerConfig(config);
  const logger = createLogger(config.LOG_LEVEL);
  const deps = buildNavigateDeps(config, logger);

  if (!config.BRIDGE_API_TOKEN) {
    logger.warn('BRIDGE_API_TOKEN is not set: /navigate_to_g2 is open to anything on this machine');
  }
  if (config.G2_MODE === 'mock') {
    logger.warn('G2_MODE=mock: requests are resolved but nothing is sent to G2');
  }

  const app = createApp({ deps, logger, apiToken: config.BRIDGE_API_TOKEN });
  app.listen(config.PORT, config.HOST, () => {
    logger.info({ host: config.HOST, port: config.PORT, g2Mode: config.G2_MODE }, 'g2-navigation-bridge listening');
  });
}

try {
  main();
} catch (err) {
  // Config errors name variables, never values.
  console.error((err as Error).message);
  process.exit(1);
}
