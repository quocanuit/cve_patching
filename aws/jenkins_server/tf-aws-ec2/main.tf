# We'll be using publicly available modules for creating different services instead of resources
# https://registry.terraform.io/browse/modules?provider=aws

# Data sources to get VPC and subnet information from main infrastructure
data "aws_vpc" "main" {
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

data "aws_subnet" "public" {
  vpc_id = data.aws_vpc.main.id
  tags = {
    Name = "${var.project_name}-${element(split("-", var.availability_zone), 2)}-public"
  }
}

# SG
module "sg" {
  source = "terraform-aws-modules/security-group/aws"

  name        = var.jenkins_security_group
  description = "Security Group for Jenkins Server"
  vpc_id      = data.aws_vpc.main.id

  ingress_with_cidr_blocks = [
    {
      from_port   = 8080
      to_port     = 8080
      protocol    = "tcp"
      description = "JenkinsPort"
      cidr_blocks = "0.0.0.0/0"
    },
    {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      description = "HTTPS"
      cidr_blocks = "0.0.0.0/0"
    },
    {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      description = "HTTP"
      cidr_blocks = "0.0.0.0/0"
    },
    {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      description = "SSH"
      cidr_blocks = var.allowed_ssh_cidr
    },
    {
      from_port   = 9000
      to_port     = 9000
      protocol    = "tcp"
      description = "SonarQubePort"
      cidr_blocks = "0.0.0.0/0"
    }
  ]

  egress_with_cidr_blocks = [
    {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = "0.0.0.0/0"
    }
  ]

  tags = {
    Name = "jenkins-sg"
  }
}

# EC2
module "ec2_instance" {
  source = "terraform-aws-modules/ec2-instance/aws"

  name = var.jenkins_ec2_instance

  instance_type               = var.instance_type
  ami                         = "ami-078772dab3242ee11"
  key_name                    = "cve_patch_136_kp"
  monitoring                  = true
  vpc_security_group_ids      = [module.sg.security_group_id]
  subnet_id                   = data.aws_subnet.public.id
  associate_public_ip_address = true
  user_data                   = file("../scripts/user_data.sh")
  availability_zone           = data.aws_availability_zones.azs.names[0]

  root_block_device = {
    volume_size = 50
    volume_type = "gp2"
  }

  tags = {
    Name        = "Jenkins-Server-cve-patching"
    Terraform   = "true"
    Environment = "dev"
  }
}