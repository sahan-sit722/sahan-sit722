location            = "Australia East"
resource_group_name = "sit722-cost-aware-rg"

acr_name = "sit722costawareacr"

storage_account_name = "sit722costawarest"

aks_cluster_name = "sit722-cost-aware-aks"
aks_dns_prefix   = "sit722-cost-aware"

aks_node_count   = 5
aks_node_vm_size = "Standard_D2s_v3"

environment = "development"

tags = {
  Project     = "Cost Aware DevOps"
  ManagedBy   = "Terraform"
  Practical   = "10.3HD"
  Environment = "Development"
}