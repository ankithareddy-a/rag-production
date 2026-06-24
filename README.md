# rag-production

A production-grade data engineering repository demonstrating:
- Data modeling with dbt
- Pipeline orchestration with Apache Airflow
- Cloud infrastructure provisioning with Terraform (AWS)
- Data quality testing with Great Expectations

## Architecture

1. **Extraction**: ingestion from raw sources into landing storage
2. **Transformation**: dbt models for staging and marts
3. **Orchestration**: Airflow DAG orchestrates extraction, transformation, and validation
4. **Infrastructure**: AWS resources provisioned with Terraform
5. **Quality**: Great Expectations validates source and transformed data

## Getting Started

1. Install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure AWS credentials and dbt profile using `dbt/profiles.yml.example`.
3. Initialize Airflow and run the DAG with Docker Compose:
   ```bash
   docker compose up -d
   ```
4. Run tests:
   ```bash
   pytest
   ```

## Repository Structure

- `airflow/`: DAGs and orchestration configuration
- `dbt/`: dbt project with staging and mart models
- `terraform/`: AWS infrastructure as code
- `great_expectations/`: data quality suites
- `src/`: ingestion, transform, load helpers
- `tests/`: unit and integration tests

## Cloud

This project uses AWS as the default cloud provider. Terraform provisions:
- Amazon S3 bucket for raw and curated storage
- Amazon RDS PostgreSQL instance for analytics
- IAM resources for secure access
