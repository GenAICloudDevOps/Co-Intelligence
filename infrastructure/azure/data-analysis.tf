# Data Analysis Infrastructure for Azure
# Logic Apps + Data Factory + Synapse SQL

# Storage container for data
resource "azurerm_storage_container" "data_analysis" {
  name                  = "data-analysis"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Synapse workspace for SQL analytics
resource "azurerm_synapse_workspace" "data_analysis" {
  name                                 = "${var.project_name}-synapse"
  resource_group_name                  = azurerm_resource_group.main.name
  location                             = azurerm_resource_group.main.location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.data_analysis.id
  sql_administrator_login              = "sqladmin"
  sql_administrator_login_password     = random_password.synapse.result

  identity {
    type = "SystemAssigned"
  }

  tags = {
    app = "co-intelligence"
  }
}

resource "random_password" "synapse" {
  length  = 16
  special = true
}

# Data Lake filesystem for Synapse
resource "azurerm_storage_data_lake_gen2_filesystem" "data_analysis" {
  name               = "synapse"
  storage_account_id = azurerm_storage_account.main.id
}

# Synapse SQL Pool (serverless is default, no dedicated pool needed for sandbox)
resource "azurerm_synapse_sql_pool" "data_analysis" {
  count                = 0  # Use serverless SQL by default (no cost)
  name                 = "dataanalysis"
  synapse_workspace_id = azurerm_synapse_workspace.data_analysis.id
  sku_name             = "DW100c"
  create_mode          = "Default"
}

# Logic App for pipeline orchestration
resource "azurerm_logic_app_workflow" "data_analysis" {
  name                = "${var.project_name}-data-analysis-pipeline"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    app = "co-intelligence"
  }
}

# Logic App HTTP trigger
resource "azurerm_logic_app_trigger_http_request" "data_analysis" {
  name         = "pipeline-trigger"
  logic_app_id = azurerm_logic_app_workflow.data_analysis.id

  schema = <<SCHEMA
{
  "type": "object",
  "properties": {
    "user_id": {"type": "integer"},
    "dataset_id": {"type": "integer"},
    "dataset_name": {"type": "string"},
    "glue_table": {"type": "string"},
    "spec_s3_uri": {"type": "string"},
    "curated_s3_uri": {"type": "string"},
    "source": {"type": "object"}
  }
}
SCHEMA
}

# Data Factory for ETL
resource "azurerm_data_factory" "data_analysis" {
  name                = "${var.project_name}-data-analysis-adf"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type = "SystemAssigned"
  }

  tags = {
    app = "co-intelligence"
  }
}

# Data Factory linked service for blob storage
resource "azurerm_data_factory_linked_service_azure_blob_storage" "data_analysis" {
  name              = "BlobStorage"
  data_factory_id   = azurerm_data_factory.data_analysis.id
  connection_string = azurerm_storage_account.main.primary_connection_string
}

# Role assignment for Data Factory to access storage
resource "azurerm_role_assignment" "adf_storage" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.data_analysis.identity[0].principal_id
}

# Role assignment for Synapse to access storage
resource "azurerm_role_assignment" "synapse_storage" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_synapse_workspace.data_analysis.identity[0].principal_id
}

# Outputs
output "data_analysis_logic_app_url" {
  value     = azurerm_logic_app_trigger_http_request.data_analysis.callback_url
  sensitive = true
}

output "data_analysis_synapse_endpoint" {
  value = azurerm_synapse_workspace.data_analysis.connectivity_endpoints["sql"]
}

output "data_analysis_storage_container" {
  value = azurerm_storage_container.data_analysis.name
}
