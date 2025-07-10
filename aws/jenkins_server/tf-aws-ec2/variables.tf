variable "aws_region" {
    description = "The region where the infrastructure should be deployed to"
    type = string
}

variable "aws_account_id" {
    description = "AWS Account ID"
    type = string
}

variable "backend_jenkins_bucket" {
    description = "S3 bucket where jenkins terraform state file will be stored"
    type = string
}

variable "backend_jenkins_bucket_key" {
    description = "bucket key for the jenkins terraform state file"
    type = string
}

variable "project_name" {
  description = "Name of the project (must match the main infrastructure)"
  type        = string
}

variable "availability_zone" {
  description = "Availability zone where Jenkins server will be deployed"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH access"
  type        = string
}

variable "instance_type" {
  description = "Instance Type"
  type        = string
}

variable "jenkins_security_group" {
  description = "Security Group name for Jenkins Server"
  type        = string
}

variable "jenkins_ec2_instance" {
  description = "Jenkins EC2 instance name"
  type        = string
}