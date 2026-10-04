# Remote state so GitHub Actions and your laptop share one state file
terraform {
  backend "azurerm" {
    resource_group_name  = "koalatech-tfstate-rg"
    storage_account_name = "koalatechtfstatesahan"
    container_name       = "tfstate"
    key                  = "sit722-cost-aware.tfstate"
  }
}
