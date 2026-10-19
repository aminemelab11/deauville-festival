from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from festival import load_festival

app = FastAPI()


@app.get("/api/festival")
def get_festival() -> dict:
    festival = load_festival()
    days = [
        (festival.first_day + timedelta(days=offset)).isoformat()
        for offset in range((festival.last_day - festival.first_day).days + 1)
    ]

    return {
        "name": festival.name,
        "first_day": festival.first_day.isoformat(),
        "last_day": festival.last_day.isoformat(),
        "days": days,
    }


@app.get("/api/venues")
def list_venues() -> list[dict]:
    festival = load_festival()
    return [venue.to_view() for venue in festival.venues]


@app.get("/api/artists")
def list_artists() -> list[dict]:
    festival = load_festival()
    artists = sorted(festival.artists, key=lambda artist: artist.slug)
    return [artist.to_view() for artist in artists]


@app.get("/api/artists/{artist_slug}")
def get_artist(artist_slug: str) -> dict:
    festival = load_festival()
    artist = festival.get_artist(artist_slug)
    if artist is None:
        raise HTTPException(status_code=404, detail=f"No artist '{artist_slug}'.")

    view = artist.to_view()
    view["performances"] = [
        performance.to_view()
        for performance in festival.performances_for_artist(artist)
    ]
    return view


@app.get("/api/programme")
def get_programme(day: date | None = None, venue: str | None = None) -> list[dict]:
    festival = load_festival()
    if venue is not None and festival.get_venue(venue) is None:
        raise HTTPException(status_code=404, detail=f"No venue '{venue}'.")

    performances = (
        festival.performances_for_day(day)
        if day is not None
        else festival.ordered_performances()
    )
    if venue is not None:
        performances = [
            performance
            for performance in performances
            if performance.venue.slug == venue
        ]
    return [performance.to_view() for performance in performances]


@app.get("/api/performances/{performance_id}")
def get_performance(performance_id: str) -> dict:
    festival = load_festival()
    performance = festival.get_performance(performance_id)
    if performance is None:
        raise HTTPException(
            status_code=404,
            detail=f"No performance '{performance_id}'.",
        )
    return performance.to_view()


@app.get("/api/now")
def get_now(at: datetime | None = None) -> dict:
    festival = load_festival()
    moment = at or datetime.now()
    return {
        "at": moment.isoformat(timespec="minutes"),
        "now_playing": [
            performance.to_view() for performance in festival.on_stage(moment)
        ],
        "up_next": [performance.to_view() for performance in festival.up_next(moment)],
    }


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
