terraform {
  backend "s3" {
    bucket = "terraform-cve-patching"
    key    = "jenkins/terraform.tfstate"
    region = "ap-southeast-2"
  }
}