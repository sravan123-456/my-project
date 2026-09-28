# One-Click GCP Bootstrap

Use this when your current GCP subscription ends and you create a **new GCP account**, **billing account**, and **project**.

## What the pipeline does

**GitHub Actions → Bootstrap New GCP Project (one-click)** runs three stages:

1. **Prepare** — enables APIs, creates Terraform state bucket, creates `github-actions` service account + IAM roles
2. **Provision** — runs Terraform (VM, static IP, firewall, Secret Manager)
3. **Deploy** — deploys the Docker app on the VM and runs a health check

It reuses the same Terraform and deploy logic as the existing `Provision GCP VM` and `Deploy Application` workflows.

---

## Before you click Run (one-time per new GCP project)

### 1. Create the GCP project

In the [GCP Console](https://console.cloud.google.com/):

- Create a new project and note the **project ID**
- Link a **billing account**

### 2. Create a bootstrap service account key

You need **one** service account key in GitHub before the pipeline can authenticate. The bootstrap job will create the long-lived `github-actions@<project>.iam.gserviceaccount.com` account if it does not exist.

**Option A — use Owner for first run (simplest)**

```bash
gcloud config set project YOUR_NEW_PROJECT_ID
gcloud iam service-accounts create bootstrap-ci --display-name="Bootstrap CI"
gcloud projects add-iam-policy-binding YOUR_NEW_PROJECT_ID \
  --member="serviceAccount:bootstrap-ci@YOUR_NEW_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/owner"
gcloud iam service-accounts keys create gcp-sa-key.json \
  --iam-account=bootstrap-ci@YOUR_NEW_PROJECT_ID.iam.gserviceaccount.com
```

**Option B — after first bootstrap**, replace `GCP_SA_KEY` with a key for `github-actions@YOUR_NEW_PROJECT_ID.iam.gserviceaccount.com`.

### 3. GitHub Secrets (repository settings)

| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | Service account JSON (bootstrap or github-actions SA) |
| `SECRET_KEY` | Flask app secret (long random string) |
| `SSH_PUBLIC_KEY` | Your SSH public key for VM access |

### 4. Run the workflow

1. Go to **Actions → Bootstrap New GCP Project (one-click)**
2. Click **Run workflow**
3. Fill in:
   - **gcp_project_id** — your new project ID
   - **domain_name** — e.g. `indukuru.online`
   - Other fields are optional (defaults match current setup)

### 5. After the workflow finishes

1. Copy the **static IP** from the Terraform job summary
2. Point your domain **A record** to that IP (Namecheap / Cloudflare / etc.)
3. Wait for DNS + SSL (Certbot on VM) — then open `https://your-domain`
4. Update `GCP_SA_KEY` to the `github-actions@...` key if you used a temporary bootstrap SA

---

## Workflow inputs

| Input | Required | Default |
|-------|----------|---------|
| `gcp_project_id` | Yes | — |
| `domain_name` | Yes | — |
| `gcp_region` | No | `us-central1` |
| `gcp_zone` | No | `us-central1-a` |
| `vm_name` | No | `vinayaka-festival` |
| `github_repo_url` | No | this repo |
| `ssh_user` | No | `vandana` |

---

## Manual bootstrap (optional)

```bash
chmod +x scripts/bootstrap-gcp-project.sh
./scripts/bootstrap-gcp-project.sh YOUR_PROJECT_ID us-central1
```

Then run **Provision GCP VM** and **Deploy Application** workflows with the same project ID and domain.

---

## APIs enabled automatically

- Compute Engine, Cloud Storage, Secret Manager
- Secret Manager (MSG91 OTP config)
- IAM, Service Usage, Cloud Resource Manager
