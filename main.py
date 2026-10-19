import json
import sys
from pathlib import Path
import unicodedata


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()

    text = "".join(char for char in text if char.isalnum() or char.isspace())

    return "-".join(text.split())


def load_festival() -> dict:
    with Path("data/festival.json").open(encoding="utf-8") as file:
        return json.load(file)


def find_venue(festival: dict, venue_slug: str) -> dict | None:
    for venue in festival["venues"]:
        if slug(venue["name"]) == venue_slug:
            return venue

    return None


def get_programme(festival: dict, day: str) -> list[dict]:
    performances = []

    for performance in festival["performances"]:
        if performance["start"][:10] == day:
            performances.append(performance)

    return performances


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
    print(f"Programme for {day}:")

    for performance in get_programme(festival, day):
        time = performance["start"][11:]
        venue = find_venue(festival, performance["venue"])

        print(
            f"{time} | {venue['name']} | {performance['title']} ({performance['kind']})"
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
            start = performance["start"].replace("T", " ")
            venue = find_venue(festival, performance["venue"])

            print(f"{start} | {venue['name']} | {performance['title']} ({role})")


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

    else:
        print("Usage:")
        print("  uv run main.py")
        print("  uv run main.py venues")
        print("  uv run main.py programme YYYY-MM-DD")
        print("  uv run main.py artist ARTIST-SLUG")


if __name__ == "__main__":
    main()
