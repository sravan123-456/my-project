output "vm_external_ip" {
  description = "Static public IP of the VM."
  value       = google_compute_address.vm_ip.address
}

output "static_ip_name" {
  description = "Reserved static IP resource name in GCP."
  value       = google_compute_address.vm_ip.name
}

output "dns_a_record_value" {
  description = "Add this IP as an A record for @ and www in Namecheap Advanced DNS."
  value       = google_compute_address.vm_ip.address
}

output "domain_name" {
  description = "Domain configured for this deployment."
  value       = var.domain_name
}

output "app_url" {
  description = "Festival app URL (direct IP access)."
  value       = "http://${google_compute_address.vm_ip.address}:${var.app_port}"
}

output "domain_url_http" {
  description = "App URL after DNS + Nginx are configured."
  value       = "http://${var.domain_name}"
}

output "domain_url_https" {
  description = "App URL after DNS + Nginx + Certbot are configured."
  value       = "https://${var.domain_name}"
}

output "ssh_command" {
  description = "SSH into the VM."
  value       = "gcloud compute ssh ${google_compute_instance.vm.name} --zone ${var.zone} --project ${var.project_id}"
}

output "vm_name" {
  description = "VM instance name."
  value       = google_compute_instance.vm.name
}

output "zone" {
  description = "GCP zone."
  value       = var.zone
}

output "project_id" {
  description = "GCP project ID."
  value       = var.project_id
}
