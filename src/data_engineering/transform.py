import pandas as pd
from pathlib import Path

DEFAULT_RAW_DIR = Path('/tmp/rag_production/raw')
DEFAULT_CURATED_DIR = Path('/tmp/rag_production/curated')


def main(raw_dir: str | Path = DEFAULT_RAW_DIR, curated_dir: str | Path = DEFAULT_CURATED_DIR) -> Path:
    raw_dir = Path(raw_dir)
    curated_dir = Path(curated_dir)
    input_file = raw_dir / 'orders.csv'
    curated_dir.mkdir(parents=True, exist_ok=True)
    output_file = curated_dir / 'orders_transformed.csv'

    df = pd.read_csv(input_file)
    df['amount'] = df['total_amount'].astype(int)
    df.to_csv(output_file, index=False)
    print(f"Transformed data written to {output_file}")
    return output_file


if __name__ == '__main__':
    main()
