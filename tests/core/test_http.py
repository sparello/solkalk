"""Tests for solkalk.core.http."""

import pytest
import responses

from solkalk.core.http import FetchError, get_text

URL = "https://example.test/data"


@responses.activate
def test_returns_body_on_200():
    responses.get(URL, body="hej", status=200)
    assert get_text(URL) == "hej"


@responses.activate
def test_retries_on_5xx_then_succeeds():
    responses.get(URL, status=503)
    responses.get(URL, body="ok", status=200)
    slept = []
    assert get_text(URL, retries=3, sleep=slept.append) == "ok"
    assert slept == [5]


@responses.activate
def test_fatal_4xx_does_not_retry():
    responses.get(URL, status=401)
    slept = []
    with pytest.raises(FetchError):
        get_text(URL, retries=3, sleep=slept.append)
    assert slept == []
    assert len(responses.calls) == 1


@responses.activate
def test_gives_up_after_retries():
    for _ in range(3):
        responses.get(URL, status=500)
    slept = []
    with pytest.raises(FetchError):
        get_text(URL, retries=3, sleep=slept.append)
    assert len(responses.calls) == 3
    assert slept == [5, 5]  # no pause after the last attempt


@responses.activate
def test_error_message_never_contains_secret():
    secret_url = URL + "?documentType=A44&securityToken=SUPERSECRET&x=1"
    responses.get(secret_url, status=403)
    with pytest.raises(FetchError) as info:
        get_text(secret_url)
    assert "SUPERSECRET" not in str(info.value)
    assert "securityToken=***" in str(info.value)


def test_redact_url_handles_several_param_names():
    from solkalk.core.http import redact_url

    assert (
        redact_url("https://a/b?api_key=abc&token=def&q=1")
        == "https://a/b?api_key=***&token=***&q=1"
    )


@responses.activate
def test_network_error_does_not_leak_secret_in_message_or_traceback():
    """requests puts the full URL in its error text; it must not reach the caller."""
    import traceback

    import requests

    secret_url = URL + "?documentType=A44&securityToken=SUPERSECRET&x=1"
    responses.get(secret_url, body=requests.ConnectionError(f"Max retries exceeded: {secret_url}"))
    with pytest.raises(FetchError) as info:
        get_text(secret_url, retries=2, sleep=lambda _: None)
    rendered = "".join(traceback.format_exception(info.value))
    assert "SUPERSECRET" not in rendered
    assert "ConnectionError" in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__
