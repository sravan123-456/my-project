resource "google_project_service" "secretmanager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_secret_manager_secret" "msg91_config" {
  secret_id = "vinayaka-msg91-config"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "msg91_config" {
  secret = google_secret_manager_secret.msg91_config.id
  secret_data = jsonencode({
    MSG91_AUTH_KEY   = var.msg91_auth_key
    MSG91_OTP_LENGTH = "6"
    MSG91_OTP_EXPIRY = "5"
  })
}

resource "google_secret_manager_secret_iam_member" "msg91_config_ci" {
  secret_id = google_secret_manager_secret.msg91_config.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cicd_service_account_email}"
}
