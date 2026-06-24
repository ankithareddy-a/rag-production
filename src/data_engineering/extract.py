import pandas as pd
from pathlib import Path

DEFAULT_RAW_DIR = Path('/tmp/rag_production/raw')


def main(raw_dir: str | Path = DEFAULT_RAW_DIR) -> Path:
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_file = raw_dir / 'orders.csv'
    sample = [
        {"id": 1, "customer_id": 10, "total_amount": 100, "created_at": "2026-06-01"},
        {"id": 2, "customer_id": 11, "total_amount": 200, "created_at": "2026-06-02"},
        {"id": 3, "customer_id": 10, "total_amount": 300, "created_at": "2026-06-03"},
    ]
    pd.DataFrame(sample).to_csv(output_file, index=False)
    print(f"Extracted {len(sample)} records to {output_file}")
    return output_file


if __name__ == '__main__':
    main()
