# Deployment

1. Configure AWS credentials and run Terraform:
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```

2. Configure dbt profiles from `dbt/profiles.yml.example`.
3. Start local orchestration with Docker Compose:
   ```bash
   docker compose up -d
   ```

4. Monitor Airflow at `http://localhost:8080`.
