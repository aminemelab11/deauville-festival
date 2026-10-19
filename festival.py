from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = "".join(char for char in text if char.isalnum() or char.isspace())
    return "-".join(text.split())


@dataclass
class Venue:
    name: str
    capacity: int
    address: str

    @property
    def slug(self) -> str:
        return slug(self.name)

    def to_view(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "capacity": self.capacity,
            "address": self.address,
        }


@dataclass
class Artist:
    name: str
    bio: str
    photo_url: str = ""

    @property
    def slug(self) -> str:
        return slug(self.name)

    def to_view(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "bio": self.bio,
            "photo_url": self.photo_url,
        }


@dataclass
class Performance:
    kind: str
    title: str
    venue: Venue
    start: datetime
    duration_minutes: int
    description: str = ""
    artist: Artist | None = None
    min_age: int | None = None
    host: Artist | None = None
    acts: list[Artist] = field(default_factory=list)
    teacher: Artist | None = None
    max_participants: int | None = None
    participants: list[str] = field(default_factory=list)

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.duration_minutes)

    @property
    def festival_day(self) -> date:
        return (self.start - timedelta(hours=6)).date()

    @property
    def id(self) -> str:
        return f"{self.venue.slug}-{self.start:%Y-%m-%d-%H%M}"

    @property
    def artists(self) -> list[Artist]:
        if self.kind == "solo":
            return [self.artist] if self.artist else []
        if self.kind == "lineup":
            return ([self.host] if self.host else []) + self.acts
        if self.kind == "workshop":
            return [self.teacher] if self.teacher else []
        return []

    @property
    def capacity(self) -> int:
        if self.kind == "workshop" and self.max_participants is not None:
            return min(self.max_participants, self.venue.capacity)
        return self.venue.capacity

    @property
    def places_left(self) -> int | None:
        if self.kind != "workshop" or self.max_participants is None:
            return None
        return max(0, self.capacity - len(self.participants))

    def involves(self, artist: Artist) -> bool:
        return artist in self.artists

    def roles_for(self, artist: Artist) -> list[str]:
        roles = []
        if self.kind == "solo" and self.artist == artist:
            roles.append("solo")
        elif self.kind == "lineup":
            if self.host == artist:
                roles.append("host")
            if artist in self.acts:
                roles.append("act")
        elif self.kind == "workshop" and self.teacher == artist:
            roles.append("teacher")
        return roles

    def summary(self) -> str:
        if self.kind == "solo" and self.artist:
            return f"with {self.artist.name}"
        if self.kind == "lineup":
            host = f"hosted by {self.host.name}" if self.host else "lineup"
            acts = ", ".join(artist.name for artist in self.acts)
            return f"{host}, with {acts}" if acts else host
        if self.kind == "workshop" and self.teacher:
            return f"taught by {self.teacher.name}"
        return ""

    def to_view(self) -> dict:
        view = {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue.slug,
            "venue_name": self.venue.name,
            "start": self.start.isoformat(timespec="minutes"),
            "end": self.end.isoformat(timespec="minutes"),
            "duration_minutes": self.duration_minutes,
            "festival_day": self.festival_day.isoformat(),
            "description": self.description,
            "summary": self.summary(),
            "capacity": self.capacity,
            "artists": [
                {"slug": artist.slug, "name": artist.name} for artist in self.artists
            ],
        }
        if self.kind == "solo":
            view.update(
                artist=self.artist.slug if self.artist else None,
                min_age=self.min_age,
            )
        elif self.kind == "lineup":
            view.update(
                host=self.host.slug if self.host else None,
                acts=[artist.slug for artist in self.acts],
            )
        elif self.kind == "workshop":
            view.update(
                teacher=self.teacher.slug if self.teacher else None,
                max_participants=self.max_participants,
                participants=self.participants.copy(),
                places_left=self.places_left,
            )
        return view

    def to_data(self) -> dict:
        performance = {
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue.slug,
            "start": self.start.isoformat(timespec="minutes"),
            "duration_minutes": self.duration_minutes,
            "description": self.description,
        }
        if self.kind == "solo":
            performance.update(
                artist=self.artist.slug if self.artist else "",
                min_age=self.min_age if self.min_age is not None else 0,
            )
        elif self.kind == "lineup":
            performance.update(
                host=self.host.slug if self.host else "",
                acts=[artist.slug for artist in self.acts],
            )
        elif self.kind == "workshop":
            performance.update(
                teacher=self.teacher.slug if self.teacher else "",
                max_participants=self.max_participants,
                participants=self.participants.copy(),
            )
        return performance


