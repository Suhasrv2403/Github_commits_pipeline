"""Unit tests for src/extract.py's GitHub extraction and S3 upload logic.

Covers the pagination loop and error handling in get_commits(), and the
success/failure paths of upload_to_s3(). requests.Session.get and
boto3.client are mocked throughout so no network calls are made and no
GITHUB_TOKEN/AWS credentials are required.
"""
import json
from unittest.mock import MagicMock, patch

import requests

import extract


def _make_response(json_data, raise_error=None):
    """Build a fake requests.Response-like object for mocking session.get."""
    response = MagicMock()
    if raise_error is not None:
        response.raise_for_status.side_effect = raise_error
    else:
        response.raise_for_status.side_effect = None
    response.json.return_value = json_data
    return response


@patch("requests.Session.get")
def test_get_commits_stops_on_empty_page(mock_get):
    """Pagination should stop as soon as a page comes back empty, without
    making further requests."""
    page_one = [{"sha": "a"}, {"sha": "b"}]
    mock_get.side_effect = [_make_response(page_one), _make_response([])]

    result = extract.get_commits("octocat", "hello-world")

    assert result == page_one
    assert mock_get.call_count == 2


@patch("requests.Session.get")
def test_get_commits_respects_max_pages(mock_get):
    """The loop must not fetch more than extract.MAX_PAGES pages even if
    every page returns a full, non-empty result."""
    page = [{"sha": "x"}] * extract.PER_PAGE
    mock_get.return_value = _make_response(page)

    result = extract.get_commits("octocat", "hello-world")

    assert mock_get.call_count == extract.MAX_PAGES
    assert len(result) == extract.MAX_PAGES * extract.PER_PAGE


@patch("requests.Session.get")
def test_get_commits_returns_partial_results_on_request_exception(mock_get):
    """If a request fails partway through, previously fetched pages should
    still be returned rather than raising or discarding everything."""
    page_one = [{"sha": "a"}]
    mock_get.side_effect = [
        _make_response(page_one),
        requests.exceptions.RequestException("boom"),
    ]

    result = extract.get_commits("octocat", "hello-world")

    assert result == page_one
    assert mock_get.call_count == 2


@patch("requests.Session.get")
def test_get_commits_returns_empty_list_on_first_page_failure(mock_get):
    """If even the first request fails, get_commits should return an empty
    list rather than raising."""
    mock_get.side_effect = requests.exceptions.RequestException("boom")

    result = extract.get_commits("octocat", "hello-world")

    assert result == []
    assert mock_get.call_count == 1


@patch("boto3.client")
def test_upload_to_s3_writes_expected_bucket_key_and_body(mock_boto_client):
    """upload_to_s3 should PUT the JSON-serialized data to raw/<filename>
    in the configured bucket."""
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    data = [{"sha": "a"}]

    extract.upload_to_s3(data, "commits_20260101.json")

    mock_s3.put_object.assert_called_once()
    _, kwargs = mock_s3.put_object.call_args
    assert kwargs["Bucket"] == extract.AWS_BUCKET
    assert kwargs["Key"] == "raw/commits_20260101.json"
    assert json.loads(kwargs["Body"]) == data


@patch("boto3.client")
def test_upload_to_s3_swallows_errors_without_raising(mock_boto_client):
    """A failed S3 upload should be caught and logged, not propagated —
    the DAG task shouldn't crash on a transient S3 issue mid-print."""
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = Exception("S3 is down")
    mock_boto_client.return_value = mock_s3

    extract.upload_to_s3([{"sha": "a"}], "commits_20260101.json")  # must not raise
