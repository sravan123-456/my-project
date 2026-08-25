variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region. us-central1 is free-tier eligible for e2-micro."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone."
  type        = string
  default     = "us-central1-a"
}

variable "vm_name" {
  description = "VM instance name."
  type        = string
  default     = "vinayaka-festival"
}

variable "machine_type" {
  description = "Smallest/cheapest machine type."
  type        = string
  default     = "e2-micro"
}

variable "boot_disk_size_gb" {
  description = "Boot disk size in GB."
  type        = number
  default     = 10
}

variable "app_port" {
  description = "Port exposed for the festival app."
  type        = number
  default     = 8080
}

variable "secret_key" {
  description = "Flask SECRET_KEY for the application."
  type        = string
  sensitive   = true
}

variable "github_repo_url" {
  description = "Git repository URL to clone on the VM."
  type        = string
  default     = "https://github.com/sravan123-456/my-project.git"
}

variable "ssh_user" {
  description = "Linux user for SSH access."
  type        = string
  default     = "vandana"
}

variable "domain_name" {
  description = "Public domain name for the festival app (DNS A record target is the static IP)."
  type        = string
  default     = "indukuru.online"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access (full openssh format)."
  type        = string
}
