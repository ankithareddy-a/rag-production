output "raw_bucket" {
  value = aws_s3_bucket.raw_data.bucket
}

output "curated_bucket" {
  value = aws_s3_bucket.curated_data.bucket
}

output "analytics_rds_endpoint" {
  value = aws_db_instance.analytics.endpoint
}
