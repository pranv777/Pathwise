import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from app.config import settings


def _day(offset: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=offset)).isoformat()


def _drive(id_, **overrides):
    base = {
        "id": id_,
        "company": "Acme",
        "role": "Engineer",
        "type": "full-time",
        "date": _day(7),
        "apply_by": _day(3),
        "location": "Bengaluru, India",
        "branches": ["CSE"],
        "min_cgpa": 7.0,
        "pay": "",
        "url": "",
        "description": "",
    }
    return {**base, **overrides}


@pytest.fixture()
def drives(monkeypatch):
    data = [
        _drive("past", date=_day(-3)),
        _drive(
            "intern",
            type="internship",
            date=_day(5),
            branches=["CSE", "IT"],
            min_cgpa=7.5,
            location="Bengaluru, India",
        ),
        _drive(
            "open",
            date=_day(10),
            branches=["All"],
            min_cgpa=6.0,
            location="Remote",
        ),
        _drive(
            "ece",
            date=_day(2),
            branches=["ECE"],
            min_cgpa=7.0,
            location="Pune, India",
        ),
    ]
    monkeypatch.setattr("app.api.routes_campus._load_drives", lambda: data)
    return data


def _ids(response):
    return [d["id"] for d in response.json()]


def test_upcoming_drives_are_sorted_by_date_and_past_ones_hidden(client, drives):
    r = client.get("/api/campus/drives")
    assert r.status_code == 200
    assert _ids(r) == ["ece", "intern", "open"]


def test_include_past_adds_old_drives_first(client, drives):
    r = client.get("/api/campus/drives", params={"include_past": True})
    assert _ids(r) == ["past", "ece", "intern", "open"]


def test_filter_by_job_type(client, drives):
    r = client.get("/api/campus/drives", params={"job_type": "internship"})
    assert _ids(r) == ["intern"]

    r = client.get("/api/campus/drives", params={"job_type": "full-time"})
    assert _ids(r) == ["ece", "open"]


def test_location_filter_always_keeps_remote_drives(client, drives):
    r = client.get("/api/campus/drives", params={"location": "bengaluru"})
    assert _ids(r) == ["intern", "open"]


def test_everything_is_eligible_when_no_branch_or_cgpa_given(client, drives):
    drives_out = client.get("/api/campus/drives").json()
    assert all(d["eligible"] for d in drives_out)
    assert all(d["reasons"] == [] for d in drives_out)


def test_branch_eligibility(client, drives):
    r = client.get("/api/campus/drives", params={"branch": "ECE"})
    by_id = {d["id"]: d for d in r.json()}

    assert by_id["ece"]["eligible"] is True
    assert by_id["open"]["eligible"] is True  # "All" branches
    assert by_id["intern"]["eligible"] is False
    assert "CSE" in by_id["intern"]["reasons"][0]


def test_branch_match_is_case_insensitive(client, drives):
    r = client.get("/api/campus/drives", params={"branch": "cse"})
    by_id = {d["id"]: d for d in r.json()}
    assert by_id["intern"]["eligible"] is True


def test_cgpa_eligibility_including_the_exact_cutoff(client, drives):
    r = client.get("/api/campus/drives", params={"cgpa": 7.0})
    by_id = {d["id"]: d for d in r.json()}

    assert by_id["ece"]["eligible"] is True  # 7.0 >= 7.0
    assert by_id["open"]["eligible"] is True
    assert by_id["intern"]["eligible"] is False
    assert "7.5" in by_id["intern"]["reasons"][0]


def test_branch_and_cgpa_reasons_are_both_reported(client, drives):
    r = client.get("/api/campus/drives", params={"branch": "ECE", "cgpa": 6.0})
    by_id = {d["id"]: d for d in r.json()}
    assert len(by_id["intern"]["reasons"]) == 2


def test_days_left_is_computed(client, drives):
    by_id = {d["id"]: d for d in client.get("/api/campus/drives").json()}
    assert by_id["intern"]["days_left"] == 5
    assert by_id["ece"]["days_left"] == 2


def test_invalid_query_values_are_rejected(client, drives):
    assert client.get("/api/campus/drives", params={"cgpa": 11}).status_code == 422
    assert client.get("/api/campus/drives", params={"cgpa": -1}).status_code == 422
    assert (
        client.get("/api/campus/drives", params={"job_type": "gig"}).status_code == 422
    )


def test_missing_data_file_returns_empty_list(client, monkeypatch):
    monkeypatch.setattr("app.api.routes_campus._load_drives", list)
    assert client.get("/api/campus/drives").json() == []


def test_bundled_drive_data_is_valid():
    """Guards the JSON you edit by hand: catches typos before deploy."""
    path = Path(settings.knowledge_base_dir) / "campus_drives.json"
    assert path.exists(), "campus_drives.json is missing"
    data = json.loads(path.read_text())
    assert data, "campus_drives.json is empty"

    ids = [d["id"] for d in data]
    assert len(ids) == len(set(ids)), "duplicate drive ids"

    for d in data:
        for key in ("id", "company", "role", "type", "date", "apply_by", "location"):
            assert d.get(key), f"{d.get('id')}: missing {key}"
        assert d["type"] in {"internship", "full-time"}, d["id"]
        assert date.fromisoformat(d["apply_by"]) <= date.fromisoformat(d["date"]), d[
            "id"
        ]
        assert isinstance(d["branches"], list) and d["branches"], d["id"]
        assert 0 <= d["min_cgpa"] <= 10, d["id"]
