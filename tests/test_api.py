import sys
from pathlib import Path

from fastapi.testclient import TestClient

root = str(Path(__file__).parent.parent)
sys.path.insert(0, root)
try:
    from api import app
    from festival import (
        Artist,
        Festival,
        Lineup,
        Performance,
        SoloShow,
        Venue,
        Workshop,
        load_festival,
    )
finally:
    sys.path.remove(root)

client = TestClient(app)


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
    festival = load_festival()

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
