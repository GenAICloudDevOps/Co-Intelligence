# Data Analysis Infrastructure for GCP
# BigQuery + Cloud Storage (sandbox-compatible)
# Note: Cloud Workflows and IAM bindings not available in sandbox

# BigQuery Dataset
resource "google_bigquery_dataset" "data_analysis" {
  dataset_id    = "co_intelligence_data_analysis"
  friendly_name = "Co-Intelligence Data Analysis"
  description   = "Dataset for Agentic Data Analysis app"
  location      = var.region

  labels = {
    app = "co-intelligence"
  }
}

# Cloud Storage bucket for data
resource "google_storage_bucket" "data_analysis" {
  name          = "${var.project_id}-data-analysis"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Output values
output "data_analysis_bigquery_dataset" {
  value = google_bigquery_dataset.data_analysis.dataset_id
}

output "data_analysis_storage_bucket" {
  value = google_storage_bucket.data_analysis.name
}
