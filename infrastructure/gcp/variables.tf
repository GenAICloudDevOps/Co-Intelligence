variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-east1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-east1-b"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "cointelligence"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "co-intelligence"
}
