# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "${var.project_name}-igw"
  }
}

# Public Subnet
resource "aws_subnet" "public" {
  count                   = length(var.public_subnets) # Số lượng subnet sẽ tạo
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnets[count.index]     # CIDR block cho từng subnet, lấy từ mảng public_subnets
  availability_zone       = var.availability_zones[count.index] # AZ cho từng subnet, lấy từ mảng availability_zones
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.project_name}-${element(split("-", var.availability_zones[count.index]), 2)}-public"
  }
}

# Private Subnet
resource "aws_subnet" "private" {
  count             = length(var.private_subnets)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnets[count.index]
  availability_zone = var.availability_zones[count.index]
  tags = {
    Name = "${var.project_name}-${element(split("-", var.availability_zones[count.index]), 2)}-private"
  }
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? length(var.public_subnets) : 0 # Nếu bật NAT Gateway, tạo 1 EIP cho mỗi public subnet
  domain = "vpc"
  tags = {
    Name = "${var.project_name}-eip-${count.index + 1}"
  }
  depends_on = [aws_internet_gateway.main]
}

# NAT Gateways
resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? length(var.public_subnets) : 0 # Tạo NAT Gateway nếu bật
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags = {
    Name = "${var.project_name}-nat-gateway-${count.index + 1}"
  }
  depends_on = [aws_internet_gateway.main]
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"                  # Định tuyến tất cả lưu lượng ra ngoài Internet
    gateway_id = aws_internet_gateway.main.id # Thông qua Internet Gateway
  }
  tags = {
    Name = "${var.project_name}-public-route-table"
  }
}

# Private Route Table
resource "aws_route_table" "private" {
  count  = length(var.private_subnets) # Tạo bảng định tuyến cho mỗi private subnet
  vpc_id = aws_vpc.main.id
  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : [] # Nếu bật NAT Gateway thì thêm route ra ngoài Internet
    content {
      cidr_block     = "0.0.0.0/0"                          # Định tuyến tất cả lưu lượng ra ngoài Internet
      nat_gateway_id = aws_nat_gateway.main[count.index].id # Thông qua NAT Gateway tương ứng
    }
  }
  tags = {
    Name = "${var.project_name}-private-route-table-${count.index + 1}"
  }
}

# Public Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.public_subnets)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnets)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}