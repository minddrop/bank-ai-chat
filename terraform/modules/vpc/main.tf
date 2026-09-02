# VPC Module - 3-Tier Enterprise Network Architecture (REQ-OPS-017 §1)
# Tokyo Region Multi-AZ (ap-northeast-1a, ap-northeast-1c)

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "bank-ai-vpc-${var.environment}"
    Environment = var.environment
    Compliance  = "FISC-APPI-FSA"
  }
}

# Internet Gateway for Tier 1 Public Subnets
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "bank-ai-igw-${var.environment}"
    Environment = var.environment
  }
}

# Tier 1: Public Subnets (ALB & NAT Gateways)
resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "public-subnet-${count.index == 0 ? "1a" : "1c"}"
    Tier        = "Public"
    Environment = var.environment
  }
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count  = length(var.public_subnet_cidrs)
  domain = "vpc"

  tags = {
    Name        = "bank-ai-nat-eip-${count.index == 0 ? "1a" : "1c"}"
    Environment = var.environment
  }
}

# Dual-AZ NAT Gateways
resource "aws_nat_gateway" "nat" {
  count         = length(var.public_subnet_cidrs)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name        = "bank-ai-nat-gw-${count.index == 0 ? "1a" : "1c"}"
    Environment = var.environment
  }

  depends_on = [aws_internet_gateway.igw]
}

# Tier 2: Private App Subnets (ECS Fargate Tasks)
resource "aws_subnet" "app" {
  count                   = length(var.app_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.app_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name        = "app-private-subnet-${count.index == 0 ? "1a" : "1c"}"
    Tier        = "Private-App"
    Environment = var.environment
  }
}

# Tier 3: Isolated Data Subnets (OpenSearch, KMS, Bedrock VPCE)
resource "aws_subnet" "data" {
  count                   = length(var.data_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.data_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name        = "data-isolated-subnet-${count.index == 0 ? "1a" : "1c"}"
    Tier        = "Isolated-Data"
    Environment = var.environment
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = "bank-ai-rt-public-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "app" {
  count  = length(aws_subnet.app)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat[count.index].id
  }

  tags = {
    Name        = "bank-ai-rt-app-${count.index == 0 ? "1a" : "1c"}"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "app" {
  count          = length(aws_subnet.app)
  subnet_id      = aws_subnet.app[count.index].id
  route_table_id = aws_route_table.app[count.index].id
}

# Isolated Route Table (No Internet Route)
resource "aws_route_table" "data" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "bank-ai-rt-data-isolated-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "data" {
  count          = length(aws_subnet.data)
  subnet_id      = aws_subnet.data[count.index].id
  route_table_id = aws_route_table.data.id
}

# Gateway VPC Endpoint for Amazon S3 (Free & Secure Data Ingestion)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.ap-northeast-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat([aws_route_table.public.id, aws_route_table.data.id], aws_route_table.app[*].id)

  tags = {
    Name        = "bank-ai-vpce-s3-${var.environment}"
    Environment = var.environment
  }
}
