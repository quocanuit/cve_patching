# Tạo S3 Bucket để lưu state file
resource "aws_s3_bucket" "terraform_state" {
  bucket = var.bucket_name
  tags = {
    Name        = var.bucket_name
    Environment = "dev"
  }
}

# Bật tính năng versioning cho S3 bucket (dùng để rollback khi cần)
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# DynamoDB Table để lock state (tránh xung đột hạ tầng)
# Serverless, NoSQL Database
resource "aws_dynamodb_table" "terraform_lock" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID" # Tên của Partition Key trong bảng DynamoDB

  # Chỉ định các thuộc tính được sử dụng trong lược đồ bảng
  attribute {
    name = "LockID"
    type = "S"
  }
  tags = {
    Name        = var.dynamodb_table_name
    Environment = "dev"
  }
}
