import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

root = str(Path(__file__).parent.parent)
sys.path.insert(0, str(Path(root) / "src"))
try:
    import deauville.api as api_module
    from deauville.api import app
    from deauville.festival import (
        Artist,
        Festival,
        Lineup,
        Performance,
        SoloShow,
        Venue,
        Workshop,
    )
    from deauville.storage import JsonFileStorage, MemoryStorage
finally:
    sys.path.remove(str(Path(root) / "src"))

client = TestClient(app)


@pytest.fixture
def writable_festival(monkeypatch: pytest.MonkeyPatch) -> tuple[Festival, list[dict]]:
    festival = JsonFileStorage(Path("data/festival.json")).load()
    saved_data = []

    class RecordingStorage(MemoryStorage):
        def save(self, value: Festival) -> None:
            super().save(value)
            saved_data.append(value.to_data())

    storage = RecordingStorage(festival)
    monkeypatch.setattr(api_module.app.state, "storage", storage)
    return festival, saved_data


def test_homepage_serves_static_site() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "showHomePage();" in response.text


def test_admin_page_serves_starter_admin() -> None:
    response = client.get("/admin/")

    assert response.status_code == 200
    assert "New performance" in response.text


def test_festival_route_returns_dates() -> None:
    response = client.get("/api/festival")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Deauville Festival du Rire 2027",
        "first_day": "2027-06-10",
        "last_day": "2027-06-13",
        "days": ["2027-06-10", "2027-06-11", "2027-06-12", "2027-06-13"],
    }


def test_venues_route_returns_contract_fields_in_file_order() -> None:
    response = client.get("/api/venues")

    assert response.status_code == 200
    venues = response.json()
    assert [venue["slug"] for venue in venues] == [
        "grand-casino",
        "theatre-des-planches",
        "le-kiosque",
        "la-cabane",
    ]
    assert all(
        set(venue) == {"slug", "name", "capacity", "address"} for venue in venues
    )


def test_artists_route_returns_contract_fields_sorted_by_slug() -> None:
    response = client.get("/api/artists")

    assert response.status_code == 200
    artists = response.json()
    assert len(artists) == 12
    assert artists[0]["name"] == "Élodie Marchal"
    assert [artist["slug"] for artist in artists] == sorted(
        artist["slug"] for artist in artists
    )
    assert all(
        set(artist) == {"slug", "name", "bio", "photo_url"} for artist in artists
    )


def test_festival_loads_data_as_objects() -> None:
    festival = JsonFileStorage(Path("data/festival.json")).load()

    assert isinstance(festival, Festival)
    assert all(isinstance(venue, Venue) for venue in festival.venues)
    assert all(isinstance(artist, Artist) for artist in festival.artists)
    assert all(
        isinstance(performance, Performance) for performance in festival.performances
    )
    assert isinstance(
        festival.get_performance("grand-casino-2027-06-11-2030"), SoloShow
    )
    assert isinstance(festival.get_performance("le-kiosque-2027-06-12-0100"), Lineup)
    assert isinstance(festival.get_performance("la-cabane-2027-06-11-1030"), Workshop)


def test_programme_route_returns_performance_views_and_filters() -> None:
    response = client.get("/api/programme", params={"day": "2027-06-11"})

    assert response.status_code == 200
    performances = response.json()
    assert performances[-1]["title"] == "After Hours"
    assert performances[-1]["festival_day"] == "2027-06-11"
    assert performances[-1]["end"] == "2027-06-12T02:00"
    assert performances[-1]["artists"] == [
        {"slug": "tom-vasseur", "name": "Tom Vasseur"},
        {"slug": "hugo-lemaire", "name": "Hugo Lemaire"},
        {"slug": "maya-choukri", "name": "Maya Choukri"},
    ]

    venue_response = client.get("/api/programme", params={"venue": "le-kiosque"})
    assert venue_response.status_code == 200
    assert len(venue_response.json()) == 7


def test_programme_route_returns_404_for_unknown_venue() -> None:
    response = client.get("/api/programme", params={"venue": "nowhere"})

    assert response.status_code == 404
    assert response.json() == {"detail": "No venue 'nowhere'."}


def test_programme_route_rejects_invalid_day() -> None:
    response = client.get("/api/programme", params={"day": "June 11"})

    assert response.status_code == 422


