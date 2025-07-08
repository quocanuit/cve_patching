output "public_jenkins_sg_id" {
  description = "ID of Jenkins security group"
  value       = aws_security_group.public_jenkins_sg.id
}