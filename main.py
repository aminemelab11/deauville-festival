import json
import sys
import unicodedata
from datetime import datetime, date, timedelta
from pathlib import Path


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


def times_conflict(first: dict, second: dict) -> bool:
    gap = timedelta(minutes=30)

    first_start = start_of(first)
    first_end = end_of(first)
    second_start = start_of(second)
    second_end = end_of(second)

    return first_start < second_end + gap and second_start < first_end + gap


def performance_artists(performance: dict) -> list[str]:
    if performance["kind"] == "solo":
        return [performance["artist"]]

    if performance["kind"] == "lineup":
        return [performance["host"]] + performance["acts"]

    if performance["kind"] == "workshop":
        return [performance["teacher"]]

    return []


def load_festival() -> dict:
    with Path("data/festival.json").open(encoding="utf-8") as file:
        return json.load(file)


def save_festival(festival: dict) -> None:
    with Path("data/festival.json").open("w", encoding="utf-8") as file:
        json.dump(festival, file, ensure_ascii=False, indent=2)
        file.write("\n")


def find_venue(festival: dict, venue_slug: str) -> dict | None:
    for venue in festival["venues"]:
        if slug(venue["name"]) == venue_slug:
            return venue

    return None


def find_artist(festival: dict, artist_slug: str) -> dict | None:
    for artist in festival["artists"]:
        if slug(artist["name"]) == artist_slug:
            return artist

    return None


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


def get_programme(festival: dict, day: str) -> list[dict]:
    selected_day = parse_day(day)

    performances = []

    for performance in festival["performances"]:
        if festival_day(performance) == selected_day:
            performances.append(performance)

    return sorted(performances, key=start_of)


def performance_id(performance: dict) -> str:
    start = start_of(performance)
    return f"{performance['venue']}-{start:%Y-%m-%d-%H%M}"


def validate_performance(festival: dict, new_performance: dict) -> None:
    venue = find_venue(festival, new_performance["venue"])

    if venue is None:
        raise ValueError(f"Unknown venue '{new_performance['venue']}'.")

    for artist_slug in performance_artists(new_performance):
        if find_artist(festival, artist_slug) is None:
            raise ValueError(f"Unknown artist '{artist_slug}'.")

    duration = new_performance["duration_minutes"]

    if not 1 <= duration <= 360:
        raise ValueError("Duration must be between 1 and 360 minutes.")

    day = festival_day(new_performance)
    first_day = date.fromisoformat(festival["first_day"])
    last_day = date.fromisoformat(festival["last_day"])

    if not first_day <= day <= last_day:
        raise ValueError(f"{day} is not a day of the festival.")

    for existing in festival["performances"]:
        if not times_conflict(existing, new_performance):
            continue

        if existing["venue"] == new_performance["venue"]:
            start = start_of(existing)
            end = end_of(existing)

            raise ValueError(
                f"{venue['name']} is busy with {existing['title']} "
                f"({start:%Y-%m-%d %H:%M}-{end:%H:%M})."
            )

        for artist_slug in performance_artists(new_performance):
            if artist_slug in performance_artists(existing):
                artist = find_artist(festival, artist_slug)

                raise ValueError(
                    f"{artist['name']} is on stage in {existing['title']}."
                )


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
    selected_day = parse_day(day)

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
        raise ValueError(f"No artist '{artist_slug}'.")

    print(artist["name"])

    for performance in sorted(festival["performances"], key=start_of):
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
    at = parse_moment(moment)

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


def add_performance(festival: dict) -> None:
    title = input("Title: ").strip()
    artist = input("Artist (slug): ").strip()
    venue = input("Venue (slug): ").strip()
    start_text = input("Start (YYYY-MM-DDTHH:MM): ").strip()
    duration_text = input("Duration (minutes): ").strip()

    if not title:
        raise ValueError("The performance title cannot be empty.")

    if not duration_text.isdigit():
        raise ValueError(f"'{duration_text}' is not a number of minutes.")

    duration = int(duration_text)
    start = parse_moment(start_text)

    performance = {
        "kind": "solo",
        "title": title,
        "artist": artist,
        "venue": venue,
        "start": start.isoformat(timespec="minutes"),
        "duration_minutes": duration,
        "description": "",
        "min_age": 0,
    }

    validate_performance(festival, performance)

    festival["performances"].append(performance)
    save_festival(festival)

    print(f"Added: {performance_id(performance)}")


def cancel_performance(festival: dict, requested_id: str) -> None:
    for performance in festival["performances"]:
        if performance_id(performance) == requested_id:
            festival["performances"].remove(performance)
            save_festival(festival)

            print(f"Cancelled: {performance['title']}")
            return

    raise ValueError(f"Unknown performance '{requested_id}'.")


def show_usage() -> None:
    print("Usage:")
    print("  uv run main.py")
    print("  uv run main.py venues")
    print("  uv run main.py programme YYYY-MM-DD")
    print("  uv run main.py artist ARTIST-SLUG")
    print("  uv run main.py now YYYY-MM-DDTHH:MM")
    print("  uv run main.py add")
    print("  uv run main.py cancel PERFORMANCE-ID")


def main() -> None:
    try:
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

        elif len(sys.argv) == 2 and sys.argv[1] == "add":
            add_performance(festival)

        elif len(sys.argv) == 3 and sys.argv[1] == "cancel":
            cancel_performance(festival, sys.argv[2])

        else:
            show_usage()
            sys.exit(1)

    except FileNotFoundError as error:
        print(f"Error: File not found: {error.filename}")
        sys.exit(1)

    except json.JSONDecodeError as error:
        print(f"Error: Invalid JSON data: {error.msg}.")
        sys.exit(1)

    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(1)

    except OSError as error:
        print(f"Error: File operation failed: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
