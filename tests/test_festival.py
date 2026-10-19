import sys
from datetime import date, datetime
from pathlib import Path

import pytest

root = str(Path(__file__).parent.parent)
sys.path.insert(0, root)
try:
    from festival import (
        Artist,
        Festival,
        Lineup,
        Performance,
        SoloShow,
        Venue,
        Workshop,
        load_festival,
    )
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
) -> SoloShow:
    return SoloShow(
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
    lineup = Lineup(
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


def test_festival_and_kind_collections_are_read_only(festival: Festival) -> None:
    lineup = Lineup(
        title="Lineup",
        venue=festival.venues[0],
        start=datetime(2027, 6, 10, 10),
        duration_minutes=60,
        host=festival.artists[0],
        acts=[festival.artists[1], festival.artists[2]],
    )
    workshop = Workshop(
        title="Workshop",
        venue=festival.venues[0],
        start=datetime(2027, 6, 10, 12),
        duration_minutes=60,
        teacher=festival.artists[3],
        max_participants=10,
    )

    with pytest.raises(AttributeError):
        festival.performances.append(make_solo(festival))
    with pytest.raises(AttributeError):
        festival.artists.append(Artist("Extra Artist", ""))
    with pytest.raises(AttributeError):
        lineup.acts.append(festival.artists[3])
    with pytest.raises(AttributeError):
        workshop.participants.append("New participant")
    with pytest.raises(TypeError):
        Festival(
            name=festival.name,
            first_day=festival.first_day,
            last_day=festival.last_day,
            venues=festival.venues,
            artists=festival.artists,
            _performances=[make_solo(festival)],
        )


@pytest.mark.parametrize("min_age", [-1, 19])
def test_solo_rejects_minimum_age_outside_range(
    festival: Festival, min_age: int
) -> None:
    with pytest.raises(ValueError, match="Minimum age must be between 0 and 18"):
        SoloShow(
            title="Age-restricted show",
            venue=festival.venues[0],
            start=datetime(2027, 6, 10, 10),
            duration_minutes=60,
            artist=festival.artists[2],
            min_age=min_age,
        )


def test_lineup_requires_at_least_two_acts(festival: Festival) -> None:
    with pytest.raises(ValueError, match="at least two acts"):
        Lineup(
            title="Too Small",
            venue=festival.venues[0],
            start=datetime(2027, 6, 10, 10),
            duration_minutes=60,
            host=festival.artists[0],
            acts=[festival.artists[1]],
        )


def test_lineup_requires_unique_acts(festival: Festival) -> None:
    with pytest.raises(ValueError, match="cannot include an act more than once"):
        Lineup(
            title="Repeated Act",
            venue=festival.venues[0],
            start=datetime(2027, 6, 10, 10),
            duration_minutes=60,
            host=festival.artists[0],
            acts=[festival.artists[1], festival.artists[1]],
        )


def test_lineup_host_cannot_be_an_act(festival: Festival) -> None:
    with pytest.raises(ValueError, match="host cannot also be an act"):
        Lineup(
            title="Host as Act",
            venue=festival.venues[0],
            start=datetime(2027, 6, 10, 10),
            duration_minutes=60,
            host=festival.artists[0],
            acts=[festival.artists[0], festival.artists[1]],
        )


def test_three_act_lineup_needs_36_minutes(festival: Festival) -> None:
    lineup_fields = {
        "title": "Three Act Lineup",
        "venue": festival.venues[0],
        "start": datetime(2027, 6, 10, 10),
        "host": festival.artists[0],
        "acts": [festival.artists[1], festival.artists[2], festival.artists[3]],
    }
    with pytest.raises(ValueError, match="must last at least 36 minutes"):
        Lineup(duration_minutes=35, **lineup_fields)

    lineup = Lineup(duration_minutes=36, **lineup_fields)

    assert lineup.duration_minutes == 36


def test_workshop_requires_at_least_one_place(festival: Festival) -> None:
    with pytest.raises(ValueError, match="at least one place"):
        Workshop(
            title="Full Workshop",
            venue=festival.venues[0],
            start=datetime(2027, 6, 10, 10),
            duration_minutes=60,
            teacher=festival.artists[3],
            max_participants=0,
        )


def test_workshop_capacity_is_limited_by_venue_seats(festival: Festival) -> None:
    workshop = Workshop(
        title="Large Workshop",
        venue=Venue("Grand Casino", 650, "Main Street"),
        start=datetime(2027, 6, 10, 10),
        duration_minutes=60,
        teacher=festival.artists[3],
        max_participants=999,
    )

    assert workshop.capacity == 650


def test_performance_is_abstract() -> None:
    with pytest.raises(TypeError):
        Performance(
            title="Abstract Show",
            venue=Venue("Test Hall", 10, "Nowhere"),
            start=datetime(2027, 6, 10, 10),
            duration_minutes=60,
        )


def test_kind_specific_summaries_match_step_nine_contract() -> None:
    festival = load_festival()

    assert (
        festival.get_performance("le-kiosque-2027-06-12-0100").summary()
        == "hosted by Tom Vasseur, with Hugo Lemaire, Maya Choukri"
    )
    assert (
        festival.get_performance("la-cabane-2027-06-11-1030").summary()
        == "with Inès Moreau, 3/12 places taken"
    )
    assert (
        festival.get_performance("grand-casino-2027-06-11-2030").summary()
        == "Léa Fontaine"
    )
