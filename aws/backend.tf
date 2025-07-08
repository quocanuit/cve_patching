# terraform {
#   backend "s3" {
#     bucket         = "challenge8-state-storage"
#     key            = "jenkins/terraform.tfstate"
#     region         = "ap-southeast-2"
#     use_lockfile   = true
#     dynamodb_table = "challenge8-terraform-lock"
#   }
# } 