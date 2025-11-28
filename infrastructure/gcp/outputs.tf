output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "gke_cluster_name" {
  value = google_container_cluster.gke.name
}

output "gke_zone" {
  value = var.zone
}

output "db_host" {
  value = google_sql_database_instance.postgres.private_ip_address
}

output "db_name" {
  value = google_sql_database.database.name
}

output "db_username" {
  value = var.db_username
}

output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "secret_key" {
  value     = random_password.secret_key.result
  sensitive = true
}

output "backend_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}"
}

output "frontend_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.frontend.repository_id}"
}

output "bucket_name" {
  value = google_storage_bucket.bucket.name
}

output "function_bucket" {
  value = google_storage_bucket.function_bucket.name
}
