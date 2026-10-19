from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from festival import load_festival, slug

app = FastAPI()


@app.get("/api/festival")
def get_festival() -> dict:
    festival = load_festival()
    first_day = date.fromisoformat(festival["first_day"])
    last_day = date.fromisoformat(festival["last_day"])
    days = [
        (first_day + timedelta(days=offset)).isoformat()
        for offset in range((last_day - first_day).days + 1)
    ]

    return {
        "name": festival["name"],
        "first_day": festival["first_day"],
        "last_day": festival["last_day"],
        "days": days,
    }


@app.get("/api/venues")
def list_venues() -> list[dict]:
    festival = load_festival()
    return [
        {
            "slug": slug(venue["name"]),
            "name": venue["name"],
            "capacity": venue["capacity"],
            "address": venue["address"],
        }
        for venue in festival["venues"]
    ]


@app.get("/api/artists")
def list_artists() -> list[dict]:
    festival = load_festival()
    artists = sorted(festival["artists"], key=lambda artist: slug(artist["name"]))
    return [
        {
            "slug": slug(artist["name"]),
            "name": artist["name"],
            "bio": artist["bio"],
            "photo_url": artist["photo_url"],
        }
        for artist in artists
    ]


web_directory = Path(__file__).parent / "web"
admin_directory = web_directory / "admin"
if admin_directory.is_dir():
    app.mount(
        "/admin",
        StaticFiles(directory=admin_directory, html=True),
        name="admin",
    )

public_directory = web_directory / "public"
if public_directory.is_dir():
    app.mount("/", StaticFiles(directory=public_directory, html=True), name="web")
