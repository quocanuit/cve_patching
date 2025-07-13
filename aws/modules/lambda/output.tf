output "lambda_function_name" {
  description = "Lambda Function name"
  value       = aws_lambda_function.func.function_name
}

output "lambda_function_arn" {
  description = "Lambda Function ARN"
  value       = aws_lambda_function.func.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda Function"
  value       = aws_iam_role.iam_for_lambda.arn
}

output "s3_bucket_name" {
  description = "bucket name"
  value       = data.aws_s3_bucket.bucket.bucket
}

output "bucket_notification_id" {
  description = "bucket notification ID"
  value       = aws_s3_bucket_notification.bucket_notification.id
}