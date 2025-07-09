variable "bucket_name" {
  description = "Name of the S3 bucket to store Terraform state files"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  type        = string
}