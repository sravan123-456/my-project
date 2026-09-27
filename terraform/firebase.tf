resource "google_project_service" "firebase" {
  project            = var.project_id
  service            = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "identitytoolkit" {
  project            = var.project_id
  service            = "identitytoolkit.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id

  depends_on = [google_project_service.firebase]
}

resource "google_firebase_web_app" "default" {
  provider     = google-beta
  project      = var.project_id
  display_name = "DanSetu Web"

  depends_on = [google_firebase_project.default]
}

data "google_firebase_web_app_config" "default" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.default.app_id
}

resource "google_identity_platform_config" "default" {
  provider = google-beta
  project  = var.project_id

  authorized_domains = [
    var.domain_name,
    "localhost",
    "${var.project_id}.firebaseapp.com",
    "${var.project_id}.web.app",
  ]

  sign_in {
    allow_duplicate_emails = false

    phone_number {
      enabled = true
      test_phone_numbers = {}
    }
  }

  sms_region_config {
    allowlist_only {
      allowed_regions = ["IN"]
    }
  }

  depends_on = [
    google_project_service.identitytoolkit,
    google_firebase_project.default,
  ]
}

# Google Sign-In: personal GCP projects (no org) cannot use google_iap_brand.
# Enable Google provider in Firebase Console → Authentication → Sign-in method → Google.

resource "google_service_account" "firebase_admin" {
  account_id   = "vinayaka-firebase-admin"
  display_name = "Vinayaka Festival Firebase Admin"
}

resource "google_project_iam_member" "firebase_admin_role" {
  project = var.project_id
  role    = "roles/firebase.admin"
  member  = "serviceAccount:${google_service_account.firebase_admin.email}"
}

resource "google_service_account_key" "firebase_admin_key" {
  service_account_id = google_service_account.firebase_admin.name
}

resource "google_secret_manager_secret" "firebase_admin_sa" {
  secret_id = "vinayaka-firebase-admin-sa"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "firebase_admin_sa" {
  secret      = google_secret_manager_secret.firebase_admin_sa.id
  secret_data = base64decode(google_service_account_key.firebase_admin_key.private_key)
}

resource "google_secret_manager_secret" "firebase_web_config" {
  secret_id = "vinayaka-firebase-web-config"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "firebase_web_config" {
  secret = google_secret_manager_secret.firebase_web_config.id
  secret_data = jsonencode({
    FIREBASE_PROJECT_ID            = var.project_id
    FIREBASE_API_KEY               = data.google_firebase_web_app_config.default.api_key
    FIREBASE_AUTH_DOMAIN           = data.google_firebase_web_app_config.default.auth_domain
    FIREBASE_APP_ID                = google_firebase_web_app.default.app_id
    FIREBASE_MESSAGING_SENDER_ID   = data.google_firebase_web_app_config.default.messaging_sender_id
    FIREBASE_SERVICE_ACCOUNT       = "/app/secrets/firebase-service-account.json"
  })
}

resource "google_secret_manager_secret_iam_member" "firebase_admin_sa_ci" {
  secret_id = google_secret_manager_secret.firebase_admin_sa.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cicd_service_account_email}"
}

resource "google_secret_manager_secret_iam_member" "firebase_web_config_ci" {
  secret_id = google_secret_manager_secret.firebase_web_config.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cicd_service_account_email}"
}
