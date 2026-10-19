import sys
from datetime import date, datetime
from pathlib import Path

import pytest

root = str(Path(__file__).parent.parent)
sys.path.insert(0, root)
try:
    from festival import Artist, Festival, Performance, Venue
finally:
    sys.path.remove(root)


@pytest.fixture
def festival() -> Festival:
    artists = [
        Artist("Host Artist", ""),
        Artist("Act Artist", ""),
        Artist("Solo Artist", ""),
        Artist("Teacher Artist", ""),
    ]
    venues = [
        Venue("First Hall", 100, "1 Main Street"),
        Venue("Second Hall", 50, "2 Main Street"),
    ]
    return Festival(
        name="Test Festival",
        first_day=date(2027, 6, 10),
        last_day=date(2027, 6, 13),
        venues=venues,
        artists=artists,
    )


def make_solo(
    festival: Festival,
    *,
    venue: Venue | None = None,
    artist: Artist | None = None,
    start: datetime = datetime(2027, 6, 10, 10, 0),
    duration: int = 60,
) -> Performance:
    return Performance(
        kind="solo",
        title="Solo Show",
        venue=venue or festival.venues[0],
        start=start,
        duration_minutes=duration,
        artist=artist or festival.artists[2],
        min_age=0,
    )


def test_rejects_performances_that_overlap_at_the_same_venue(
    festival: Festival,
) -> None:
    festival.add_performance(make_solo(festival))

    with pytest.raises(ValueError, match="First Hall is busy"):
        festival.add_performance(
            make_solo(festival, start=datetime(2027, 6, 10, 11, 15))
        )

    assert len(festival.performances) == 1


def test_rejects_artist_overlap_at_a_different_venue(festival: Festival) -> None:
    artist = festival.artists[2]
    festival.add_performance(make_solo(festival, artist=artist))

    with pytest.raises(ValueError, match="Solo Artist is on stage"):
        festival.add_performance(
            make_solo(
                festival,
                venue=festival.venues[1],
                artist=artist,
                start=datetime(2027, 6, 10, 11, 15),
            )
        )


def test_rejects_artist_overlap_when_artist_is_a_lineup_act(
    festival: Festival,
) -> None:
    act = festival.artists[1]
    lineup = Performance(
        kind="lineup",
        title="Lineup",
        venue=festival.venues[0],
        start=datetime(2027, 6, 10, 10, 0),
        duration_minutes=60,
        host=festival.artists[0],
        acts=[act, festival.artists[2]],
    )
    festival.add_performance(lineup)

    with pytest.raises(ValueError, match="Act Artist is on stage"):
        festival.add_performance(
            make_solo(
                festival,
                venue=festival.venues[1],
                artist=act,
                start=datetime(2027, 6, 10, 11, 15),
            )
        )


def test_one_am_performance_belongs_to_previous_festival_day(
    festival: Festival,
) -> None:
    performance = make_solo(
        festival,
        start=datetime(2027, 6, 12, 1, 0),
    )

    festival.add_performance(performance)

    assert performance.festival_day == date(2027, 6, 11)
    assert festival.performances_for_day(date(2027, 6, 11)) == [performance]


def test_rejects_performance_outside_festival_days(festival: Festival) -> None:
    with pytest.raises(ValueError, match="2027-06-09 is not a day of the festival"):
        festival.add_performance(make_solo(festival, start=datetime(2027, 6, 9, 10)))


@pytest.mark.parametrize("duration", [0, 361])
def test_rejects_duration_outside_allowed_range(
    festival: Festival, duration: int
) -> None:
    with pytest.raises(ValueError, match="Duration must be between 1 and 360"):
        festival.add_performance(make_solo(festival, duration=duration))


def test_rejects_unknown_venue(festival: Festival) -> None:
    with pytest.raises(ValueError, match="Unknown venue 'unknown-hall'"):
        festival.add_performance(
            make_solo(festival, venue=Venue("Unknown Hall", 10, "Nowhere"))
        )


def test_rejects_unknown_artist(festival: Festival) -> None:
    with pytest.raises(ValueError, match="Unknown artist 'unknown-artist'"):
        festival.add_performance(
            make_solo(festival, artist=Artist("Unknown Artist", ""))
        )


def test_now_queries_return_active_and_next_performances(festival: Festival) -> None:
    active = make_solo(festival, start=datetime(2027, 6, 10, 10, 0))
    upcoming = [
        make_solo(
            festival,
            venue=venue,
            artist=festival.artists[index],
            start=datetime(2027, 6, 10, hour, 0),
        )
        for venue, index, hour in [
            (festival.venues[1], 0, 12),
            (festival.venues[1], 1, 14),
            (festival.venues[1], 3, 16),
            (festival.venues[1], 2, 18),
        ]
    ]
    for performance in [active, *upcoming]:
        festival.add_performance(performance)

    moment = datetime(2027, 6, 10, 10, 30)
    assert festival.on_stage(moment) == [active]
    assert festival.up_next(moment) == upcoming[:3]
