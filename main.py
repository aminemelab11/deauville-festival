import json
import sys
from pathlib import Path
import unicodedata
from datetime import datetime, date, timedelta


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()

    text = "".join(char for char in text if char.isalnum() or char.isspace())

    return "-".join(text.split())


def start_of(performance: dict) -> datetime:
    return datetime.fromisoformat(performance["start"])


def end_of(performance: dict) -> datetime:
    return start_of(performance) + timedelta(minutes=performance["duration_minutes"])


def festival_day(performance: dict) -> date:
    return (start_of(performance) - timedelta(hours=6)).date()


def load_festival() -> dict:
    with Path("data/festival.json").open(encoding="utf-8") as file:
        return json.load(file)


def find_venue(festival: dict, venue_slug: str) -> dict | None:
    for venue in festival["venues"]:
        if slug(venue["name"]) == venue_slug:
            return venue

    return None


def get_programme(festival: dict, day: str) -> list[dict]:
    selected_day = date.fromisoformat(day)

    performances = []

    for performance in festival["performances"]:
        if festival_day(performance) == selected_day:
            performances.append(performance)

    return sorted(performances, key=start_of)


def find_artist(festival: dict, artist_slug: str) -> dict | None:
    for artist in festival["artists"]:
        if slug(artist["name"]) == artist_slug:
            return artist

    return None


def show_summary(festival: dict) -> None:
    print(festival["name"])
    print(f"From {festival['first_day']} to {festival['last_day']}")
    print(
        f"{len(festival['venues'])} venues, "
        f"{len(festival['artists'])} artists, "
        f"{len(festival['performances'])} performances"
    )


def show_venues(festival: dict) -> None:
    total_seats = 0

    for venue in festival["venues"]:
        print(f"{slug(venue['name'])}: {venue['name']}, {venue['capacity']} seats")
        total_seats += venue["capacity"]

    print(f"Total: {total_seats} seats")


def show_programme(festival: dict, day: str) -> None:
    selected_day = date.fromisoformat(day)

    print(f"Programme for {selected_day:%A %d %B}:")

    for performance in get_programme(festival, day):
        start = start_of(performance)
        end = end_of(performance)
        venue = find_venue(festival, performance["venue"])

        print(
            f"{start:%H:%M}-{end:%H:%M} | {venue['name']} | "
            f"{performance['title']} ({performance['kind']})"
        )


def show_artist(festival: dict, artist_slug: str) -> None:
    artist = find_artist(festival, artist_slug)

    if artist is None:
        print(f"No artist '{artist_slug}'.")
        return

    print(artist["name"])

    for performance in festival["performances"]:
        roles = []

        if performance["kind"] == "solo" and performance["artist"] == artist_slug:
            roles.append("solo")

        elif performance["kind"] == "lineup":
            if performance["host"] == artist_slug:
                roles.append("host")

            if artist_slug in performance["acts"]:
                roles.append("act")

        elif (
            performance["kind"] == "workshop" and performance["teacher"] == artist_slug
        ):
            roles.append("teacher")

        for role in roles:
            start = start_of(performance)
            end = end_of(performance)
            day = festival_day(performance)
            venue = find_venue(festival, performance["venue"])

            print(
                f"{day:%a %d} {start:%H:%M}-{end:%H:%M} | "
                f"{venue['name']} | {performance['title']} ({role})"
            )


def show_now(festival: dict, moment: str) -> None:
    at = datetime.fromisoformat(moment)

    on_stage = []
    upcoming = []

    for performance in festival["performances"]:
        start = start_of(performance)
        end = end_of(performance)

        if start <= at < end:
            on_stage.append(performance)

        elif start > at:
            upcoming.append(performance)

    on_stage = sorted(on_stage, key=start_of)
    upcoming = sorted(upcoming, key=start_of)[:3]

    print(f"On stage at {at:%Y-%m-%d %H:%M}:")

    for performance in on_stage:
        venue = find_venue(festival, performance["venue"])
        end = end_of(performance)

        print(f"- {performance['title']} at {venue['name']}, until {end:%H:%M}")

    print("Up next:")

    for performance in upcoming:
        venue = find_venue(festival, performance["venue"])
        start = start_of(performance)
        end = end_of(performance)

        print(
            f"- {start:%H:%M}-{end:%H:%M} | {venue['name']} | "
            f"{performance['title']} ({performance['kind']})"
        )


def main() -> None:
    festival = load_festival()

    if len(sys.argv) == 1:
        show_summary(festival)

    elif len(sys.argv) == 2 and sys.argv[1] == "venues":
        show_venues(festival)

    elif len(sys.argv) == 3 and sys.argv[1] == "programme":
        show_programme(festival, sys.argv[2])

    elif len(sys.argv) == 3 and sys.argv[1] == "artist":
        show_artist(festival, sys.argv[2])

    elif len(sys.argv) == 3 and sys.argv[1] == "now":
        show_now(festival, sys.argv[2])

    else:
        print("Usage:")
        print("  uv run main.py")
        print("  uv run main.py venues")
        print("  uv run main.py programme YYYY-MM-DD")
        print("  uv run main.py artist ARTIST-SLUG")
        print("  uv run main.py now YYYY-MM-DDTHH:MM")


if __name__ == "__main__":
    main()
