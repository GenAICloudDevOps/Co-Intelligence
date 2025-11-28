output "resource_group" {
  value = local.resource_group_name
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "db_host" {
  value = azurerm_postgresql_flexible_server.postgres.fqdn
}

output "db_name" {
  value = azurerm_postgresql_flexible_server_database.db.name
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

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  value = azurerm_container_registry.acr.admin_username
}

output "acr_admin_password" {
  value     = azurerm_container_registry.acr.admin_password
  sensitive = true
}

output "storage_account" {
  value = azurerm_storage_account.storage.name
}

output "code_executor_url" {
  value = "https://${azurerm_linux_function_app.code_executor.default_hostname}/api/execute"
}

output "storage_key" {
  value     = azurerm_storage_account.storage.primary_access_key
  sensitive = true
}
