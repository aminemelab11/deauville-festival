import sys
from pathlib import Path

from fastapi.testclient import TestClient

root = str(Path(__file__).parent.parent)
sys.path.insert(0, root)
try:
    from api import app
finally:
    sys.path.remove(root)

client = TestClient(app)


def test_homepage_serves_starter_site() -> None:
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
