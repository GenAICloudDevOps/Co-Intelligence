terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Random suffix for unique names
resource "random_id" "suffix" {
  byte_length = 4
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.app_name}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.app_name}-subnet"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Cloud Router & NAT for private GKE nodes
resource "google_compute_router" "router" {
  name    = "${var.app_name}-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.app_name}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# GKE Cluster (Standard, not Autopilot)
resource "google_container_cluster" "gke" {
  name     = "${var.app_name}-gke"
  location = var.zone

  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "primary" {
  name       = "${var.app_name}-node-pool"
  location   = var.zone
  cluster    = google_container_cluster.gke.name
  node_count = 2

  autoscaling {
    min_node_count = 2
    max_node_count = 3
  }

  node_config {
    machine_type = "e2-medium"
    disk_size_gb = 50

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      app = var.app_name
    }
  }
}

# Cloud SQL PostgreSQL
resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "google_sql_database_instance" "postgres" {
  name             = "${var.app_name}-db-${random_id.suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-custom-2-8192" # 2 vCPU, 8GB RAM
    disk_size         = 50
    disk_type         = "PD_SSD"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled = true
    }
  }

  deletion_protection = false

  depends_on = [google_service_networking_connection.private_vpc]
}

resource "google_sql_database" "database" {
  name     = "cointelligence"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "user" {
  name     = var.db_username
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# Private VPC connection for Cloud SQL
resource "google_compute_global_address" "private_ip" {
  name          = "${var.app_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
  depends_on              = [google_project_service.apis["servicenetworking.googleapis.com"]]
}

# Artifact Registry
resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "${var.app_name}-backend"
  format        = "DOCKER"
}

resource "google_artifact_registry_repository" "frontend" {
  location      = var.region
  repository_id = "${var.app_name}-frontend"
  format        = "DOCKER"
}

# Cloud Storage
resource "google_storage_bucket" "bucket" {
  name          = "${var.app_name}-${random_id.suffix.hex}"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

# Secret Manager
resource "random_password" "secret_key" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.app_name}-db-password"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "${var.app_name}-secret-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "secret_key" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = random_password.secret_key.result
}

# Cloud Function for code execution
resource "google_storage_bucket" "function_bucket" {
  name          = "${var.app_name}-functions-${random_id.suffix.hex}"
  location      = var.region
  force_destroy = true
}

# Cloud Function source code
data "archive_file" "function_zip" {
  type        = "zip"
  output_path = "${path.module}/function.zip"
  source {
    content  = <<-EOF
import json
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
import math, datetime, random, statistics, re, collections, itertools
import string, decimal, fractions, uuid, hashlib, base64, textwrap

def execute_code(request):
    request_json = request.get_json(silent=True)
    code = request_json.get('code', '') if request_json else ''
    if not code:
        return json.dumps({'error': 'No code provided'}), 400
    
    stdout_capture, stderr_capture = io.StringIO(), io.StringIO()
    try:
        allowed = {'math','json','datetime','random','statistics','re','collections','itertools','string','decimal','fractions','uuid','hashlib','base64','textwrap'}
        def safe_import(name, *a, **k):
            if name in allowed: return __import__(name, *a, **k)
            raise ImportError(f"Module '{name}' not allowed")
        
        safe_globals = {
            '__builtins__': {'__import__': safe_import, 'print': print, 'len': len, 'range': range,
                'str': str, 'int': int, 'float': float, 'list': list, 'dict': dict, 'set': set,
                'tuple': tuple, 'sum': sum, 'max': max, 'min': min, 'abs': abs, 'round': round,
                'sorted': sorted, 'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
                'any': any, 'all': all, 'bool': bool, 'bytes': bytes, 'chr': chr, 'ord': ord,
                'hex': hex, 'oct': oct, 'bin': bin, 'pow': pow, 'divmod': divmod,
                'isinstance': isinstance, 'type': type},
            'math': math, 'json': json, 'datetime': datetime, 'random': random,
            'statistics': statistics, 're': re, 'collections': collections, 'itertools': itertools,
            'string': string, 'decimal': decimal, 'fractions': fractions, 'uuid': uuid,
            'hashlib': hashlib, 'base64': base64, 'textwrap': textwrap,
        }
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, safe_globals)
        return json.dumps({'output': stdout_capture.getvalue(), 'errors': stderr_capture.getvalue() or None, 'success': True})
    except Exception as e:
        return json.dumps({'output': stdout_capture.getvalue(), 'errors': f"{type(e).__name__}: {e}\n{traceback.format_exc()}", 'success': False})
EOF
    filename = "main.py"
  }
}

resource "google_storage_bucket_object" "function_source" {
  name   = "function-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_zip.output_path
}

resource "google_cloudfunctions_function" "code_executor" {
  name        = "${var.app_name}-code-executor"
  description = "Secure Python code execution sandbox"
  runtime     = "python311"
  region      = var.region

  available_memory_mb   = 512
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_source.name
  trigger_http          = true
  entry_point           = "execute_code"
  timeout               = 30

  depends_on = [google_project_service.apis["cloudfunctions.googleapis.com"]]
}

# IAM for GKE to invoke Cloud Function
resource "google_cloudfunctions_function_iam_member" "invoker" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.code_executor.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.gke_sa.email}"
}

resource "google_service_account" "gke_sa" {
  account_id   = "${var.app_name}-gke-sa"
  display_name = "GKE Service Account for Co-Intelligence"
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}
