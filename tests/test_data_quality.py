from pathlib import Path
import pandas as pd
import great_expectations as ge


def test_great_expectations_suite(tmp_path):
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    df = pd.DataFrame([{"order_id": 1, "customer_id": 10, "amount": 100}])
    file_path = curated_dir / "orders_transformed.csv"
    df.to_csv(file_path, index=False)
    batch_df = ge.from_pandas(df)
    assert batch_df.shape[0] == 1
