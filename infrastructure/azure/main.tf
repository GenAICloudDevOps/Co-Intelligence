terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
  skip_provider_registration = true
}

data "azurerm_client_config" "current" {}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "random_password" "secret_key" {
  length  = 32
  special = false
}

# Hardcode resource group (sandbox can't read it via data source)
locals {
  resource_group_name = var.resource_group_name
  location            = var.location
}

# Virtual Network
resource "azurerm_virtual_network" "vnet" {
  name                = "${var.app_name}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = local.location
  resource_group_name = local.resource_group_name
}

resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = local.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "db" {
  name                 = "db-subnet"
  resource_group_name  = local.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.2.0/24"]
  service_endpoints    = ["Microsoft.Storage"]

  delegation {
    name = "fs"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgres" {
  name                = "${var.app_name}.postgres.database.azure.com"
  resource_group_name = local.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "${var.app_name}-postgres-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
  resource_group_name   = local.resource_group_name
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${var.app_name}-aks"
  location            = local.location
  resource_group_name = local.resource_group_name
  dns_prefix          = var.app_name

  default_node_pool {
    name                = "default"
    node_count          = 2
    vm_size             = "Standard_B2s"
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 3
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    service_cidr   = "10.1.0.0/16"
    dns_service_ip = "10.1.0.10"
  }
}

# PostgreSQL Flexible Server (public access for sandbox)
resource "azurerm_postgresql_flexible_server" "postgres" {
  name                   = "${var.app_name}-db-${random_id.suffix.hex}"
  resource_group_name    = local.resource_group_name
  location               = local.location
  version                = "15"
  administrator_login    = var.db_username
  administrator_password = random_password.db_password.result
  storage_mb             = 32768
  sku_name               = "B_Standard_B2ms"

  public_network_access_enabled = true
}

# Firewall rule to allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.postgres.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = "cointelligence"
  server_id = azurerm_postgresql_flexible_server.postgres.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Container Registry
resource "azurerm_container_registry" "acr" {
  name                = "${var.app_name}acr${random_id.suffix.hex}"
  resource_group_name = local.resource_group_name
  location            = local.location
  sku                 = "Basic"
  admin_enabled       = true
}

# Note: Role assignment removed - sandbox doesn't have permission
# AKS will use ACR admin credentials instead

# Storage Account
resource "azurerm_storage_account" "storage" {
  name                     = "${var.app_name}st${random_id.suffix.hex}"
  resource_group_name      = local.resource_group_name
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "uploads" {
  name                  = "uploads"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

# Azure Function for Code Execution
resource "azurerm_service_plan" "functions" {
  name                = "${var.app_name}-func-plan"
  resource_group_name = local.resource_group_name
  location            = local.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "code_executor" {
  name                = "${var.app_name}-executor-${random_id.suffix.hex}"
  resource_group_name = local.resource_group_name
  location            = local.location
  service_plan_id     = azurerm_service_plan.functions.id

  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
  }
}

# Key Vault
resource "azurerm_key_vault" "kv" {
  name                = "coikv${random_id.suffix.hex}"
  location            = local.location
  resource_group_name = local.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
  }
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = random_password.db_password.result
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "secret_key" {
  name         = "secret-key"
  value        = random_password.secret_key.result
  key_vault_id = azurerm_key_vault.kv.id
}
