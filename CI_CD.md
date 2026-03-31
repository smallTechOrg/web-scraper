# CI/CD Pipeline

## Overview

Automated lint → deploy pipeline via GitHub Actions. Deploys to `staging-instance` on every push to `main`. There is no staging/production split — the scraper has a single deployment.

## Architecture

```
Push to main ──▶ lint ──▶ SSH deploy to staging-instance (port 5001)
```

## Pipeline Stages

### 1. Test (`test` job)

- **Python**: 3.12
- **Lint**: `ruff check .`
- **Tests**: `pytest -v` (currently no test files — will pass with a warning)

### 2. Deploy (`deploy` job)

Triggers on pushes to `main` after tests pass.

1. Authenticates to GCP
2. SSHs into `staging-instance` and runs:
   - `git fetch --all && git reset --hard origin/main`
   - `scripts/deploy.sh` (activates venv, installs deps, restarts Flask on port 5001)
3. Verifies `GET /api/health` returns 200

## Deploy Script (`scripts/deploy.sh`)

Runs on the VM:

1. `cd /opt/web-scraper-boilerplate`
2. Activates `venv/`
3. `pip install -r requirements.txt`
4. Kills any existing Flask process on port 5001
5. Starts Flask via `nohup flask run --host=0.0.0.0 --port=5001`

## GitHub Secrets Required

| Secret | Environment | Value |
|--------|-------------|-------|
| `GCP_SA_KEY` | (repo-level) | Service account JSON key |
| `GCP_PROJECT` | (repo-level) | `ai-agent-boilerplate0` |
| `GCP_VM_INSTANCE_NAME` | production | `staging-instance` |
| `GCP_ZONE` | production | `us-central1-f` |

## GitHub Environments

- **production** — create in repo Settings → Environments. Optional: add required reviewers.

## VM Prerequisites

1. Repo cloned at `/opt/web-scraper-boilerplate`
2. Python 3.12 virtualenv at `venv/`
3. Playwright chromium installed (`python -m playwright install --with-deps chromium`)
4. System deps for OpenCV: `sudo apt install libgl1`
5. `.env` file with `GROQ_API_KEY` and any other required env vars
6. SSH key added to GitHub for `git fetch`

## Rollback

```bash
gcloud compute ssh staging-instance --zone=us-central1-f --command="
  cd /opt/web-scraper-boilerplate &&
  sudo git reset --hard GOOD_COMMIT_SHA &&
  sudo ./scripts/deploy.sh
"
```
