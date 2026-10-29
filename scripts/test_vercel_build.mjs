import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const script = fileURLToPath(new URL('./build_vercel.mjs', import.meta.url));

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'dealerwatch-vercel-'));
  mkdirSync(join(root, 'dealerwatch/web'), { recursive: true });
  writeFileSync(join(root, 'dealerwatch/web/index.html'), '<script src="/static/app.js"></script>');
  writeFileSync(join(root, 'dealerwatch/web/app.js'), 'console.info("DealerWatch");');
  writeFileSync(join(root, 'dealerwatch/web/style.css'), 'body { color: black; }');
  writeFileSync(join(root, '.env'), 'UNPUBLISHED_SECRET=value');
  return root;
}

test('build packages static assets and forwards API/audio to the configured HTTPS backend', () => {
  const root = fixture();
  try {
    const built = spawnSync(process.execPath, [script], {
      cwd: root, env: { ...process.env, DW_BACKEND_URL: 'https://backend.example.com/' }, encoding: 'utf8',
    });
    assert.equal(built.status, 0, built.stderr);
    const output = join(root, '.vercel/output');
    const config = JSON.parse(readFileSync(join(output, 'config.json'), 'utf8'));
    const api = config.routes.find(route => route.dest === 'https://backend.example.com/api/$1');
    const audio = config.routes.find(route => route.dest === 'https://backend.example.com/audio/$1');
    assert.ok(api && audio);
    assert.equal('/api/cases/CASE-1'.replace(new RegExp(api.src), api.dest), 'https://backend.example.com/api/cases/CASE-1');
    assert.equal('/audio/C-001'.replace(new RegExp(audio.src), audio.dest), 'https://backend.example.com/audio/C-001');
    assert.match(readFileSync(join(output, 'static/index.html'), 'utf8'), /\/static\/app\.js/);
    assert.match(readFileSync(join(output, 'static/static/app.js'), 'utf8'), /DealerWatch/);
    assert.throws(() => readFileSync(join(output, 'static/.env')));
    assert.throws(() => readFileSync(join(output, 'static/dealerwatch/api.py')));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('build refuses missing, insecure or credential-bearing backend addresses', () => {
  const root = fixture();
  try {
    for (const value of ['', 'http://backend.example.com', 'https://user:private-value@example.com',
      'https://backend.example.com/api', 'https://backend.example.com?query=1']) {
      const built = spawnSync(process.execPath, [script], {
        cwd: root, env: { ...process.env, DW_BACKEND_URL: value }, encoding: 'utf8',
      });
      assert.notEqual(built.status, 0);
      assert.match(built.stderr, /DW_BACKEND_URL/);
      assert.ok(!built.stderr.includes('private-value'));
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
