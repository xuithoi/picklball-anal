# EC2 HTTPS backend and Cloudflare Worker

The frontend runs at `picklball-anal.xuithoi.workers.dev`. The Worker forwards
`/api/*` to `https://pickleballmvp.run.place`, where Caddy terminates HTTPS and
forwards to one FastAPI/YOLO process. The backend container has no public port.
Cloudflare Access protects the frontend/Worker; backend Basic authentication is
configured separately. No passwords or AWS keys belong in Git.

This recipe supports **Amazon Linux 2023 x86_64** (the existing EC2 machine) and
Ubuntu 24.04 x86_64. It does not create instances, resize disks or activate paid
plans. The existing `t3.micro`/8 GiB host can be used to try the deployment, but
model inference or rebuilding may exhaust its 1 GiB RAM or free disk space.
The Compose limit is a ceiling, not a reservation or increase in physical RAM.
Free Tier/credit eligibility is account-specific; storage and IPv4 can still cost
money. CPU credit mode Standard avoids surplus CPU credit charges by throttling.

## 1. Update EC2 after merging the pull request

Do not deploy the old `main` revision: it does not contain the Worker or these
scripts. After this PR is merged, from the existing EC2 checkout run:

```sh
cd ~/picklball-anal
git pull --ff-only origin main
sudo bash deploy/aws/bootstrap.sh
```

The bootstrap script preserves the installed Docker engine. On Amazon Linux, if
Compose is missing it installs Docker Compose v2.39.4 after checking the official
release's SHA-256 checksum. TLS/checksum verification stays enabled. The old
`bootstrap-ubuntu.sh` entrypoint forwards to the same installer.

## 2. Verify DNS and create private backend settings

The DNS A record for `pickleballmvp.run.place` must match the EC2 instance's
**current** public IPv4. It was `16.178.87.33` during setup; do not assume that
address survives Stop/Start. Allow TCP 80 and 443 in the instance security group.
For SSH, restrict port 22 to your own IP and, when using browser EC2 Instance
Connect, the service's published IP range for the instance's region. Do not
expose port 10000. If using Cloudflare DNS for the backend domain, start with
DNS-only mode so certificate troubleshooting is straightforward.

```sh
getent ahostsv4 pickleballmvp.run.place
cd ~/picklball-anal/deploy/aws
bash configure.sh pickleballmvp.run.place
```

`configure.sh` creates an ignored `.env` with mode 0600. It reuses the password
from `~/pickleball-backend.env` generated in the earlier Docker setup, if that
file exists. Otherwise it generates a new random password. An existing `.env`
is preserved and the command stops, so you can continue with that file after
checking its domain. Nonstandard legacy credentials require manual migration;
the script never silently changes an existing password.

Read the password only in your own secure terminal when entering the Cloudflare
secret. Do not paste it into chat, screenshots, command arguments, PRs or Git.
Do not print expanded `docker compose config` in shared logs; use `--quiet`.

## 3. Build, then switch the existing backend to Compose

Build using the existing Docker CLI (Compose build/Buildx is not required):

```sh
cd ~/picklball-anal
sudo docker build -t pickleball-ai .
cd deploy/aws
sudo docker volume create pickleball_data
```

Only after the build succeeds, stop the earlier standalone container if it exists:

```sh
sudo docker ps -a --filter name=pickleball-ai
sudo docker stop pickleball-ai
```

If that container does not exist, skip its stop command. The stopped container
is retained for rollback. Do not run it alongside Compose: both use the same job
volume and the application has an in-process job registry. Switching interrupts
any in-flight jobs; perform this when no video is processing.

Then start the backend and HTTPS proxy:

```sh
sudo docker compose up -d
sudo docker compose ps
curl --fail https://pickleballmvp.run.place/api/health
```

Expected JSON: `{"ok":true}`. Caddy obtains/renews a public certificate using
ports 80/443. Certificate issuance is asynchronous; check the logs if it is not
ready yet:

```sh
sudo docker compose logs --tail=60 backend https
```

