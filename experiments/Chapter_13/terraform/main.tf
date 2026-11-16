# Additional cloud reference for Chapter 13. No credentials belong in this file.
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = ">= 2.0.0, < 3.0.0"
    }
  }
}

# Credentials are read from MONGODB_ATLAS_PUBLIC_KEY / MONGODB_ATLAS_PRIVATE_KEY.
provider "mongodbatlas" {}

variable "atlas_org_id" {
  type        = string
  description = "Atlas organization in which to create a separate exercise project."
}
variable "atlas_user_password" {
  type      = string
  sensitive = true
}
variable "allowed_ip" {
  type        = string
  description = "Your public IPv4 address, without /32. Only this client IP is permitted."
  validation {
    condition     = can(cidrhost("${var.allowed_ip}/32", 0)) && var.allowed_ip != "0.0.0.0"
    error_message = "Supply your specific public IPv4 address."
  }
}
variable "atlas_region" {
  type    = string
  default = "AP_SOUTH_1"
}

resource "mongodbatlas_project" "exercise13" {
  name   = "Exercise13-Containers-Cloud"
  org_id = var.atlas_org_id
}

# Provider v2 tenant-cluster syntax. M0 version/storage/replica count are Atlas-managed.
resource "mongodbatlas_advanced_cluster" "free" {
  project_id   = mongodbatlas_project.exercise13.id
  name         = "exercise13-free"
  cluster_type = "REPLICASET"
  replication_specs = [{
    region_configs = [{
      provider_name         = "TENANT"
      backing_provider_name = "AWS"
      region_name           = var.atlas_region
      priority              = 7
      electable_specs       = { instance_size = "M0" }
    }]
  }]
}

resource "mongodbatlas_database_user" "lab" {
  project_id         = mongodbatlas_project.exercise13.id
  username           = "exercise13_user"
  password           = var.atlas_user_password
  auth_database_name = "admin"
  roles {
    role_name     = "readWrite"
    database_name = "exercise13"
  }
}

resource "mongodbatlas_project_ip_access_list" "client" {
  project_id = mongodbatlas_project.exercise13.id
  ip_address = var.allowed_ip
  comment    = "Exercise 13 specific client address"
}

output "project_id" {
  value = mongodbatlas_project.exercise13.id
}
output "cluster_name" {
  value = mongodbatlas_advanced_cluster.free.name
}
# Obtain the SRV connection string from Atlas Connect after deployment.
# Do not concatenate mongodb+srv:// with a value already containing that prefix.
