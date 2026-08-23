output "vm_external_ip" {
  description = "Static public IP of the VM."
  value       = google_compute_address.vm_ip.address
}

output "app_url" {
  description = "Festival app URL."
  value       = "http://${google_compute_address.vm_ip.address}:${var.app_port}"
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
