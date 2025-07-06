data "aws_region" "current" {}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "project_name" {
  description = "Name of the project for VPBank Hackathon 2025"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones"
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
  default     = true
}

