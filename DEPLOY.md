# Deploy Pickleball Kun AI

The root `Dockerfile` builds the React frontend and FastAPI backend into one web
service. The CPU model is included at build time. The app serves the homepage,
assets and `/api` from one origin; no separate frontend server is needed.

## Botkeep (Application)

Choose **Application**, then a Docker/Dockerfile runtime if the platform offers it.
A static-site runtime cannot execute the AI backend. Use:

| Setting | Value |
| --- | --- |
| Repository | `xuithoi/picklball-anal` |
| Branch | `feat/pickleball-ai-mvp-autodelete` |
| Build context | repository root (`.`) |
| Dockerfile | `Dockerfile` at repository root |
| Port | `10000` (or set `PORT` to the platform-assigned port) |
| RAM | 2048 MB for initial short-video testing |
| CPU | 150% / 1.5 vCore if available |
| Storage | 10 GB recommended; 1 GB is insufficient for the ML stack and videos |
| Persistent mount | `/var/data` |
| Instances / workers | 1 / 1 |
| Health check | `/api/health` |

Set environment variables in the hosting dashboard, not in repository files:

- `REQUIRE_AUTH=1`
- `APP_USERNAME=kun`
- `APP_PASSWORD`: choose a long, unique password using the host's secure environment editor.
- `MAX_UPLOAD_MB=100` initially on a small server (the UI's 600 MB client ceiling
  does not override this lower server limit).
- `RESULT_TTL_SECONDS=1800`
- `CLEANUP_INTERVAL_SECONDS=30`

Enable the host's HTTPS domain before signing in. The browser will prompt for the
username and password. The health check is public; all application and API routes
require authentication when configured. Startup fails if authentication is required
but the password is absent. This is a private MVP access gate, not multi-user accounts.

If Botkeep does not offer Docker, do not select "Static site" to work around it:
Python, Node (for the frontend build), FFmpeg, OpenCV system libraries and a Unicode
font are required. Confirm the supported runtime and filesystem paths first.

Start with 30–60 second videos and one upload at a time. A 2 GB CPU service is a
starting point, not a guarantee for long 1080p videos; increase RAM/CPU if the host
reports memory exhaustion. Persistent disks retain results across restarts, but
in-flight jobs are interrupted because the MVP has no durable queue.

## Render alternative

`render.yaml` declares one Docker web service, one worker, a persistent 10 GB disk,
health checks and an automatically generated access password. It uses the **paid
Standard plan**; review the service and disk charges shown by Render before creating
it. No Render service has been created by saving these files.

1. Sign in at https://dashboard.render.com/ and choose **New → Blueprint**.
2. Connect `xuithoi/picklball-anal` and select branch
   `feat/pickleball-ai-mvp-autodelete` (the default `main` branch has no app).
3. Use the root `render.yaml`, review resources and create the Blueprint.
4. Wait for the build and health check to complete. Use the service URL Render
   actually assigns; do not assume a particular `onrender.com` name is available.
5. In the service's Environment settings, securely view `APP_PASSWORD`. Sign in
   to the assigned HTTPS URL with username `kun` and that password. Do not send
   the password in chat.

After initial deployment, automatic deployment is disabled. To update, select the
new commit in the hosting dashboard and deploy manually.

## Validation of the deployment image

The root Docker image was built and tested locally with a 2 GB memory limit and
1.5 vCore limit. Checks covered authentication, the compiled homepage and logo,
actual video inference, Unicode names, ball observations, heatmap, six exports and
confirmed deletion. A completed job and its files survived a container restart on
the mounted volume. The backend suite passed 34 tests. This is a short-clip smoke
test, not a capacity guarantee for long 1080p videos or a live hosting deployment.

## Cloudflare frontend with a Docker backend

A static frontend deployment alone cannot execute the Python/PyTorch/FFmpeg video
pipeline. The repository's `wrangler.jsonc` deploys frontend assets and a Worker
that streams `/api/*` requests to a separately running Docker backend. Vite's
proxy is only for local development. A Worker alone does not provision that backend.

Cloudflare build settings (repository root `/`):

- Build command: `npm --prefix frontend ci && npm --prefix frontend run build`
- Deploy command: `npx wrangler@4.158.0 deploy`

The checked-in Wrangler configuration supplies the Worker entrypoint, assets and
compatibility date. In the Worker's **Settings → Variables and Secrets**, add:

- `BACKEND_ORIGIN`: the actual HTTPS backend origin, e.g. `https://your-service.example.com`.
  Supply only the origin, without `/api`, query strings or credentials. The
  checked-in default is `https://pickleballmvp.run.place`; verify its HTTPS health
  before deploying the Worker.
- If the backend uses its existing Basic authentication, `BACKEND_USERNAME`
  (default `kun`) and **secret** `BACKEND_PASSWORD` matching the backend's
  `APP_PASSWORD`. Enter the password securely in Cloudflare, never in Git or chat.

Keep the Worker's existing Cloudflare Access protection enabled when using a
shared backend password: the Worker uses that credential on behalf of its allowed
users. Cloudflare Access cookies and identity tokens are not forwarded upstream.
The backend should remain protected by its own authentication.

Redeploy after saving the settings. `/api/health` must return `{"ok":true}`;
then validate an upload, job polling, downloads and deletion through the Worker.
If no backend is configured, the Worker returns a JSON 503 with setup instructions
rather than serving the frontend HTML for API calls. Upload size is also limited
by the Cloudflare plan and backend settings; a 600 MB client ceiling does not
raise either limit. Services handling model inference must use one Uvicorn worker.

Run proxy regression checks with `node --test worker/index.test.mjs`.
No cloud backend is created or paid plan activated by adding this configuration.

## AWS EC2

For the existing Docker backend on AWS EC2 with HTTPS and Cloudflare API routing,
see [deploy/aws/README.md](deploy/aws/README.md). The EC2 recipe includes a single
backend worker, persistent Docker volumes, generated private authentication settings
and Caddy HTTPS. It does not create AWS resources or guarantee free hosting.
