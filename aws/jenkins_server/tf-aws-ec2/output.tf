output "jenkins_instance_id" {
  description = "Jenkins EC2 instance ID"
  value       = module.ec2_instance.id
}

output "jenkins_public_ip" {
  description = "Jenkins server public IP address"
  value       = module.ec2_instance.public_ip
}

output "jenkins_private_ip" {
  description = "Jenkins server private IP address"
  value       = module.ec2_instance.private_ip
}

output "jenkins_security_group_id" {
  description = "Jenkins security group ID"
  value       = module.sg.security_group_id
}

output "jenkins_url" {
  description = "Jenkins server URL"
  value       = "http://${module.ec2_instance.public_ip}:8080"
}

output "vpc_id" {
  description = "VPC ID where Jenkins is deployed"
  value       = data.aws_vpc.main.id
}

output "subnet_id" {
  description = "Subnet ID where Jenkins is deployed"
  value       = data.aws_subnet.public.id
}