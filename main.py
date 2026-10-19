import json
import sys

from festival import (
    add_performance,
    cancel_performance,
    load_festival,
    show_artist,
    show_now,
    show_programme,
    show_summary,
    show_venues,
)


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
