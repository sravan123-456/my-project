# Post-Deploy Checklist — DanSetu

Run this **after every deployment** to catch regressions before users do.

---

## Automated checks (GitHub Actions)

| When | Workflow | What it checks |
|------|----------|----------------|
| Every push / PR to `main` | **Smoke Tests** (`smoke-test.yml`) | Routes, DB migrations, static files (in CI) |
| Every deploy to production | **Deploy** (`deploy.yml`) | Live URL smoke tests after health check |

View results: GitHub repo → **Actions** tab.

Logged-in smoke tests (optional): set `SMOKE_ORG`, `SMOKE_USER`, `SMOKE_PASSWORD` when running on the server (see below).

---

## Quick automated check (2 minutes)

On the server (or locally inside Docker):

```bash
cd /opt/vinayaka-festival

# In-app checks (database, routes, migrations)
docker compose exec -T festival-app python scripts/smoke_test.py

# Live site checks (through Nginx / HTTPS)
docker compose exec -T festival-app python scripts/smoke_test.py --url https://indukuru.online
```

Optional — test login with a real committee account:

```bash
docker compose exec -T \
  -e SMOKE_ORG=indukuru \
  -e SMOKE_USER=test1 \
  -e SMOKE_PASSWORD='your-password' \
  festival-app python scripts/smoke_test.py
```

**All tests must pass** before you tell the committee the deploy is done.

To skip smoke tests during deploy (emergency only):

```bash
SKIP_SMOKE_TEST=1 bash scripts/deploy.sh
```

---

## Manual checklist (15–20 minutes)

Tick each item on **mobile** and **desktop** after major releases.

### 1. Public / landing

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 1.1 | Open https://indukuru.online | Landing loads, collage images visible | |
| 1.2 | Language switch (EN / TE / HI / KN) | Text changes, no broken layout | |
| 1.3 | **Join existing committee** → fill form | Create account button works | |
| 1.4 | OTP on join (if MSG91 enabled) | OTP sent & verified, account created | |
| 1.5 | **Login** with committee code + user + password | Reaches dashboard | |
| 1.6 | **Start new committee** (pricing page) | Form loads, OTP + submit works | |

### 2. Dashboard & festival year

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 2.1 | Dashboard loads | Totals, banner, festival year badge | |
| 2.2 | Shows **current festival year** data only | Banner note links to Reports | |
| 2.3 | Committee Admin → **Start planning for 2027** | Year updates, dashboard refreshes | |

### 3. Donations & expenses

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 3.1 | Add donation (cash + UPI) | Saved, appears in list | |
| 3.2 | Add expense | Saved, balance updates on dashboard | |
| 3.3 | Edit / delete donation or expense | Works without error | |
| 3.4 | Pledges — add, collect, cancel | Pledge flow works | |
| 3.5 | Payment QR on donations page | Shows if uploaded in admin | |

### 4. Reports & archive

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 4.1 | Reports → year dropdown | 2026 / 2027 data separated | |
| 4.2 | Festival Year Archive table | Past years listed with totals | |
| 4.3 | Export CSV | Downloads correctly | |
| 4.4 | Export PDF | Generates without 500 error | |

### 5. Gallery

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 5.1 | Gallery year dropdown | Switch years | |
| 5.2 | Upload photo (current year) | Appears in grid | |
| 5.3 | Lightbox / view photo | Opens correctly | |

### 6. Committee admin

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 6.1 | Approve pending user | User can log in | |
| 6.2 | Invite link copy | Link works for new join | |
| 6.3 | Banner upload | Shows on dashboard | |
| 6.4 | Forgot password → OTP → reset | Password updated, can log in | |

### 7. Site admin

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 7.1 | Site Admin dashboard | Stats load | |
| 7.2 | Contacts → **Active committees** tab | Phone numbers listed | |
| 7.3 | Contacts → **Archived** tab | Shows deleted-committee numbers | |
| 7.4 | Approve pending committee | Committee can log in | |
| 7.5 | Delete test committee (not indukuru) | No 500; phones in Archived tab | |
| 7.6 | Same phone in two committees | Both registrations allowed | |

### 8. Mobile layout

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 8.1 | Landing on phone | No cut-off text, scroll OK | |
| 8.2 | After registration “Back to home” | Full screen visible | |
| 8.3 | Dashboard bottom nav | All links work | |
| 8.4 | Donations / expenses forms | Usable on small screen | |

### 9. Regression hotspots (check if related code changed)

| Area | Files often touched | Quick check |
|------|---------------------|-------------|
| OTP / MSG91 | `msg91*.js`, `auth.py` OTP routes | Join + forgot-password OTP |
| Festival year | `year_scope.py`, `admin.py` | Dashboard year + Reports year |
| Committee delete | `outreach_service.py`, `site_admin.py` | Delete + Archived contacts |
| Landing / CSS | `landing.css`, `landing.html` | Mobile join + collage |
| Deploy / env | `.env`, Docker | `/health` returns `{"status":"ok"}` |

---

## If something fails

1. Note **which step** failed and the **exact error message** (screenshot helps).
2. On the server: `docker compose logs --tail=100 festival-app`
3. Roll back if critical: redeploy previous working build from git.
4. Fix locally → run `python scripts/smoke_test.py` → deploy again.

---

## Deploy command reference

```bash
# Standard deploy (includes smoke tests)
bash scripts/deploy.sh

# Manual deploy + smoke
cd /opt/vinayaka-festival
sudo docker compose up -d --build
docker compose exec -T festival-app python scripts/smoke_test.py --url https://indukuru.online
```

---

*Last updated: feature areas include OTP widget, festival year, gallery, site-admin contacts, multi-committee phone numbers.*
