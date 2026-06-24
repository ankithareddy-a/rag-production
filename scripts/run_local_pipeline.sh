#!/usr/bin/env bash
set -e
python src/data_engineering/extract.py
python src/data_engineering/transform.py
python src/data_engineering/validate.py
