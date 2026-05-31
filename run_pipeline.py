import os
import sys
import json
import logging
import logging.config
from dotenv import load_dotenv

from src.extract import extract_data
from src.transform import transform_data
from src.load import load_data


def setup_env(env_path: str = ".env") -> None:
    """
    Loads environment variables from the .env file into os.environ.
    Must be called before any os.getenv() calls in the pipeline.
    Logs a warning if no .env file is found (environment variables
    may still be set externally in CI/CD or production environments).
    """
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=False)
        print(f"[ENV] Loaded environment variables from '{env_path}'")
    else:
        print(
            f"[ENV] Warning: '{env_path}' not found. "
            "Relying on system environment variables."
        )


def setup_pipeline_logging(config_path: str = "config/logging_config.json") -> None:
    """Initialises structured logging from an external configuration file."""
    os.makedirs("logs", exist_ok=True)
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            log_config = json.load(f)
        logging.config.dictConfig(log_config)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning(
            f"Logging config not found at '{config_path}'. Using fallback configuration."
        )


def load_pipeline_config(config_path: str = "config/base_config.json") -> dict:
    """Loads pipeline operational properties from JSON config into memory."""
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    raise FileNotFoundError(
        f"Base configuration file missing at: {config_path}"
    )


def run_etl() -> None:
    """Orchestrates the full ETL pipeline lifecycle: Extract → Transform → Load."""

    # Step 0: Load .env FIRST — before any os.getenv() calls
    setup_env()
    setup_pipeline_logging()

    logger = logging.getLogger("ETL_Orchestrator")
    logger.info("=== ETL Pipeline Execution Started ===")

    try:
        # 1. Load config
        config = load_pipeline_config()
        env_label = os.getenv("ETL_ENV", config.get("environment", "development"))
        logger.info(
            f"Environment: {env_label} | Pipeline: {config.get('pipeline_name')}"
        )

        # Environment variable overrides take priority over config file values
        source_url = os.getenv("ETL_SOURCE_URL") or config["source_url"]
        target_path = os.getenv("ETL_TARGET_PATH") or config["target_path"]
        transform_settings: dict = config.get("transformation_settings", {})

        # 2. Extract — fetch + validate records (auth headers built from .env)
        raw_records = extract_data(source_url)

        # 3. Transform — clean + normalise using config-driven settings
        transformed_df = transform_data(raw_records, settings=transform_settings)

        # 4. Load — persist to CSV
        success = load_data(transformed_df, target_path)

        if success:
            logger.info("=== ETL Pipeline Completed Successfully ===")
        else:
            logger.warning("=== ETL Pipeline Finished with Warnings (empty output) ===")

    except Exception as pipeline_error:
        logging.getLogger("").critical(
            f"Pipeline aborted — unhandled exception: {pipeline_error}",
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    run_etl()
