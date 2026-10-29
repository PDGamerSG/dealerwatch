# Vercel frontend and AWS backend

Vercel serves the basic frontend and proxies API/audio requests to one AWS-hosted Docker application. AWS keeps SQLite databases, imported datasets, archived audio and run history on persistent disk. This preserves the tested single-worker transaction and job behavior.

## Vercel

The repository's `vercel.json` runs `node scripts/build_vercel.mjs`. Set `DW_BACKEND_URL` in the Vercel project's build environment to the AWS backend's **HTTPS origin**, without a path, credentials or query string. The build emits only `index.html`, JavaScript and CSS to the static directory. The source repository, environment files and local generated/runtime data are not publicly served.

```bash
npx vercel link --project dealerwatch
npx vercel env add DW_BACKEND_URL preview
npx vercel deploy --yes
```

Add the exact resulting Vercel URL to `DW_PUBLIC_ORIGINS` on the backend and recreate the backend container. The setting is a comma-separated list of HTTPS origins; wildcards are rejected. Backend account tokens are never included in frontend JavaScript or Vercel build output. API and audio requests pass through external HTTPS rewrites with caching disabled.

## AWS

Use one Ubuntu 24.04 Lightsail instance, a static IPv4 address, and persistent disk. The intended Mumbai 2 GB plan is $12/month before credits, taxes and additional usage; check the bundle price and account eligibility before provisioning. The application must have only one worker/replica.

The AWS configuration is in `infra/aws/`. Copy source to the instance, install a private environment file at `/srv/dealerwatch/aws.env`, then run `sudo bash infra/aws/bootstrap.sh /srv/dealerwatch/aws.env` from that checkout. Required environment values are `PUBLIC_IP`, distinct `DW_ADMIN_TOKEN` and `DW_REVIEWER_TOKEN` of at least 32 characters, and the exact `DW_PUBLIC_ORIGINS`. Set `DW_COOKIE_SECURE=1`, `DW_LLM=mock`, `DW_ASR=replay` and `DW_DEMO=0` for the default hosted synthetic application. Secrets must not be committed or pasted into shell logs.

Open ports 80/443 and restrict SSH to the operator's IP. Caddy obtains a publicly trusted Let's Encrypt certificate for the static IP using the `shortlived` profile and renews it automatically. Its certificate state and the complete application data directory are persisted under `/srv/dealerwatch`. Port 8077 is bound only to host loopback for local diagnosis and is not exposed publicly.

Back up `/srv/dealerwatch/data` while the backend is stopped, together with the environment configuration and Caddy state. Take a disk snapshot before deleting/replacing the instance. Restarting or recreating containers preserves data; deleting the underlying instance disk does not. SQLite rollback journal mode is required for atomic case/audit commits; do not enable WAL or mount the databases over NFS/EFS.

## Verification

Local regression and deployment packaging:

```bash
uv run --frozen pytest -m '' -q
uv run --frozen ruff check .
node --test scripts/test_vercel_build.mjs
node --check dealerwatch/web/app.js
```

Read-only live checks use `scripts/check_deployment.py` and a token supplied by environment. Full live browser workflows use `DW_BROWSER_BASE_URL`, `DW_BROWSER_ADMIN_TOKEN`, `DW_BROWSER_REVIEWER_TOKEN` and explicit `DW_BROWSER_ALLOW_RESET=1`. Run these only against a disposable synthetic preview with `DW_DEMO=1`: the workflow exercises the destructive ledger-reset demonstration. Disable demo mutations before handing over a deployment intended to retain human reviews.

Vercel deployment protection, if enabled, is separate from the application's login. The verification tools accept a protection bypass token by environment; neither token is written to reports. Never share bypass tokens or publicize them in URLs.

Live hosted LLM/transcription behavior requires separately configured provider credentials. Mock/replay mode supports the complete evidence/review workflow without those services.
