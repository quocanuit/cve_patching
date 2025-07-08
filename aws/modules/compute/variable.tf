variable "ami_id" {
  description = "AMI ID for the Jenkins server"
  type        = string
}

variable "instance_type" {
  description = "Instance type for the Jenkins server"
  type        = string
}

variable "key_name" {
  description = "Key pair name for SSH access to the Jenkins server"
  type        = string
}

variable "project_name" {
  description = "Name of the project for VPBank Hackathon 2025"
  type        = string
}

variable "user_data_file" {
  description = "User data script for the Jenkins server"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID where the Jenkins server will be launched"
  type        = string
}

variable "jenkins_security_group" {
  description = "value of the security group for the Jenkins server"
  type        = string
}