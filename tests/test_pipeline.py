"""
Test suite for the Python ETL Toolkit.
Covers all three pipeline phases: Extract, Transform, Load.
"""

import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.extract import extract_data
from src.transform import transform_data
from src.load import load_data


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

VALID_RECORDS = [
    {"id": 1, "name": "john doe",   "username": "jdoe",  "email": "JOHN@doe.com",   "phone": "123", "website": "doe.com"},
    {"id": 1, "name": "john doe",   "username": "jdoe",  "email": "JOHN@doe.com",   "phone": "123", "website": "doe.com"},  # duplicate
    {"id": 2, "name": "jane smith", "username": "jsmith", "email": "JANE@smith.com", "phone": "456", "website": "smith.com"},
]

INVALID_RECORDS = [
    {"id": 3, "name": "",           "username": "blank_name", "email": "ok@ok.com"},   # blank name
    {"id": 4, "name": "No Email",   "username": "noemail",    "email": "not-an-email"},# bad email
]


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACT phase
# ─────────────────────────────────────────────────────────────────────────────

class TestExtract:

    def test_extract_returns_valid_records(self):
        """Successful fetch should return a list of validated dicts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = VALID_RECORDS[:2]  # no duplicates

        with patch("src.extract.requests.get", return_value=mock_response):
            result = extract_data("http://fake-url.test/users")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)

    def test_extract_wraps_single_dict_in_list(self):
        """A single-object JSON response should be wrapped into a list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = VALID_RECORDS[0]  # single dict, not a list

        with patch("src.extract.requests.get", return_value=mock_response):
            result = extract_data("http://fake-url.test/users/1")

        assert isinstance(result, list)
        assert len(result) == 1

    def test_extract_skips_invalid_records(self):
        """Records that fail Pydantic validation should be skipped, not crash."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mix one valid + two invalid records
        mock_response.json.return_value = [VALID_RECORDS[0]] + INVALID_RECORDS

        with patch("src.extract.requests.get", return_value=mock_response):
            result = extract_data("http://fake-url.test/users")

        # Only the valid record should pass through
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_extract_retries_on_connection_error(self):
        """Transient connection errors should trigger retries before raising."""
        import requests as req
        with patch("src.extract.requests.get",
                   side_effect=req.exceptions.ConnectionError("timeout")) as mock_get, \
             patch("src.extract.time.sleep"):  # skip real sleep in tests

            with pytest.raises(req.exceptions.RetryError):
                extract_data("http://fake-url.test/users")

        # Should have attempted _MAX_RETRIES times
        from src.extract import _MAX_RETRIES
        assert mock_get.call_count == _MAX_RETRIES

    def test_extract_raises_immediately_on_4xx(self):
        """Client errors (4xx) should NOT be retried."""
        import requests as req
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError("404 Not Found")

        with patch("src.extract.requests.get", return_value=mock_response):
            with pytest.raises(req.exceptions.HTTPError):
                extract_data("http://fake-url.test/missing")


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFORM phase
# ─────────────────────────────────────────────────────────────────────────────

class TestTransform:

    def test_deduplication(self):
        """Duplicate rows should be removed."""
        result = transform_data(VALID_RECORDS)
        assert len(result) == 2  # 3 records, 1 is a duplicate

    def test_name_title_cased(self):
        """Names should be title-cased."""
        result = transform_data(VALID_RECORDS)
        assert result.iloc[0]["name"] == "John Doe"

    def test_email_lowercased(self):
        """Emails should be lowercased."""
        result = transform_data(VALID_RECORDS)
        assert result.iloc[0]["email"] == "john@doe.com"

    def test_empty_input_returns_empty_dataframe(self):
        """Empty input should yield an empty DataFrame, not an exception."""
        result = transform_data([])
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_custom_target_columns_from_settings(self):
        """Only columns specified in settings should appear in output."""
        settings = {"target_columns": ["id", "name", "email"]}
        result = transform_data(VALID_RECORDS, settings=settings)
        assert list(result.columns) == ["id", "name", "email"]

    def test_missing_configured_column_is_ignored_gracefully(self):
        """A configured column absent from the data should not raise an error."""
        settings = {"target_columns": ["id", "name", "nonexistent_field"]}
        result = transform_data(VALID_RECORDS, settings=settings)
        assert "nonexistent_field" not in result.columns
        assert "id" in result.columns

    def test_dedup_disabled_via_settings(self):
        """When drop_duplicates=false, duplicates should be preserved."""
        settings = {"drop_duplicates": False}
        result = transform_data(VALID_RECORDS, settings=settings)
        assert len(result) == 3  # all 3 rows, duplicate kept


# ─────────────────────────────────────────────────────────────────────────────
# LOAD phase
# ─────────────────────────────────────────────────────────────────────────────

class TestLoad:

    def test_load_writes_csv(self, tmp_path):
        """A non-empty DataFrame should be written to a CSV file."""
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        output_file = str(tmp_path / "output" / "result.csv")

        success = load_data(df, output_file)

        assert success is True
        assert os.path.exists(output_file)

        written = pd.read_csv(output_file)
        assert len(written) == 2
        assert list(written.columns) == ["id", "name"]

    def test_load_creates_missing_directories(self, tmp_path):
        """Nested directories that don't exist should be created automatically."""
        df = pd.DataFrame({"id": [1]})
        deep_path = str(tmp_path / "a" / "b" / "c" / "out.csv")

        load_data(df, deep_path)

        assert os.path.exists(deep_path)

    def test_load_empty_dataframe_returns_false(self, tmp_path):
        """An empty DataFrame should return False and skip writing."""
        df = pd.DataFrame()
        output_file = str(tmp_path / "empty.csv")

        success = load_data(df, output_file)

        assert success is False
        assert not os.path.exists(output_file)

    def test_load_csv_utf8_encoded(self, tmp_path):
        """Output CSV must be UTF-8 encoded."""
        df = pd.DataFrame({"name": ["Ünïcödé Nämé"]})
        output_file = str(tmp_path / "utf8.csv")

        load_data(df, output_file)

        with open(output_file, encoding="utf-8") as f:
            content = f.read()
        assert "Ünïcödé Nämé" in content
