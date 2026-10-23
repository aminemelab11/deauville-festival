# Object-Oriented Programming in Python - the project track

ECE Paris - 2026-2027

You learn Python by building one project, from the first line to a web
platform: the programme of the **Deauville Festival du Rire** (10-13 June
2027). The website is given; behind it, everything is yours. Each step adds
one thing that works, and brings the notion that makes it possible.

This repository holds the **sheets** of the steps and small **side examples**
on other subjects (a library, buses, a bank…). They show a technique; your
project is where you use it. Your code lives in **your own repository**,
started from the starter at step 00.

A second repository, the **practice repository**, holds more examples
(notebooks) and exercises with tests for each block. It is optional: use it
when a notion needs more practice. Each sheet ends with the matching part.

## The steps

| Block | Step                                                       | At the end of the step                                       |
| ----- | ---------------------------------------------------------- | ------------------------------------------------------------ |
| B1    | [00 Start](B1/E00_start.md)                                | the project runs and prints a summary of the festival        |
|       | [01 Explore](B1/E01_explore.md)                            | six questions about the data, answered by loops              |
|       | [02 The programme of a day](B1/E02_ask_a_day.md)           | the user asks for a day, gets its programme (with a bug)     |
| B2    | [03 Functions and commands](B2/E03_functions.md)           | `main.py programme 2027-06-11`, on GitHub                    |
|       | [04 Real dates and times](B2/E04_time.md)                  | the night belongs to the right day; what is on stage now     |
|       | [05 Rules, errors and saving](B2/E05_errors_and_saving.md) | adding a show checks the rules and saves the file            |
| B3    | [06 The website lights up](B3/E06_first_routes.md)         | a server; the website shows days, venues, artists            |
|       | [07 The first classes](B3/E07_classes.md)                  | the programme and the artist pages appear                    |
|       | [08 The festival object](B3/E08_festival_object.md)        | "on stage now" appears; tests prove every rule               |
| B4    | [09 Three kinds](B4/E09_three_kinds.md)                    | solo shows, lineups, workshops: one family, no `if kind ==`  |
|       | [10 The admin](B4/E10_admin.md)                            | organisers schedule, move, cancel; nobody bypasses the rules |
|       | [11 A real package](B4/E11_package.md)                     | `uv run deauville serve`, `uv build`                         |
| B5    | [12 The whole contract](B5/E12_full_contract.md)           | all of `API.md`, tested                                      |
|       | [13 Ship it](B5/E13_ship.md)                               | a fresh clone runs; your README explains your structure      |

## Project model (Steps 07-10)

- `Venue` and `Artist` hold the fields loaded from the JSON file and compute
  their stable slugs from their names.
- Abstract `Performance` holds the fields and calculations shared by every
  show: end time, festival day, identifier, and common API view fields.
  `SoloShow`, `Lineup`, and `Workshop` each provide their own artists, roles,
  summary, kind-specific fields, and validation.
- `Festival` owns the venue, artist, and private performance collections. Its
  methods are the only way to add, move, cancel, or register participants,
  enforcing scheduling and capacity rules for both the CLI and API. Its
  collections are exposed as read-only tuples. The JSON loader selects the
  performance subclass from each record's `kind`, then builds the object graph
  shared by the command line and API.
- `FestivalError` and its not-found, conflict, and invalid-value subclasses let
  the API map domain refusals to HTTP statuses in one handler. Pydantic request
  models validate admin bodies; successful changes are atomically saved.

## Package and storage (Step 11)

The application lives in `src/deauville/`: `festival.py` contains the domain
model, `storage.py` defines the storage interface and JSON/in-memory
implementations, `api.py` exposes the HTTP routes, and `cli.py` provides the
`deauville` command. The API and CLI receive a `Storage`; festival rules do not
depend on JSON or file paths.

Run `uv sync`, then use `uv run deauville programme 2027-06-11` or
`uv run deauville serve`. Both commands accept `--data PATH` before or after
the subcommand; the default is `data/festival.json`. Run `uv run pytest` for
the tests and `uv build` to build the wheel. The API is created with
`create_app(storage)`, so HTTP tests use an isolated copy of the festival data
in pytest's temporary directory rather than changing the project data file.

Each block README lists its steps and side examples: [B1](B1/README.md),
[B2](B2/README.md), [B3](B3/README.md), [B4](B4/README.md),
[B5](B5/README.md).

## How a step works

Each sheet has the same parts:

- **At the end**: what works when the step is done, seen from outside (an
  output in the terminal, a page of the website).
- **Why now**: what the previous version cannot do. The notion of the step
  answers it.
- **Learn**: the notion, short, and the side examples.
- **Do**: what to build. It says _what_ must work, never _which_ functions or
  classes to write: the structure of your project is your work, and you
  defend it at the oral.
- **Check**: the exact output, or what the website must show. No tests are
  given: from step 08, you write your own.

Steps not finished in class are finished at home before the next block: each
block starts where the previous one ended.

## Setup

1. Install uv:
   - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell):
     `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

   Close the terminal, open a new one, check with `uv --version`.

2. Install VS Code with the extensions _Python_ (Microsoft) and _Ruff_
   (Astral). Keep your folders outside OneDrive.
3. Open this folder in VS Code, then a terminal (`Terminal > New Terminal`),
   and run `uv sync`.
4. Side examples run from this folder:

   ```bash
   uv run python B1/side/e00_playlist.py
   ```

Then [step 00](B1/E00_start.md) creates your project, in its own folder.

## Known bugs

- **Festival day boundary — Fixed in Step 04:** Performances
  starting before 06:00 are now assigned to the previous festival
  day. For example, "After Hours" starts at 01:00 on 12 June
  but correctly appears in Friday's programme (11 June).