def test_performance_route_returns_full_view() -> None:
    response = client.get("/api/performances/le-kiosque-2027-06-12-0100")

    assert response.status_code == 200
    assert response.json() == {
        "id": "le-kiosque-2027-06-12-0100",
        "kind": "lineup",
        "title": "After Hours",
        "venue": "le-kiosque",
        "venue_name": "Le Kiosque",
        "start": "2027-06-12T01:00",
        "end": "2027-06-12T02:00",
        "duration_minutes": 60,
        "festival_day": "2027-06-11",
        "description": "The last show of Friday night, after midnight.",
        "summary": "hosted by Tom Vasseur, with Hugo Lemaire, Maya Choukri",
        "capacity": 120,
        "artists": [
            {"slug": "tom-vasseur", "name": "Tom Vasseur"},
            {"slug": "hugo-lemaire", "name": "Hugo Lemaire"},
            {"slug": "maya-choukri", "name": "Maya Choukri"},
        ],
        "host": "tom-vasseur",
        "acts": ["hugo-lemaire", "maya-choukri"],
    }


def test_performance_route_returns_404_for_unknown_id() -> None:
    response = client.get("/api/performances/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "No performance 'unknown'."}


def test_artist_detail_route_lists_performances_in_order() -> None:
    response = client.get("/api/artists/max-pellerin")

    assert response.status_code == 200
    artist = response.json()
    assert artist["name"] == "Max Pellerin"
    assert [performance["title"] for performance in artist["performances"]] == [
        "Opening Gala",
        "Late Laughs",
        "Deauville Comedy Club",
        "Closing Gala",
    ]


def test_artist_detail_route_returns_404_for_unknown_artist() -> None:
    response = client.get("/api/artists/nowhere")

    assert response.status_code == 404
    assert response.json() == {"detail": "No artist 'nowhere'."}


def test_workshop_performance_view_reports_remaining_places() -> None:
    response = client.get("/api/performances/la-cabane-2027-06-11-1030")

    assert response.status_code == 200
    assert response.json()["places_left"] == 9
    assert response.json()["capacity"] == 12


def test_solo_performance_view_includes_age_and_artist_fields() -> None:
    response = client.get("/api/performances/theatre-des-planches-2027-06-11-2130")

    assert response.status_code == 200
    performance = response.json()
    assert performance["kind"] == "solo"
    assert performance["artist"] == "karim-benali"
    assert performance["min_age"] == 16
    assert performance["summary"] == "Karim Benali"


def test_admin_adds_artist_and_rejects_duplicate_slug(
    writable_festival: tuple[Festival, list[dict]],
) -> None:
    festival, saved_data = writable_festival

    created = client.post(
        "/api/artists",
        json={"name": " Zoé Tanguy ", "bio": "New artist."},
    )
    duplicate = client.post("/api/artists", json={"name": "zoe tanguy"})

    assert created.status_code == 201
    assert created.json()["name"] == "Zoé Tanguy"
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "An artist named 'zoe tanguy' already exists."
    }
    assert len(festival.artists) == 13
    assert len(saved_data) == 1
    assert saved_data[0]["artists"][-1]["name"] == "Zoé Tanguy"


def test_admin_schedules_performance_and_rejects_busy_venue(
    writable_festival: tuple[Festival, list[dict]],
) -> None:
    festival, saved_data = writable_festival
    body = {
        "kind": "solo",
        "title": "New Nora Show",
        "venue": "le-kiosque",
        "start": "2027-06-13T11:00",
        "duration_minutes": 45,
        "artist": "nora-lebrun",
        "min_age": 0,
    }

    created = client.post("/api/performances", json=body)
    conflict = client.post(
        "/api/performances",
        json={
            **body,
            "title": "Crowded Show",
            "start": "2027-06-13T11:30",
        },
    )

    assert created.status_code == 201
    assert created.json()["id"] == "le-kiosque-2027-06-13-1100"
    assert conflict.status_code == 409
    assert "Le Kiosque is busy" in conflict.json()["detail"]
    assert len(festival.performances) == 24
    assert len(saved_data) == 1


def test_admin_move_is_atomic_when_new_slot_is_busy(
    writable_festival: tuple[Festival, list[dict]],
) -> None:
    festival, saved_data = writable_festival
    body = {
        "kind": "solo",
        "title": "New Nora Show",
        "venue": "le-kiosque",
        "start": "2027-06-13T11:00",
        "duration_minutes": 45,
        "artist": "nora-lebrun",
        "min_age": 0,
    }
    created = client.post("/api/performances", json=body)
    old_id = created.json()["id"]
    moved = client.put(
        f"/api/performances/{old_id}",
        json={**body, "start": "2027-06-13T12:00"},
    )
    refused_move = client.put(
        f"/api/performances/{moved.json()['id']}",
        json={**body, "start": "2027-06-13T15:00"},
    )

    assert moved.status_code == 200
    assert moved.json()["id"] == "le-kiosque-2027-06-13-1200"
    assert refused_move.status_code == 409
    assert festival.get_performance(moved.json()["id"]).start.isoformat() == (
        "2027-06-13T12:00:00"
    )
    assert festival.get_performance(old_id) is None
    assert len(saved_data) == 2


