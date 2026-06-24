# Architecture

This repository is designed to demonstrate modern data engineering principles.

## Components

- **Extraction**: simple CSV ingestion from raw sources
- **Transformation**: data normalization for business use
- **Modeling**: dbt staging and mart models
- **Orchestration**: Airflow DAG runs extract, transform, validate
- **Infrastructure**: Terraform provisions AWS S3 and RDS
- **Data Quality**: Great Expectations validates curated output
