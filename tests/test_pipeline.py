from pathlib import Path
from data_engineering import extract, transform


def test_extract_writes_file(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    output = extract.main(raw_dir)
    assert output.exists()


def test_transform_reads_and_writes(tmp_path):
    raw_dir = tmp_path / "raw"
    curated_dir = tmp_path / "curated"
    raw_dir.mkdir()
    curated_dir.mkdir()
    input_file = raw_dir / "orders.csv"
    input_file.write_text(
        "id,customer_id,total_amount,created_at\n"
        "1,10,100,2026-06-01\n"
    )
    output = transform.main(raw_dir, curated_dir)
    assert output.exists()
