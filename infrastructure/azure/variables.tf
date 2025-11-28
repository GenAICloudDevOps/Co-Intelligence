variable "resource_group_name" {
  description = "Existing resource group name"
  type        = string
  default     = "1-eed7bd8e-playground-sandbox"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westus"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "cointelligence"
}

variable "db_username" {
  description = "Database admin username"
  type        = string
  default     = "cointelligence"
}
