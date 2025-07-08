output "jenkins_public_ip" {
  description = "Public IP of Jenkins EC2 instance"
  value       = aws_instance.jenkins_server.public_ip
}