resource "aws_s3_bucket" "raw_data" {
  bucket = "${var.project_name}-raw-data-${random_id.bucket_id.hex}"
  acl    = "private"
}

resource "aws_s3_bucket" "curated_data" {
  bucket = "${var.project_name}-curated-data-${random_id.bucket_id.hex}"
  acl    = "private"
}

resource "aws_db_instance" "analytics" {
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.t3.micro"
  name                 = "analytics"
  username             = "dbt_user"
  password             = "dbt_pass123!"
  parameter_group_name = "default.postgres15"
  skip_final_snapshot  = true
}

resource "random_id" "bucket_id" {
  byte_length = 4
}
