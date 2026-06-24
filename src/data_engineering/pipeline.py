from .extract import main as extract_main
from .transform import main as transform_main
from .validate import main as validate_main


def run_pipeline():
    extract_main()
    transform_main()
    validate_main()


if __name__ == '__main__':
    run_pipeline()
