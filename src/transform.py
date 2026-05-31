import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Default column selection used when none is specified in config.
_DEFAULT_TARGET_COLUMNS: list[str] = [
    "id", "name", "username", "email", "phone", "website"
]


def transform_data(
    raw_records: list[dict],
    settings: dict | None = None,
) -> pd.DataFrame:
    """
    Cleans, normalises, and transforms validated records into a structured DataFrame.

    Args:
        raw_records: List of dicts that have already been validated by extract_data.
        settings:    Transformation settings dict from base_config.json.
                     Supports keys:
                       - target_columns   (list[str])  — columns to select
                       - standardize_strings (bool)    — title-case name, lower email
                       - drop_duplicates    (bool)      — remove duplicate rows

    Returns:
        A clean pandas DataFrame ready for the Load phase.
    """
    logger.info("Starting Transformation and schema normalisation phase...")

    if not raw_records:
        logger.warning("Empty payload received. Returning empty structural DataFrame.")
        return pd.DataFrame()

    settings = settings or {}
    target_columns: list[str] = settings.get("target_columns", _DEFAULT_TARGET_COLUMNS)
    should_standardize: bool = settings.get("standardize_strings", True)
    should_dedup: bool = settings.get("drop_duplicates", True)

    try:
        raw_df = pd.DataFrame(raw_records)

        # Select only the configured columns that actually exist in the data
        available_cols = [col for col in target_columns if col in raw_df.columns]
        missing_cols = [col for col in target_columns if col not in raw_df.columns]
        if missing_cols:
            logger.warning(f"Configured columns not found in source data: {missing_cols}")

        df = raw_df[available_cols].copy()

        # Deduplication
        if should_dedup:
            before = len(df)
            df.drop_duplicates(inplace=True)
            dropped = before - len(df)
            if dropped:
                logger.info(f"Removed {dropped} duplicate row(s).")

        # String standardisation
        if should_standardize:
            if "name" in df.columns:
                df["name"] = df["name"].astype(str).str.title()
            if "email" in df.columns:
                df["email"] = df["email"].astype(str).str.lower().str.strip()
            if "username" in df.columns:
                df["username"] = df["username"].astype(str).str.strip()

        # Safe null handling for optional fields
        null_defaults = {col: "N/A" for col in ["website", "phone"] if col in df.columns}
        if null_defaults:
            df.fillna(value=null_defaults, inplace=True)

        logger.info(
            f"Transformation complete. Output shape: {len(df)} rows × {len(df.columns)} columns."
        )
        return df

    except Exception as e:
        logger.error(f"Critical failure during Transformation phase: {e}")
        raise
