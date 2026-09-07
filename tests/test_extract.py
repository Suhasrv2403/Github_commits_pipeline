"""Unit tests for src/extract.py's GitHub extraction logic.

Covers the pagination loop and error handling in get_commits(), which had
no test coverage before. requests.Session.get is mocked throughout so no
network calls are made and no GITHUB_TOKEN is required.
"""
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
