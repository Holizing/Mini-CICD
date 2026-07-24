# Ubuntu staging runbook

This runbook uses one Ubuntu 24.04 machine for both the Mini-CICD platform and
its deployment target. To keep the environment easy to manage, inspect and
document, all project-owned source code and runtime data stay under
`/home/cino/Mini-CICD`.

Only operating-system integration files for systemd, Nginx and sudoers are
installed under `/etc`. This separation keeps the complete project workspace
in one home directory without moving system configuration out of its standard
Ubuntu location.

## 1. Install runtime packages

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx openssh-server curl
```

Install Node.js 22 LTS and Docker Engine from their official repositories, then
verify:

```bash
node --version
npm --version
docker --version
python3 --version
```

## 2. Create service users

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin cicd
sudo useradd --create-home --shell /bin/bash deploy
sudo usermod -aG docker cicd
sudo usermod -aG docker deploy
sudo loginctl enable-linger deploy
```

`enable-linger` is required because Express, FastAPI and Spring Boot run as
`deploy` user systemd services.

## 3. Prepare project runtime

Run these commands from `/home/cino/Mini-CICD`:

```bash
mkdir -p runtime/{config,secrets,ssh,logs,workspace,www,npm-cache,docker-config,deployments}
sudo chgrp -R cicd /home/cino/Mini-CICD
sudo chmod -R g+rX /home/cino/Mini-CICD
sudo chown -R cicd:cicd runtime
sudo chown -R deploy:deploy runtime/deployments

python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
cp -a frontend/dist/. runtime/www/
```

Copy the environment example:

```bash
cp ops/linux/mini-cicd.env.example runtime/config/mini-cicd.env
```

Generate a JWT secret locally. Do not commit or print it:

```bash
umask 077
openssl rand -hex 64 > runtime/secrets/jwt-secret
```

## 4. Configure loopback SSH

Generate the deployment key as the `cicd` user:

```bash
sudo -u cicd ssh-keygen -t rsa -b 4096 -N '' \
  -f /home/cino/Mini-CICD/runtime/ssh/deploy_rsa
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
sudo sh -c 'cat /home/cino/Mini-CICD/runtime/ssh/deploy_rsa.pub >> /home/deploy/.ssh/authorized_keys'
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Pin the local SSH server key. Mini-CICD rejects unknown keys:

```bash
sudo -u cicd sh -c 'ssh-keyscan -H 127.0.0.1 > /home/cino/Mini-CICD/runtime/ssh/known_hosts'
sudo chown cicd:cicd runtime/ssh/known_hosts
sudo chmod 600 runtime/ssh/known_hosts
sudo -u cicd ssh \
  -i /home/cino/Mini-CICD/runtime/ssh/deploy_rsa \
  deploy@127.0.0.1 true
```

For Deploy requests use:

```text
server_ip: 127.0.0.1
server_user: deploy
server_ssh_key: /home/cino/Mini-CICD/runtime/ssh/deploy_rsa
```

## 5. Install platform services

```bash
sudo cp ops/linux/mini-cicd.service /etc/systemd/system/
sudo cp ops/linux/nginx-mini-cicd.conf /etc/nginx/sites-available/mini-cicd
sudo ln -sfn /etc/nginx/sites-available/mini-cicd /etc/nginx/sites-enabled/mini-cicd
sudo cp ops/linux/nginx-webhook.conf /etc/nginx/sites-available/mini-cicd-webhook
sudo ln -sfn /etc/nginx/sites-available/mini-cicd-webhook /etc/nginx/sites-enabled/mini-cicd-webhook
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp ops/linux/sudoers-mini-cicd /etc/sudoers.d/mini-cicd
sudo chmod 440 /etc/sudoers.d/mini-cicd
sudo visudo -cf /etc/sudoers.d/mini-cicd
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now mini-cicd nginx ssh docker
```

Create the application admin interactively:

```bash
sudo -u cicd /home/cino/Mini-CICD/.venv/bin/python -m backend.auth.create_admin --username admin
```

## 6. Runtime settings

Set these values in the Settings page:

```text
Workspace: /home/cino/Mini-CICD/runtime/workspace
Logs: /home/cino/Mini-CICD/runtime/logs
Build timeout: 900
Deploy timeout: 900
Docker enabled: true
Auto deploy: false
```

Keep `MINI_CICD_ENABLE_EXPERIMENTAL_STRATEGIES=false`. The Deploy page reports
whether a selected build is Verified, Experimental disabled, Experimental
enabled or Unsupported.

In the Settings page, configure the deployment target:

```text
Host: 127.0.0.1
SSH port: 22
SSH user: deploy
Private key: /home/cino/Mini-CICD/runtime/ssh/deploy_rsa
Known hosts: /home/cino/Mini-CICD/runtime/ssh/known_hosts
```

Save the target and use **Test connection** before enabling Auto Deploy.

## 7. React/Vite source demo

Install the dedicated Nginx site:

```bash
sudo cp ops/linux/nginx-demo-source.conf /etc/nginx/sites-available/mini-cicd-demo
sudo ln -sfn /etc/nginx/sites-available/mini-cicd-demo /etc/nginx/sites-enabled/mini-cicd-demo
sudo nginx -t
sudo systemctl reload nginx
```

Use:

```text
deploy_path: /home/cino/Mini-CICD/runtime/deployments/react-vite
service_name: nginx
health_check_port: 8081
health_check_path: /
```

The strategy uploads the prebuilt `dist/` artifact to `releases/<deploy_id>`,
atomically switches `current`, reloads Nginx and rolls back on failed health.

## 8. Verified profile contracts

- React/Vite: directory artifact containing `index.html`; Nginx and curl.
- Express: directory with `package.json`, `package-lock.json` and a `start`
  script; installs with `npm ci --omit=dev`.
- FastAPI: directory with `main.py` and exact `==` requirements; starts
  `main:app` using a per-release virtual environment.
- Spring Boot: exactly one executable `.jar`; starts with `java -jar`.
- Docker: built image or existing image; validates the running container and
  optional HTTP endpoint.

## 9. Restart verification

```bash
sudo reboot
```

After Ubuntu starts again, check:

```bash
systemctl is-active mini-cicd nginx ssh docker
systemctl --user --machine=deploy@ is-active default.target
curl -I http://localhost
curl -I http://localhost:8081
```

The Mini-CICD source, database, workspace, logs, frontend build, SSH material
and deployment evidence remain under `/home/cino/Mini-CICD` after the restart.

## 10. GitHub webhook automation

Set a new Webhook secret in Settings, then configure Automation on the target
Project. The Project repository must use `github.com`, and its branch must
match the GitHub push branch exactly.

Install and authenticate Tailscale on Ubuntu. Publish only the loopback webhook
listener:

```bash
sudo tailscale funnel --bg --https=443 http://127.0.0.1:8080
tailscale funnel status
```

Create a GitHub repository webhook with:

```text
Payload URL: https://<ubuntu-node>.<tailnet>.ts.net/api/webhooks/github
Content type: application/json
Secret: the value entered in Mini-CICD Settings
Events: Just the push event
```

The Nginx listener on `127.0.0.1:8080` proxies only the exact webhook path.
Every other path returns `404`. A valid push is acknowledged immediately and
appears on the Automation page while Build and Deploy continue in the
background.

For a source Project, configure the build script and health endpoint. For a
Docker Project, also configure image name/tag, Dockerfile, context, container
name and port mapping. Webhook automation never executes a custom deploy
script.
