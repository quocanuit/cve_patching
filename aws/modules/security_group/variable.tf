variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH access to public instances"
  type        = string
  default     = "10.0.0.0/16"
}

variable "vpc_id" {
  description = "The ID of the VPC where the security group will be created"
  type        = string
}