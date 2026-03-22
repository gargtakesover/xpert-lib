import pytest
import json
import click
from unittest.mock import patch, MagicMock
from xpert_cli.cli import output_result

def test_output_result_value_error_json():
    """Test that output_result handles ValueError during JSON serialization."""
    mock_tweet = MagicMock()
    with patch("xpert_cli.cli._tweet_to_dict", return_value={"id": "1"}):
        with patch("json.dumps", side_effect=ValueError("JSON serialization failed")):
            with pytest.raises(click.ClickException) as excinfo:
                output_result([mock_tweet], "json", None)
            assert "Failed to export data: JSON serialization failed" in str(excinfo.value)

def test_output_result_value_error_format():
    """Test that output_result handles ValueError during format export."""
    mock_tweet = MagicMock()
    with patch("xpert_cli.cli.tweets_to_format", side_effect=ValueError("Format export failed"), create=True):
        with pytest.raises(click.ClickException) as excinfo:
            output_result([mock_tweet], "csv", "output.csv")
        assert "Failed to export data: Format export failed" in str(excinfo.value)