Compose reuses the existing **`pickleball_data`** Docker volume (external), so
uploads/results from the original `docker run` are retained. Caddy stores TLS
state in its own persistent volumes. No `down -v` or volume deletion is needed.
Results still expire after the configured 30-minute retention period. The
initial upload limit is 100 MB and can be reduced in the private `.env`.

Rollback: `sudo docker compose stop`, then `sudo docker start pickleball-ai`
if the earlier standalone container was retained. Fix the issue before switching
back to Compose. The old backend is again loopback-only; HTTPS will be unavailable
while the Compose proxy is stopped.

## 4. Configure and deploy the Cloudflare Worker

Do this **after the HTTPS health check above succeeds**. This PR supplies the
actual API proxy (`worker/index.mjs`) and Wrangler asset bindings. Setting an
environment variable on the old static-only deployment cannot connect the API.

In Workers & Pages → `picklball-anal` → Settings → Variables and Secrets:

- `BACKEND_ORIGIN` (Text): `https://pickleballmvp.run.place` (no `/api`).
- `BACKEND_USERNAME` (Text): `kun`.
- `BACKEND_PASSWORD` (**Secret**): EC2's private `.env` `APP_PASSWORD`.

The first two nonsecret values are already supplied in `wrangler.jsonc`.
`keep_vars` preserves other dashboard variables; secrets stay in Cloudflare.
Keep the existing Cloudflare Access policy protecting the Worker, since it uses
the shared backend password on behalf of authenticated users. The Worker strips
Cloudflare cookies and identity tokens before forwarding requests to EC2.

Cloudflare Git build settings:

- Production branch: `main`, repository root: `/`.
- Build: `npm --prefix frontend ci && npm --prefix frontend run build`
- Deploy: `npx wrangler@4.158.0 deploy`

For non-production branches such as `fix/cloudflare-aws-deployment`, set the
**non-production/Preview deploy command** to `npx wrangler@4.158.0 preview`.
The production command remains `npx wrangler@4.158.0 deploy` on `main`.
The explicit `previews.vars` block is needed because Worker Preview variables
are not inherited from production. Assets and compatibility settings stay at
the top level; they are shared by both deployment modes.

The Preview currently points at the same EC2 backend as production. Production
secrets are not automatically inherited: add `BACKEND_PASSWORD` to the Preview's
secrets or Preview base config in Cloudflare, with the same backend password.
Only do this after protecting the Preview URL with Cloudflare Access as well;
the production Access policy may not cover Preview hostnames. Without the
Preview secret, the frontend can load and public health can work, but job APIs
return 401. Test uploads/deletion affect the shared backend's actual data.
Use a separate backend origin and credentials in `previews.vars`/Preview secrets
when you need isolated test data. No credential value belongs in this file.

After merging this PR, configure the secret and rerun the Git deployment if needed.
This replaces the old `--assets`-only deployment command. There is no automatic
AWS update from Cloudflare's build: EC2 must run the updated backend separately.

## 5. Check the complete workflow

After signing in to Cloudflare Access, `/api/health` on the Worker domain must
return `{"ok":true}`. Upload a short MP4, enter names, click the matching athletes
on frame zero, verify job completion, downloads and deletion. The Worker streams
uploads/downloads, but the Cloudflare plan can impose a lower request-size limit.
Start with a short clip. A health check alone does not verify inference or proxy
authentication: confirm an actual upload after each deployment.

Local checks:

```sh
node --test worker/*.test.mjs frontend/src/api.test.js
python3 -m unittest discover -s deploy/aws/tests -v
APP_PASSWORD=validation-only BACKEND_DOMAIN=pickleballmvp.run.place docker compose -f deploy/aws/compose.yaml config --quiet
```

The combined image has been built and smoke-tested locally under 1600 MB/1.5 CPU:
authentication, health, compiled frontend, YOLO inference on a synthetic 12-frame
clip, ball tracking, six exports and deletion. This does not prove readiness on
the smaller EC2 host or accuracy on real match footage. Public certificate
issuance and live Cloudflare-to-EC2 traffic must be checked on the real deployment.
