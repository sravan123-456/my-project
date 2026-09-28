#!/usr/bin/env bash
# Prepare a fresh GCP project for Terraform + app deployment.
set -euo pipefail

PROJECT_ID="${1:?Usage: bootstrap-gcp-project.sh <project_id> [region]}"
REGION="${2:-us-central1}"
TFSTATE_BUCKET="${PROJECT_ID}-vinayaka-tfstate"
CICD_SA_ID="github-actions"
CICD_SA_EMAIL="${CICD_SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Bootstrapping GCP project: ${PROJECT_ID} (region: ${REGION})"

gcloud config set project "${PROJECT_ID}"

APIS=(
  cloudresourcemanager.googleapis.com
  serviceusage.googleapis.com
  iam.googleapis.com
  compute.googleapis.com
  storage.googleapis.com
  storage-api.googleapis.com
  secretmanager.googleapis.com
)

echo "==> Enabling required APIs..."
gcloud services enable "${APIS[@]}" --project="${PROJECT_ID}"

if gcloud storage buckets describe "gs://${TFSTATE_BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "==> Terraform state bucket already exists: gs://${TFSTATE_BUCKET}"
else
  echo "==> Creating Terraform state bucket: gs://${TFSTATE_BUCKET}"
  gcloud storage buckets create "gs://${TFSTATE_BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
fi

if gcloud iam service-accounts describe "${CICD_SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "==> CI/CD service account already exists: ${CICD_SA_EMAIL}"
else
  echo "==> Creating CI/CD service account: ${CICD_SA_EMAIL}"
  gcloud iam service-accounts create "${CICD_SA_ID}" \
    --project="${PROJECT_ID}" \
    --display-name="GitHub Actions"
fi

bind_role() {
  local role="$1"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CICD_SA_EMAIL}" \
    --role="${role}" \
    --quiet >/dev/null
}

echo "==> Granting CI/CD roles to ${CICD_SA_EMAIL}..."
for role in \
  roles/compute.admin \
  roles/storage.admin \
  roles/iam.serviceAccountUser \
  roles/secretmanager.admin \
  roles/serviceusage.serviceUsageAdmin \
  roles/resourcemanager.projectIamAdmin; do
  bind_role "${role}"
done

echo ""
echo "Bootstrap complete."
echo "  Project:        ${PROJECT_ID}"
echo "  TF state bucket: gs://${TFSTATE_BUCKET}"
echo "  CI/CD SA:       ${CICD_SA_EMAIL}"
echo ""
echo "Ensure GitHub secret GCP_SA_KEY is a JSON key for ${CICD_SA_EMAIL}."