@dataclass
class Festival:
    name: str
    first_day: date
    last_day: date
    venues: list[Venue]
    artists: list[Artist]
    performances: list[Performance]

    @property
    def days(self) -> list[date]:
        return [
            self.first_day + timedelta(days=offset)
            for offset in range((self.last_day - self.first_day).days + 1)
        ]

    def get_venue(self, venue_slug: str) -> Venue | None:
        return next((venue for venue in self.venues if venue.slug == venue_slug), None)

    def get_artist(self, artist_slug: str) -> Artist | None:
        return next(
            (artist for artist in self.artists if artist.slug == artist_slug), None
        )

    def get_performance(self, performance_id: str) -> Performance | None:
        return next(
            (
                performance
                for performance in self.performances
                if performance.id == performance_id
            ),
            None,
        )

    def ordered_performances(self) -> list[Performance]:
        return sorted(
            self.performances,
            key=lambda performance: (performance.start, performance.venue.name),
        )

    def performances_for_day(self, selected_day: date) -> list[Performance]:
        return [
            performance
            for performance in self.ordered_performances()
            if performance.festival_day == selected_day
        ]

    def performances_for_artist(self, artist: Artist) -> list[Performance]:
        return [
            performance
            for performance in self.ordered_performances()
            if performance.involves(artist)
        ]

    def to_data(self) -> dict:
        return {
            "name": self.name,
            "first_day": self.first_day.isoformat(),
            "last_day": self.last_day.isoformat(),
            "venues": [
                {
                    "name": venue.name,
                    "capacity": venue.capacity,
                    "address": venue.address,
                }
                for venue in self.venues
            ],
            "artists": [
                {
                    "name": artist.name,
                    "bio": artist.bio,
                    "photo_url": artist.photo_url,
                }
                for artist in self.artists
            ],
            "performances": [
                performance.to_data() for performance in self.performances
            ],
        }


def performance_from_data(
    data: dict, venues: dict[str, Venue], artists: dict[str, Artist]
) -> Performance:
    kind = data["kind"]
    performance = Performance(
        kind=kind,
        title=data["title"],
        venue=venues[data["venue"]],
        start=datetime.fromisoformat(data["start"]),
        duration_minutes=data["duration_minutes"],
        description=data.get("description", ""),
    )
    if kind == "solo":
        performance.artist = artists[data["artist"]]
        performance.min_age = data.get("min_age", 0)
    elif kind == "lineup":
        performance.host = artists[data["host"]]
        performance.acts = [artists[artist_slug] for artist_slug in data["acts"]]
    elif kind == "workshop":
        performance.teacher = artists[data["teacher"]]
        performance.max_participants = data["max_participants"]
        performance.participants = data.get("participants", []).copy()
    return performance


def festival_from_data(data: dict) -> Festival:
    venues = [Venue(**venue) for venue in data["venues"]]
    artists = [
        Artist(
            name=artist["name"],
            bio=artist.get("bio", ""),
            photo_url=artist.get("photo_url", ""),
        )
        for artist in data["artists"]
    ]
    venue_lookup = {venue.slug: venue for venue in venues}
    artist_lookup = {artist.slug: artist for artist in artists}
    performances = [
        performance_from_data(performance, venue_lookup, artist_lookup)
        for performance in data["performances"]
    ]
    return Festival(
        name=data["name"],
        first_day=date.fromisoformat(data["first_day"]),
        last_day=date.fromisoformat(data["last_day"]),
        venues=venues,
        artists=artists,
        performances=performances,
    )


def load_festival() -> Festival:
    with Path("data/festival.json").open(encoding="utf-8") as file:
        return festival_from_data(json.load(file))


def save_festival(festival: Festival) -> None:
    with Path("data/festival.json").open("w", encoding="utf-8") as file:
        json.dump(festival.to_data(), file, ensure_ascii=False, indent=2)
        file.write("\n")


def start_of(performance: Performance) -> datetime:
    return performance.start


def end_of(performance: Performance) -> datetime:
    return performance.end


def festival_day(performance: Performance) -> date:
    return performance.festival_day


def times_conflict(first: Performance, second: Performance) -> bool:
    gap = timedelta(minutes=30)
    return first.start < second.end + gap and second.start < first.end + gap


def performance_artists(performance: Performance) -> list[str]:
    return [artist.slug for artist in performance.artists]


def find_venue(festival: Festival, venue_slug: str) -> Venue | None:
    return festival.get_venue(venue_slug)


def find_artist(festival: Festival, artist_slug: str) -> Artist | None:
    return festival.get_artist(artist_slug)


def parse_day(text: str) -> date:
    if (
        len(text) != 10
        or text[4] != "-"
        or text[7] != "-"
        or not (text[:4] + text[5:7] + text[8:]).isdigit()
    ):
        raise ValueError(f"'{text}' is not a day, use YYYY-MM-DD.")
    return date.fromisoformat(text)


def parse_moment(text: str) -> datetime:
    if (
        len(text) != 16
        or text[4] != "-"
        or text[7] != "-"
        or text[10] != "T"
        or text[13] != ":"
        or not (text[:4] + text[5:7] + text[8:10] + text[11:13] + text[14:]).isdigit()
    ):
        raise ValueError(f"'{text}' is not a valid moment, use YYYY-MM-DDTHH:MM.")
    return datetime.fromisoformat(text)


