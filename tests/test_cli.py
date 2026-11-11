"""Tests for solkalk.cli (mocked HTTP)."""

import re

import responses

from solkalk import cli
from solkalk.features.prices import ecb_exchange_rates


@responses.activate
def test_ecb_command_writes_csv(tmp_path, ecb_xml):
    responses.get(ecb_exchange_rates.build_url("SEK", "2024-12-26", "2025-01-08"), body=ecb_xml)
    out = tmp_path / "kurs.csv"
    code = cli.main(
        ["ecb", "--from-date", "2025-01-02", "--to-date", "2025-01-08", "--out", str(out)]
    )
    assert code == 0
    assert len(ecb_exchange_rates.read_csv(out)) == 7


def test_entsoe_command_requires_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ENTSOE_API_KEY", raising=False)
    assert cli.main(["entsoe", "--out-dir", str(tmp_path)]) == 1


@responses.activate
def test_ecb_command_fails_on_empty_response(tmp_path):
    empty = '<message:GenericData xmlns:message="m"><message:DataSet/></message:GenericData>'
    responses.get(ecb_exchange_rates.build_url("SEK", "2024-12-26", "2025-01-03"), body=empty)
    out = tmp_path / "kurs.csv"
    code = cli.main(
        ["ecb", "--from-date", "2025-01-02", "--to-date", "2025-01-03", "--out", str(out)]
    )
    assert code == 1
    assert not out.exists()


def test_entsoe_command_rejects_unknown_area(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ENTSOE_API_KEY", "x")
    assert cli.main(["entsoe", "--areas", "SE3,SE5", "--out-dir", str(tmp_path)]) == 1
    assert "SE5" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


@responses.activate
def test_strang_command_reports_fetch_error(tmp_path, capsys):
    responses.get(re.compile(r"https://opendata-download-metanalys\.smhi\.se/.*"), status=404)
    out = tmp_path / "sol.csv"
    code = cli.main(
        ["strang", "--lat", "59.33", "--lon", "18.07", "--year", "2024", "--out", str(out)]
    )
    assert code == 1
    assert "HTTP 404" in capsys.readouterr().out
    assert not out.exists()


@responses.activate
def test_ecb_command_reports_fetch_error(tmp_path, capsys):
    responses.get(ecb_exchange_rates.build_url("SEK", "2024-12-26", "2025-01-03"), status=404)
    code = cli.main(["ecb", "--from-date", "2025-01-02", "--to-date", "2025-01-03"])
    assert code == 1
    assert "HTTP 404" in capsys.readouterr().out
