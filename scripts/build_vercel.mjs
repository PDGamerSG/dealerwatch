// Vercel serves the landing page at /, the reviewer console at /app and proxies
// API/audio requests to the durable AWS backend.
import { copyFileSync, cpSync, existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

let backend;
try {
  backend = new URL(process.env.DW_BACKEND_URL || '');
  if (backend.protocol !== 'https:' || backend.username || backend.password || backend.search || backend.hash
      || backend.pathname !== '/') throw new Error('Invalid backend origin');
} catch {
  console.error('DW_BACKEND_URL must be an HTTPS backend origin without credentials, query, fragment or path.');
  process.exit(1);
}

// The landing page (landing/) is a Vite app built with a relative base, so its
// dist/ can sit at the site root. A prebuilt dist/ is reused; otherwise it is
// built here with dev dependencies, because Vercel sets NODE_ENV=production.
const landingDist = join('landing', 'dist');
if (!existsSync(join(landingDist, 'index.html'))) {
  if (!existsSync(join('landing', 'package.json'))) {
    console.error('landing/ is missing; the site root needs the landing page build.');
    process.exit(1);
  }
  for (const args of [['ci', '--include=dev', '--prefix', 'landing'], ['run', 'build', '--prefix', 'landing']]) {
    const result = spawnSync('npm', args, { stdio: 'inherit' });
    if (result.status !== 0) {
      console.error(`npm ${args.join(' ')} failed`);
      process.exit(1);
    }
  }
}

const output = join(process.cwd(), '.vercel', 'output');
rmSync(output, { recursive: true, force: true });
mkdirSync(join(output, 'static', 'static'), { recursive: true });
mkdirSync(join(output, 'static', 'app'), { recursive: true });
cpSync(landingDist, join(output, 'static'), { recursive: true });
copyFileSync('dealerwatch/web/index.html', join(output, 'static/app/index.html'));
for (const name of ['app.js', 'style.css']) {
  copyFileSync(join('dealerwatch/web', name), join(output, 'static/static', name));
}
// Self-hosted fonts referenced from style.css; the CSP allows same-origin fonts only.
if (existsSync('dealerwatch/web/fonts')) {
  cpSync('dealerwatch/web/fonts', join(output, 'static/static/fonts'), { recursive: true });
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
    { src: '^/app/?$', dest: '/app/index.html' },
  ],
};
writeFileSync(join(output, 'config.json'), JSON.stringify(config, null, 2) + '\n');
console.info('Built DealerWatch landing page, reviewer console and API/audio proxy routes.');
