import great_expectations as ge
import pandas as pd
from pathlib import Path

DEFAULT_CURATED_DIR = Path('/tmp/rag_production/curated')
DEFAULT_EXPECTATION_SUITE = 'order_table_suite'


def main(curated_dir: str | Path = DEFAULT_CURATED_DIR, expectation_suite_name: str = DEFAULT_EXPECTATION_SUITE) -> bool:
    curated_dir = Path(curated_dir)
    input_file = curated_dir / 'orders_transformed.csv'
    batch_df = ge.from_pandas(pd.read_csv(input_file))
    context = ge.get_context(project_config_file_path='great_expectations/great_expectations.yml')
    validator = context.get_validator(
        batch=ge.Batch(data=batch_df),
        expectation_suite_name=expectation_suite_name,
    )
    result = validator.validate()
    if not result.success:
        raise SystemExit('Data quality validation failed')
    print('Data quality validation succeeded')
    return True


if __name__ == '__main__':
    main()
