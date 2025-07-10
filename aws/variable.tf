variable "aws_region" {
  description = "AWS region where the VPC will be created"
  type        = string
}

variable "project_name" {
  description = "Name of the project for VPBank Hackathon 2025"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones to use for subnets"
  type        = list(string)
}

variable "public_subnets" {
  description = "List of public subnet CIDR blocks"
  type        = list(string)
}

variable "private_subnets" {
  description = "List of private subnet CIDR blocks"
  type        = list(string)
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway"
  type        = bool
}

variable "bucket_name" {
  description = "Name of the S3 bucket to store Terraform state files"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "Value of the CIDR block allowed for SSH access to public instances"
  type        = string
}

variable "bucket_name_cve" {
  description = "Name of the S3 bucket to store CVE csv"
  type        = string
}
