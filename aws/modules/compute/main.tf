resource "aws_instance" "jenkins_server" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  key_name                    = var.key_name
  user_data                   = var.user_data_file
  security_groups             = [var.jenkins_security_group]
  associate_public_ip_address = true
  tags = {
    Name = "${var.project_name}-jenkins-server"
  }
}