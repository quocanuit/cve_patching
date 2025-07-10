terraform {
  backend "s3" {
    bucket         = "project-state-storage"
    key            = "state/terraform.tfstate"
    region         = "ap-southeast-2"
    use_lockfile   = true
    dynamodb_table = "project-terraform-lock"
  }
} 