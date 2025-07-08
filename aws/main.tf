terraform {
  required_version = ">= 1.12.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

module "vpc" {
  source             = "./modules/vpc"
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  public_subnets     = var.public_subnets
  private_subnets    = var.private_subnets
  enable_nat_gateway = var.enable_nat_gateway
  project_name       = var.project_name
}

module "backend" {
  source              = "./modules/storage/backend"
  bucket_name         = var.bucket_name
  dynamodb_table_name = var.dynamodb_table_name
}

module "security_group" {
  source           = "./modules/security_group"
  project_name     = var.project_name
  vpc_id           = module.vpc.vpc_id
  allowed_ssh_cidr = var.allowed_ssh_cidr
}

data "template_file" "user_data" {
  template = file("./user_data.sh")
}


module "jenkins_server" {
  source                 = "./modules/compute"
  project_name           = var.project_name
  ami_id                 = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  user_data_file         = data.template_file.user_data.rendered
  subnet_id              = module.vpc.public_subnets[0]
  jenkins_security_group = module.security_group.public_jenkins_sg_id
}