def get_programme(festival: Festival, day: str) -> list[Performance]:
    return festival.performances_for_day(parse_day(day))


def performance_id(performance: Performance) -> str:
    return performance.id


def validate_performance(festival: Festival, performance: Performance) -> None:
    if festival.get_venue(performance.venue.slug) is None:
        raise ValueError(f"Unknown venue '{performance.venue.slug}'.")

    for artist in performance.artists:
        if festival.get_artist(artist.slug) is None:
            raise ValueError(f"Unknown artist '{artist.slug}'.")

    if not 1 <= performance.duration_minutes <= 360:
        raise ValueError("Duration must be between 1 and 360 minutes.")

    if not festival.first_day <= performance.festival_day <= festival.last_day:
        raise ValueError(f"{performance.festival_day} is not a day of the festival.")

    for existing in festival.performances:
        if not times_conflict(existing, performance):
            continue
        if existing.venue.slug == performance.venue.slug:
            raise ValueError(
                f"{performance.venue.name} is busy with {existing.title} "
                f"({existing.start:%Y-%m-%d %H:%M}-{existing.end:%H:%M})."
            )
        for artist in performance.artists:
            if existing.involves(artist):
                raise ValueError(f"{artist.name} is on stage in {existing.title}.")


def show_summary(festival: Festival) -> None:
    print(festival.name)
    print(f"From {festival.first_day} to {festival.last_day}")
    print(
        f"{len(festival.venues)} venues, "
        f"{len(festival.artists)} artists, "
        f"{len(festival.performances)} performances"
    )


def show_venues(festival: Festival) -> None:
    total_seats = 0
    for venue in festival.venues:
        print(f"{venue.slug}: {venue.name}, {venue.capacity} seats")
        total_seats += venue.capacity
    print(f"Total: {total_seats} seats")


def show_programme(festival: Festival, day: str) -> None:
    selected_day = parse_day(day)
    print(f"Programme for {selected_day:%A %d %B}:")
    for performance in festival.performances_for_day(selected_day):
        print(
            f"{performance.start:%H:%M}-{performance.end:%H:%M} | "
            f"{performance.venue.name} | {performance.title} ({performance.kind})"
        )


def show_artist(festival: Festival, artist_slug: str) -> None:
    artist = festival.get_artist(artist_slug)
    if artist is None:
        raise ValueError(f"No artist '{artist_slug}'.")
    print(artist.name)
    for performance in festival.performances_for_artist(artist):
        for role in performance.roles_for(artist):
            print(
                f"{performance.festival_day:%a %d} "
                f"{performance.start:%H:%M}-{performance.end:%H:%M} | "
                f"{performance.venue.name} | {performance.title} ({role})"
            )


def show_now(festival: Festival, moment: str) -> None:
    at = parse_moment(moment)
    on_stage = [
        performance
        for performance in festival.performances
        if performance.start <= at < performance.end
    ]
    upcoming = sorted(
        (
            performance
            for performance in festival.performances
            if performance.start > at
        ),
        key=lambda performance: (performance.start, performance.venue.name),
    )[:3]
    print(f"On stage at {at:%Y-%m-%d %H:%M}:")
    for performance in on_stage:
        print(
            f"- {performance.title} at {performance.venue.name}, "
            f"until {performance.end:%H:%M}"
        )
    print("Up next:")
    for performance in upcoming[:3]:
        print(
            f"- {performance.start:%H:%M}-{performance.end:%H:%M} | "
            f"{performance.venue.name} | {performance.title} ({performance.kind})"
        )


def add_performance(festival: Festival) -> None:
    title = input("Title: ").strip()
    artist_slug = input("Artist (slug): ").strip()
    venue_slug = input("Venue (slug): ").strip()
    start_text = input("Start (YYYY-MM-DDTHH:MM): ").strip()
    duration_text = input("Duration (minutes): ").strip()
    if not title:
        raise ValueError("The performance title cannot be empty.")
    if not duration_text.isdigit():
        raise ValueError(f"'{duration_text}' is not a number of minutes.")
    venue = festival.get_venue(venue_slug)
    if venue is None:
        raise ValueError(f"Unknown venue '{venue_slug}'.")
    artist = festival.get_artist(artist_slug)
    if artist is None:
        raise ValueError(f"Unknown artist '{artist_slug}'.")
    performance = Performance(
        kind="solo",
        title=title,
        venue=venue,
        start=parse_moment(start_text),
        duration_minutes=int(duration_text),
        description="",
        artist=artist,
        min_age=0,
    )
    validate_performance(festival, performance)
    festival.performances.append(performance)
    save_festival(festival)
    print(f"Added: {performance.id}")


def cancel_performance(festival: Festival, requested_id: str) -> None:
    performance = festival.get_performance(requested_id)
    if performance is None:
        raise ValueError(f"Unknown performance '{requested_id}'.")
    festival.performances.remove(performance)
    save_festival(festival)
    print(f"Cancelled: {performance.title}")
