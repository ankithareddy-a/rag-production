from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def extract():
    subprocess.run(["python", "/app/src/data_engineering/extract.py"], check=True)


def transform():
    subprocess.run(["python", "/app/src/data_engineering/transform.py"], check=True)


def validate():
    subprocess.run(["python", "/app/src/data_engineering/validate.py"], check=True)

with DAG(
    dag_id="data_engineering_pipeline",
    schedule_interval="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["production", "data-engineering"],
) as dag:

    extract_task = PythonOperator(task_id="extract", python_callable=extract)
    transform_task = PythonOperator(task_id="transform", python_callable=transform)
    validate_task = PythonOperator(task_id="validate", python_callable=validate)

    extract_task >> transform_task >> validate_task
