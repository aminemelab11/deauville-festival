import logging
from datetime import date, datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from deauville.festival import (
    Artist,
    ConflictError,
    DataError,
    Festival,
    FestivalError,
    InvalidValueError,
    NotFoundError,
    Performance,
    performance_from_data,
)
from deauville.storage import JsonFileStorage, Storage

app = FastAPI()
app.state.storage = JsonFileStorage(Path("data/festival.json"))
logger = logging.getLogger(__name__)


class ArtistRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    bio: str = ""
    photo_url: str = ""


class ParticipantRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)


class PerformanceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    start: datetime
    duration_minutes: int = Field(ge=1, le=360)
    description: str = ""


class SoloShowRequest(PerformanceRequest):
    kind: Literal["solo"]
    artist: str = Field(min_length=1)
    min_age: int = Field(default=0, ge=0, le=18)


class LineupRequest(PerformanceRequest):
    kind: Literal["lineup"]
    host: str = Field(min_length=1)
    acts: list[str]


class WorkshopRequest(PerformanceRequest):
    kind: Literal["workshop"]
    teacher: str = Field(min_length=1)
    max_participants: int = Field(ge=1)
    participants: list[str] = Field(default_factory=list)


PerformanceRequestBody = Annotated[
    SoloShowRequest | LineupRequest | WorkshopRequest,
    Field(discriminator="kind"),
]


@app.exception_handler(FestivalError)
def festival_error_handler(_: Request, error: FestivalError) -> JSONResponse:
    if isinstance(error, DataError):
        status_code = 500
    elif isinstance(error, NotFoundError):
        status_code = 404
    elif isinstance(error, ConflictError):
        status_code = 409
    elif isinstance(error, InvalidValueError):
        status_code = 422
    else:
        status_code = 422
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


@app.exception_handler(OSError)
def storage_error_handler(_: Request, error: OSError) -> JSONResponse:
    logger.error("Unable to read or write the festival data file: %s", error)
    return JSONResponse(
        status_code=500,
        content={"detail": "The festival data file could not be read or written."},
    )


@app.exception_handler(JSONDecodeError)
def invalid_data_file_handler(_: Request, error: JSONDecodeError) -> JSONResponse:
    logger.error("The festival data file contains invalid JSON: %s", error.msg)
    return JSONResponse(
        status_code=500,
        content={"detail": "The festival data file contains invalid JSON."},
    )


def make_performance(
    festival: Festival, request: PerformanceRequestBody
) -> Performance:
    return performance_from_data(
        request.model_dump(mode="json"),
        {venue.slug: venue for venue in festival.venues},
        {artist.slug: artist for artist in festival.artists},
    )


def create_app(storage: Storage | None = None) -> FastAPI:
    if storage is not None:
        app.state.storage = storage
    return app


@app.get("/api/festival")
def get_festival(request: Request) -> dict:
    festival = request.app.state.storage.load()
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
def list_venues(request: Request) -> list[dict]:
    festival = request.app.state.storage.load()
    return [venue.to_view() for venue in festival.venues]


@app.get("/api/artists")
def list_artists(request: Request) -> list[dict]:
    festival = request.app.state.storage.load()
    artists = sorted(festival.artists, key=lambda artist: artist.slug)
    return [artist.to_view() for artist in artists]


@app.get("/api/artists/{artist_slug}")
def get_artist(request: Request, artist_slug: str) -> dict:
    festival = request.app.state.storage.load()
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
def get_programme(
    request: Request, day: date | None = None, venue: str | None = None
) -> list[dict]:
    festival = request.app.state.storage.load()
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
def get_performance(request: Request, performance_id: str) -> dict:
    festival = request.app.state.storage.load()
    performance = festival.get_performance(performance_id)
    if performance is None:
        raise HTTPException(
            status_code=404,
            detail=f"No performance '{performance_id}'.",
        )
    return performance.to_view()


@app.get("/api/now")
def get_now(request: Request, at: datetime | None = None) -> dict:
    festival = request.app.state.storage.load()
    moment = at or datetime.now()
    return {
        "at": moment.isoformat(timespec="minutes"),
        "now_playing": [
            performance.to_view() for performance in festival.on_stage(moment)
        ],
        "up_next": [performance.to_view() for performance in festival.up_next(moment)],
    }


@app.post("/api/artists", status_code=201)
def create_artist(body: ArtistRequest, request: Request) -> dict:
    storage: Storage = request.app.state.storage
    festival = storage.load()
    artist = Artist(**body.model_dump())
    festival.add_artist(artist)
    storage.save(festival)
    return artist.to_view()


@app.post("/api/performances", status_code=201)
def create_performance(body: PerformanceRequestBody, request: Request) -> dict:
    storage: Storage = request.app.state.storage
    festival = storage.load()
    performance = make_performance(festival, body)
    festival.add_performance(performance)
    storage.save(festival)
    return performance.to_view()


@app.put("/api/performances/{performance_id}")
def update_performance(
    performance_id: str, body: PerformanceRequestBody, request: Request
) -> dict:
    storage: Storage = request.app.state.storage
    festival = storage.load()
    performance = make_performance(festival, body)
    updated = festival.update_performance(performance_id, performance)
    storage.save(festival)
    return updated.to_view()


@app.delete("/api/performances/{performance_id}", status_code=204)
def delete_performance(performance_id: str, request: Request) -> Response:
    storage: Storage = request.app.state.storage
    festival = storage.load()
    festival.cancel_performance(performance_id)
    storage.save(festival)
    return Response(status_code=204)


@app.post("/api/performances/{performance_id}/participants", status_code=201)
def create_participant(
    performance_id: str, body: ParticipantRequest, request: Request
) -> dict:
    storage: Storage = request.app.state.storage
    festival = storage.load()
    workshop = festival.register_participant(performance_id, body.name)
    storage.save(festival)
    return workshop.to_view()


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
