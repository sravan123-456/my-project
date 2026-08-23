# GCP Deployment Guide — Vinayaka Festival App

Project: **business-account-506411**  
VM: **e2-micro** (cheapest, free-tier eligible in `us-central1`)  
App URL: `http://<VM_IP>:8080`

---

## Overview

| Workflow | When to run | What it does |
|----------|-------------|--------------|
| **Provision GCP VM (Terraform)** | First time + infra changes | Creates VM, static IP, firewall, installs Docker |
| **Deploy Application to GCP VM** | Every code change | Pulls latest code and runs `docker compose up` |

---

## One-time setup (do this once)

### 1. Enable APIs in GCP

In [GCP Console](https://console.cloud.google.com/compute/instances?project=business-account-506411):

- Enable **Compute Engine API**
- Enable **Cloud Storage API**

Or run:
```bash
gcloud config set project business-account-506411
gcloud services enable compute.googleapis.com storage.googleapis.com
```

### 2. Create Terraform state bucket

```bash
gcloud storage buckets create gs://business-account-506411-vinayaka-tfstate \
  --project=business-account-506411 \
  --location=us-central1 \
  --uniform-bucket-level-access
```

### 3. Create a service account for GitHub Actions

```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deploy"

gcloud projects add-iam-policy-binding business-account-506411 \
  --member="serviceAccount:github-actions@business-account-506411.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud projects add-iam-policy-binding business-account-506411 \
  --member="serviceAccount:github-actions@business-account-506411.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding business-account-506411 \
  --member="serviceAccount:github-actions@business-account-506411.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud iam service-accounts keys create gcp-sa-key.json \
  --iam-account=github-actions@business-account-506411.iam.gserviceaccount.com
```

### 4. Generate SSH key for VM access

```powershell
ssh-keygen -t ed25519 -C "vinayaka-vm" -f vinayaka_vm_key -N '""'
```

### 5. Add GitHub Secrets

Go to: **https://github.com/sravan123-456/my-project/settings/secrets/actions**

| Secret | Value |
|--------|-------|
| `GCP_SA_KEY` | Full contents of `gcp-sa-key.json` |
| `SECRET_KEY` | Long random string for Flask (e.g. 64 chars) |
| `SSH_PUBLIC_KEY` | Full contents of `vinayaka_vm_key.pub` |

---

## Deploy

### Step 1 — Provision VM (first time only)

1. Go to **GitHub → Actions → Provision GCP VM (Terraform)**
2. Click **Run workflow**
3. Wait ~5–8 minutes
4. Note the app URL in the workflow summary: `http://<IP>:8080`

### Step 2 — Deploy application (every code update)

1. Push code to `main`, **or**
2. Go to **GitHub → Actions → Deploy Application to GCP VM → Run workflow**

---

## Local Terraform (optional)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform apply
```

---

## Useful commands

```bash
# SSH into VM
gcloud compute ssh vinayaka-festival --zone=us-central1-a --project=business-account-506411

# View startup logs on VM
sudo tail -f /var/log/vinayaka-startup.log

# Manual redeploy on VM
cd /opt/vinayaka-festival && ./scripts/deploy.sh

# Destroy infrastructure (careful!)
cd terraform && terraform destroy
```

---

## What I need from you

Please add these **3 GitHub secrets** before running workflows:

1. `GCP_SA_KEY` — service account JSON (step 3 above)
2. `SECRET_KEY` — app secret key
3. `SSH_PUBLIC_KEY` — your SSH public key

After that, run **Provision GCP VM** first, then **Deploy Application**.
