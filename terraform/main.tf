provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_compute_address" "vm_ip" {
  name   = "${var.vm_name}-ip"
  region = var.region

  depends_on = [google_project_service.compute]
}

resource "google_compute_firewall" "app" {
  name    = "${var.vm_name}-allow-app"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.vm_name}-web"]

  depends_on = [google_project_service.compute]
}

resource "google_compute_instance" "vm" {
  name         = var.vm_name
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["${var.vm_name}-web"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.boot_disk_size_gb
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.vm_ip.address
    }
  }

  metadata = {
    secret-key      = var.secret_key
    github-repo-url = var.github_repo_url
    app-port        = tostring(var.app_port)
    ssh-keys        = "${var.ssh_user}:${var.ssh_public_key}"
  }

  metadata_startup_script = file("${path.module}/startup.sh")

  allow_stopping_for_update = true

  depends_on = [google_compute_firewall.app]
}
