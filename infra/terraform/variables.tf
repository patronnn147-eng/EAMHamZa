variable "project_name" {
  description = "Short name prefixed onto every resource name."
  type        = string
  default     = "eam-prod"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "germanywestcentral"
}

variable "environment" {
  description = "Environment tag applied to every resource."
  type        = string
  default     = "production"
}

variable "admin_ip_ranges" {
  description = <<-EOT
    CIDR ranges allowed to reach the AKS API server (your admin IP(s) and
    the GitLab runner's egress IP, each as e.g. "203.0.113.5/32").
  EOT
  type = list(string)
}

variable "system_node_count" {
  description = "Fixed node count for the system node pool."
  type        = number
  default     = 2
}

variable "user_node_min_count" {
  description = "Minimum node count for the autoscaling user node pool."
  type        = number
  default     = 2
}

variable "user_node_max_count" {
  description = "Maximum node count for the autoscaling user node pool."
  type        = number
  default     = 4
}

variable "postgres_admin_login" {
  description = "Admin username for the Postgres Flexible Server."
  type        = string
  default     = "eamadmin"
}

variable "postgres_admin_password" {
  description = "Admin password for the Postgres Flexible Server. Set via TF_VAR_postgres_admin_password env var, never commit it."
  type        = string
  sensitive   = true
}
