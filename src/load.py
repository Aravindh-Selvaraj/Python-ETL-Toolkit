import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)


def load_data(df: pd.DataFrame, target_path: str) -> bool:
    """
    Persists the transformed DataFrame to a CSV file at the given path.

    Args:
        df:          Clean, validated DataFrame from the Transform phase.
        target_path: Destination file path (directories are created if missing).

    Returns:
        True  — file written successfully.
        False — DataFrame was empty; file write skipped.

    Raises:
        OSError:    If the directory cannot be created or the file cannot be written.
        Exception:  Any unexpected error during the write sequence.
    """
    logger.info(f"Starting Load phase. Target destination: {target_path}")

    if df.empty:
        logger.warning("DataFrame is empty. Skipping file persistence.")
        return False

    try:
        # Ensure parent directory structure exists
        directory = os.path.dirname(target_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created output directory: {directory}")

        df.to_csv(target_path, index=False, encoding="utf-8")

        file_size_kb = os.path.getsize(target_path) / 1024
        logger.info(
            f"Load complete. {len(df)} rows written to '{target_path}' "
            f"({file_size_kb:.1f} KB)."
        )
        return True

    except Exception as e:
        logger.error(f"Critical failure during Load phase: {e}")
        raise
