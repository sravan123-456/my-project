# Local development (dev branch)

Production deploys from **`main`** only. Day-to-day work happens on **`dev`**.

## Branch workflow

```
dev branch  →  test locally (Docker)  →  merge to main  →  GitHub Actions deploys to indukuru.online
```

| Branch | Purpose | Auto-deploy |
|--------|---------|-------------|
| `dev` | Your local machine — build features, test | No (local Docker only) |
| `main` | Production | Yes → GCP VM |

## First-time setup

```powershell
cd my-project
git checkout dev
copy .env.example .env
# Edit .env — at minimum set SECRET_KEY; copy MSG91 keys from production if testing OTP
```

## Deploy locally (after every change on `dev`)

**Windows (PowerShell):**

```powershell
.\scripts\deploy-local.ps1
```

**Linux / Mac / Git Bash:**

```bash
./scripts/deploy-local.sh
```

Open **http://localhost:8080** and test.

Manual alternative:

```powershell
docker compose up --build -d
docker compose exec -T festival-app python scripts/smoke_test.py --url http://127.0.0.1:5000
```

## Ship to production

When local testing looks good:

```powershell
git checkout main
git pull origin main
git merge dev
git push origin main
```

GitHub Actions will run smoke tests and deploy to https://indukuru.online.

## Daily habit

```powershell
git checkout dev
# ... make changes ...
git add -A && git commit -m "your message"
git push origin dev
.\scripts\deploy-local.ps1
```
