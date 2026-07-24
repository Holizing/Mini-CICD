# Mini-CICD release checklist

This checklist defines the v1 internship/demo release gate. It is intentionally
manual: the repository does not contain GitHub Actions because Mini-CICD itself
is the CI/CD system being demonstrated.

## Supported scope

The verified profiles are:

| Profile | Build contract | Deploy contract | Health endpoint |
| --- | --- | --- | --- |
| React/Vite | `npm ci`, `npm run build`, `dist/` | Nginx static release | `:8081/` |
| Express | `npm ci`, locked dependencies | User systemd service | `:3101/health` |
| FastAPI | compile plus exact Python pins | Virtualenv and user systemd service | `:8101/health` |
| Spring Boot | Maven executable JAR | User systemd service | `:8181/health` |
| Docker | Build image from Git | Docker container | `:8082/` |

All other strategies are experimental and disabled by default. The release
uses one Ubuntu host, one deployment target, SQLite, and FastAPI
`BackgroundTasks`. Multi-host scheduling, a durable queue, rollback
orchestration, HTTPS owned by the application and GitHub Actions are outside
this release.

## Automated local gate

Run from the repository root with an isolated virtual environment:

```bash
python3 -m venv .venv-test
.venv-test/bin/python -m pip install -r backend/requirements-dev.txt
.venv-test/bin/python -m pytest backend/tests
.venv-test/bin/python -m pip check
.venv-test/bin/python -m compileall backend
.venv-test/bin/python -c "from backend.app import app; print(len(app.routes))"
npm --prefix frontend ci
npm --prefix frontend run build
git diff --check
```

The test fixture sets `MINI_CICD_DATABASE_PATH` to a disposable SQLite file.
Never point tests at `backend/cicd.db` or
`/home/cino/Mini-CICD/runtime/cicd.db`.

Expected structural result:

- 10 SQLAlchemy tables.
- 37 FastAPI routes.
- No failing backend tests.
- A successful frontend production build.
- No `.github/workflows` directory.

`npm audit` currently reports the React Router RSC/server-action advisory for
`react-router-dom` 7.18.1. Mini-CICD uses a client-only Vite SPA and does not
enable React Server Components, SSR actions or React Router framework mode, so
the affected code path is not reachable. Vite and its transitive PostCSS and
esbuild dependencies must otherwise be on their patched release line.

## Ubuntu preflight

Before a public webhook test:

```bash
systemctl is-active mini-cicd nginx ssh docker
curl --fail http://127.0.0.1/api/health
sudo -u cicd ssh \
  -i /home/cino/Mini-CICD/runtime/ssh/deploy_rsa \
  -o UserKnownHostsFile=/home/cino/Mini-CICD/runtime/ssh/known_hosts \
  deploy@127.0.0.1 true
tailscale funnel status
```

Confirm Settings has:

- Workspace `/home/cino/Mini-CICD/runtime/workspace`.
- Logs `/home/cino/Mini-CICD/runtime/logs`.
- Build and deploy timeouts `900`.
- Docker enabled.
- A webhook secret between 32 and 255 characters.
- The loopback deployment target and trusted host-key file.

## Public webhook checks

The public Nginx listener must expose only:

```text
POST /api/webhooks/github
```

Required checks:

1. GitHub `ping` receives `200`.
2. Invalid HMAC receives `401`.
3. Duplicate `X-GitHub-Delivery` does not create another pipeline.
4. A push to the wrong branch is recorded as `ignored`.
5. Auto Deploy off ends at `build_succeeded`.
6. Build failure creates no Deploy.
7. Bad SSH credentials end at `failed` without a stuck worker.
8. Restart recovery marks interrupted deliveries `failed`.

## Five-profile evidence

Trigger the demo branches one at a time and record the resulting IDs:

| Branch | Delivery | Build | Deploy | Terminal status | Health |
| --- | --- | --- | --- | --- | --- |
| `demo/react-vite` |  |  |  |  | `http://localhost:8081/` |
| `demo/express` |  |  |  |  | `http://localhost:3101/health` |
| `demo/fastapi` |  |  |  |  | `http://localhost:8101/health` |
| `demo/spring-boot` |  |  |  |  | `http://localhost:8181/health` |
| `demo/docker` |  |  |  |  | `http://localhost:8082/` |

For each row verify:

- The Build commit hash equals the GitHub payload `after` SHA.
- Project, Build and Deploy metadata are linked without manual duplication.
- Every stage reaches a terminal state.
- Logs contain no webhook secret, password or private-key content.

## Release sequence

1. Complete the local gate and five-profile evidence.
2. Mark the webhook PR ready and merge it into `dev` with a merge commit.
3. Open one release PR from `dev` to `main`.
4. Preserve the tracked demo database when resolving the release PR.
5. Test a clean clone of `main`.
6. Create annotated tag `v1.0.0`.
7. Keep all feature and demo branches for project history.