def test_admin_cancels_performance(
    writable_festival: tuple[Festival, list[dict]],
) -> None:
    festival, saved_data = writable_festival
    performance_id = festival.performances[0].id

    response = client.delete(f"/api/performances/{performance_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert festival.get_performance(performance_id) is None
    assert len(saved_data) == 1


def test_admin_registers_participant_once(
    writable_festival: tuple[Festival, list[dict]],
) -> None:
    festival, saved_data = writable_festival
    workshop = next(
        performance
        for performance in festival.performances
        if performance.title == "Stand-up Lab"
    )

    registered = client.post(
        f"/api/performances/{workshop.id}/participants",
        json={"name": " Camille Test "},
    )
    duplicate = client.post(
        f"/api/performances/{workshop.id}/participants",
        json={"name": "camille test"},
    )

    assert registered.status_code == 201
    assert registered.json()["participants"][-1] == "Camille Test"
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "camille test is already registered."}
    assert workshop.participants[-1] == "Camille Test"
    assert len(saved_data) == 1


def test_admin_rejects_invalid_performance_body(
    writable_festival: tuple[Festival, list[dict]],
) -> None:
    festival, saved_data = writable_festival

    response = client.post(
        "/api/performances",
        json={
            "kind": "solo",
            "title": "Invalid Age",
            "venue": "le-kiosque",
            "start": "2027-06-13T11:00",
            "duration_minutes": 45,
            "artist": "nora-lebrun",
            "min_age": 19,
        },
    )

    assert response.status_code == 422
    assert len(festival.performances) == 23
    assert saved_data == []


def test_admin_maps_missing_references_rules_and_festival_dates(
    writable_festival: tuple[Festival, list[dict]],
) -> None:
    festival, saved_data = writable_festival
    body = {
        "kind": "solo",
        "title": "A New Show",
        "venue": "unknown-venue",
        "start": "2027-06-13T11:00",
        "duration_minutes": 45,
        "artist": "unknown-artist",
    }

    missing_venue = client.post("/api/performances", json=body)
    missing_artist = client.post(
        "/api/performances", json={**body, "venue": "le-kiosque"}
    )
    bad_date = client.post(
        "/api/performances",
        json={
            **body,
            "venue": "le-kiosque",
            "start": "2027-06-09T11:00",
            "artist": "nora-lebrun",
        },
    )
    one_act = client.post(
        "/api/performances",
        json={
            **body,
            "kind": "lineup",
            "venue": "le-kiosque",
            "host": "tom-vasseur",
            "acts": ["hugo-lemaire"],
        },
    )

    assert missing_venue.status_code == 404
    assert missing_artist.status_code == 404
    assert bad_date.status_code == 409
    assert one_act.status_code == 422
    assert len(festival.performances) == 23
    assert saved_data == []


def test_admin_changes_are_persisted_to_the_data_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    original_data = Path(__file__).parent.parent / "data" / "festival.json"
    (data_directory / "festival.json").write_bytes(original_data.read_bytes())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        api_module.app.state,
        "storage",
        JsonFileStorage(Path("data/festival.json")),
    )

    response = client.post(
        "/api/artists",
        json={"name": "Zoé Tanguy", "bio": "New artist."},
    )

    assert response.status_code == 201
    persisted = json.loads((data_directory / "festival.json").read_text("utf-8"))
    assert persisted["artists"][-1]["name"] == "Zoé Tanguy"
    assert any(
        artist["slug"] == "zoe-tanguy" for artist in client.get("/api/artists").json()
    )


def test_invalid_json_data_file_returns_clear_server_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    (data_directory / "festival.json").write_text("{", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        api_module.app.state,
        "storage",
        JsonFileStorage(Path("data/festival.json")),
    )

    response = client.get("/api/festival")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "The festival data file contains invalid JSON."
    }


def test_now_route_returns_active_and_next_three_performances() -> None:
    response = client.get("/api/now", params={"at": "2027-06-11T21:00"})

    assert response.status_code == 200
    data = response.json()
    assert data["at"] == "2027-06-11T21:00"
    assert [performance["title"] for performance in data["now_playing"]] == [
        "Tall Tales"
    ]
    assert [performance["title"] for performance in data["up_next"]] == [
        "Straight Face",
        "Late Laughs",
        "After Hours",
    ]


def test_now_route_returns_after_hours_when_it_is_active() -> None:
    response = client.get("/api/now", params={"at": "2027-06-12T01:30"})

    assert response.status_code == 200
    data = response.json()
    assert [performance["title"] for performance in data["now_playing"]] == [
        "After Hours"
    ]
