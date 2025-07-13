terraform {
  backend "s3" {
    bucket = "project-state-storage"
    key    = "jenkins/terraform.tfstate"
    region = "ap-southeast-2"
  }
}