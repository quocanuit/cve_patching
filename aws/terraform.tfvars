aws_region         = "ap-southeast-2"
project_name       = "hackathon-challenge8"
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["ap-southeast-2a", "ap-southeast-2b"]
public_subnets     = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnets    = ["10.0.10.0/24", "10.0.20.0/24"]
enable_nat_gateway = true
