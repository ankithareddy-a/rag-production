variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project prefix for naming resources"
  type        = string
  default     = "rag-production"
}
