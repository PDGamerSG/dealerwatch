// Vercel serves the basic UI and proxies API/audio to the durable AWS backend.
import { copyFileSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

let backend;
try {
  backend = new URL(process.env.DW_BACKEND_URL || '');
  if (backend.protocol !== 'https:' || backend.username || backend.password || backend.search || backend.hash
      || backend.pathname !== '/') throw new Error('Invalid backend origin');
} catch {
  console.error('DW_BACKEND_URL must be an HTTPS backend origin without credentials, query, fragment or path.');
  process.exit(1);
}

const output = join(process.cwd(), '.vercel', 'output');
rmSync(output, { recursive: true, force: true });
mkdirSync(join(output, 'static', 'static'), { recursive: true });
copyFileSync('dealerwatch/web/index.html', join(output, 'static/index.html'));
for (const name of ['app.js', 'style.css']) {
  copyFileSync(join('dealerwatch/web', name), join(output, 'static/static', name));
}
const config = {
  version: 3,
  routes: [
    {
      src: '/(.*)', continue: true,
      headers: {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'no-referrer',
        'Cache-Control': 'no-store',
        'CDN-Cache-Control': 'no-store',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
      },
    },
    { src: '^/api/(.*)$', dest: `${backend.origin}/api/$1` },
    { src: '^/audio/(.*)$', dest: `${backend.origin}/audio/$1` },
    { handle: 'filesystem' },
    { src: '^/$', dest: '/index.html' },
  ],
};
writeFileSync(join(output, 'config.json'), JSON.stringify(config, null, 2) + '\n');
console.info('Built DealerWatch static frontend with API/audio proxy routes.');
