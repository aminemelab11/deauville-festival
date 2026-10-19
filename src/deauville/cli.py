from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from deauville.api import create_app
from deauville.festival import (
    FestivalError,
    add_performance,
    cancel_performance,
    show_artist,
    show_now,
    show_programme,
    show_summary,
    show_venues,
)
from deauville.storage import JsonFileStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deauville")
    parser.add_argument("--data", type=Path, default=Path("data/festival.json"))
    commands = parser.add_subparsers(dest="command")

    for name in ("venues", "add"):
        command_parser = commands.add_parser(name)
        command_parser.add_argument("--data", type=Path, default=argparse.SUPPRESS)

    programme_parser = commands.add_parser("programme")
    programme_parser.add_argument("day")
    programme_parser.add_argument("--data", type=Path, default=argparse.SUPPRESS)

    artist_parser = commands.add_parser("artist")
    artist_parser.add_argument("slug")
    artist_parser.add_argument("--data", type=Path, default=argparse.SUPPRESS)

    now_parser = commands.add_parser("now")
    now_parser.add_argument("moment")
    now_parser.add_argument("--data", type=Path, default=argparse.SUPPRESS)

    cancel_parser = commands.add_parser("cancel")
    cancel_parser.add_argument("performance_id")
    cancel_parser.add_argument("--data", type=Path, default=argparse.SUPPRESS)

    serve_parser = commands.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--data", type=Path, default=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    storage = JsonFileStorage(args.data)

    try:
        if args.command == "serve":
            uvicorn.run(create_app(storage), host=args.host, port=args.port)
            return

        festival = storage.load()
        if args.command is None:
            show_summary(festival)
        elif args.command == "venues":
            show_venues(festival)
        elif args.command == "programme":
            show_programme(festival, args.day)
        elif args.command == "artist":
            show_artist(festival, args.slug)
        elif args.command == "now":
            show_now(festival, args.moment)
        elif args.command == "add":
            add_performance(festival)
            storage.save(festival)
        elif args.command == "cancel":
            cancel_performance(festival, args.performance_id)
            storage.save(festival)
    except FileNotFoundError as error:
        print(f"Error: File not found: {error.filename}")
        sys.exit(1)
    except FestivalError as error:
        print(f"Error: {error}")
        sys.exit(1)
    except OSError as error:
        print(f"Error: File operation failed: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
