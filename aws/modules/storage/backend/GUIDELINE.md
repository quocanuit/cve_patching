# Tài liệu hướng dẫn tạo Terraform Remote State với S3 và DynamoDB
## Mục tiêu

- Chuyển đổi Terraform state từ **local sang remote backend** trên AWS S3, đồng thời sử dụng DynamoDB để lock state **tránh xung đột** khi nhiều người cùng thao tác.

##  Yêu cầu:

- Terraform đã cài (>= 1.5+ hoặc 1.6+)
- AWS CLI đã cấu hình
- Quyền tạo S3 + DynamoDB

## Các bước chi tiết

###  Bước 1: Tạo S3 Bucket và DynamoDB Table (backend resource)

 - File main.tf

```terraform
resource "aws_s3_bucket" "tfstate" {
  bucket = var.bucket_name

  versioning {
    enabled = true
  }

  tags = {
    Name = var.bucket_name
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = var.dynamodb_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = var.dynamodb_table_name
  }
}
```

 - File variable.tf

```terraform
variable "bucket_name" {
  description = "Name of the S3 bucket to store Terraform state files"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  type        = string
}
```

### Bước 2: Khai báo s3 ở root folder

- Khai báo các tài nguyên S3 ở module con vào fil  `main.tf` ở root

```terraform
module "backend" {
  source              = "./modules/storage/backend"
  bucket_name         = var.bucket_name
  dynamodb_table_name = var.dynamodb_table_name
}
```

- Khai báo các biến S3 vào file `variable.tf` ở root

```terraform
variable "bucket_name" {
  description = "Name of the S3 bucket to store Terraform state files"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  type        = string
}
```

- Khai báo các giá trị của S3 vào file `terraform.tfvars`

```terraform
bucket_name         = "challenge8-state-storage"
dynamodb_table_name = "challenge8-terraform-lock"
```

### Bước 3: Khai báo backend.tf ở root folder

```terraform
terraform {
  backend "s3" {
    bucket         = "challenge8-state-storage"
    key            = "jenkins/terraform.tfstate"
    region         = "ap-southeast-2"
    use_lockfile   = true
    dynamodb_table = "challenge8-terraform-lock"
  }
} 
```

- Từ Terraform 1.6+ ➔ dùng `use_lock_table = true` thay cho dynamodb_table.

### Bước 4: Thứ tự thực hiện lệnh

- Trước tiên, cần vào file `backend.tf ` ở root module để **xóa** hoặc **comment** tạm thời (để dùng local state trước)

- Tiếp theo, dùng lệnh:
    - `terraform init` để khởi tạo local state
    - `terraform validate` để kiểm tra cú pháp
    - `terraform plan` để xem các thay đổi sẽ áp dụng
    - `terraform apply` để áp dụng các tài nguyên

- Sau khi đã tạo thành công, dùng lệnh `terraform init -migrate-state` để chuyển state từ local sang S3.

### Bước 4: Kiểm tra kết quả:

- Truy cập AWS S3 ➔ Kiểm tra file state `jenkins/terraform.tfstate`

- Truy cập DynamoDB ➔ Kiểm tra lock table (có thể trống khi không ai thao tác)

## Các lỗi thường gặp và cách fix

| Lỗi                                  | Nguyên nhân                          | Cách fix                                 |
| ------------------------------------ | ------------------------------------ | ---------------------------------------- |
| `NoSuchBucket`                       | S3 bucket chưa tạo hoặc đã bị xóa    | Phải **tạo bucket trước**                |
| `ResourceNotFoundException` DynamoDB | Table DynamoDB chưa tạo hoặc sai tên | Tạo table hoặc sửa đúng tên              |
| Không xóa được S3 bucket             | Bucket còn file hoặc version         | Xóa toàn bộ **objects + versions** trước |
| Lock không release                   | DynamoDB table bị xóa mất            | Dùng `terraform force-unlock <LockID>`   |


## Lưu ý

- Không thể destroy khi backend trỏ vào S3 đã bị xóa ➔ phải xóa `backend.tf `+ .terraform để quay về local backend.
- Nên enable versioning trên S3 để rollback nếu cần.
- Có thể dùng terraform state list để kiểm tra các resource trong state.

