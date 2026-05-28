"""Unit tests for the booking_service module."""
import pytest
from datetime import time

from app.models import BookingPlayer, GeneralBooking, TeeTime
from app.services.booking_service import (
    PlayerInput,
    create_general_booking,
    parse_handicap,
    validate_general_booking,
    validate_player_handicaps,
)


class TestParseHandicap:
    """parse_handicap converts user-supplied handicap strings to floats."""

    def test_normal_number(self):
        assert parse_handicap('14.3') == 14.3

    def test_plus_handicap_stored_as_negative(self):
        assert parse_handicap('+2.0') == -2.0

    def test_zero(self):
        assert parse_handicap('0') == 0.0

    def test_empty_string_returns_none(self):
        assert parse_handicap('') is None

    def test_whitespace_returns_none(self):
        assert parse_handicap('   ') is None

    def test_none_input(self):
        assert parse_handicap(None) is None

    def test_invalid_string_returns_none(self):
        assert parse_handicap('abc') is None

    def test_strips_whitespace(self):
        assert parse_handicap(' 14.3 ') == 14.3


class TestValidateGeneralBooking:
    """validate_general_booking enforces the rules common to both paths."""

    def test_valid_booking_returns_none(self, db, tee_time, member_user):
        assert validate_general_booking(tee_time, 1, member=member_user) is None

    def test_past_tee_time_rejected(self, db, past_date):
        tt = TeeTime(
            date=past_date, time=time(10, 0), max_players=4, is_available=True
        )
        db.session.add(tt)
        db.session.commit()
        err = validate_general_booking(tt, 1)
        assert err is not None
        assert err.code == 'tee_time_past'

    def test_group_size_exceeding_slots_rejected(self, db, tee_time):
        # tee_time fixture has max_players=4
        err = validate_general_booking(tee_time, 5)
        assert err is not None
        assert err.code == 'not_enough_slots'

    def test_member_already_booked_as_primary(self, db, tee_time, member_user):
        db.session.add(GeneralBooking(
            tee_time_id=tee_time.id, member_id=member_user.id, group_size=1
        ))
        db.session.commit()
        err = validate_general_booking(tee_time, 1, member=member_user)
        assert err is not None
        assert err.code == 'already_booked'

    def test_visitor_path_skips_member_check(self, db, tee_time):
        # With no member supplied, the already-booked check is skipped
        assert validate_general_booking(tee_time, 1) is None

    def test_member_already_booked_as_named_player(
        self, db, tee_time, member_user, other_member
    ):
        # Another member books the slot and names member_user as a group player
        booking = GeneralBooking(
            tee_time_id=tee_time.id, member_id=other_member.id, group_size=2
        )
        db.session.add(booking)
        db.session.flush()
        db.session.add(BookingPlayer(
            booking=booking, player_name=member_user.full_name
        ))
        db.session.commit()
        err = validate_general_booking(tee_time, 1, member=member_user)
        assert err is not None
        assert err.code == 'already_booked'


class TestValidatePlayerHandicaps:
    """validate_player_handicaps enforces the legal range of -10 to 54."""

    def test_none_input_ok(self):
        assert validate_player_handicaps(None) is None

    def test_empty_list_ok(self):
        assert validate_player_handicaps([]) is None

    def test_valid_handicap_ok(self):
        assert validate_player_handicaps(
            [PlayerInput(name='A', handicap=14.0)]
        ) is None

    def test_plus_handicap_ok(self):
        # Plus-handicap stored as negative; -2.0 is within range
        assert validate_player_handicaps(
            [PlayerInput(name='A', handicap=-2.0)]
        ) is None

    def test_none_handicap_is_skipped(self):
        # Player with no handicap provided does not trigger validation
        assert validate_player_handicaps(
            [PlayerInput(name='A', handicap=None)]
        ) is None

    def test_too_high_rejected(self):
        err = validate_player_handicaps(
            [PlayerInput(name='A', handicap=99.0)]
        )
        assert err is not None
        assert err.code == 'invalid_player_handicap'

    def test_too_low_rejected(self):
        err = validate_player_handicaps(
            [PlayerInput(name='A', handicap=-15.0)]
        )
        assert err is not None
        assert err.code == 'invalid_player_handicap'

    def test_error_message_uses_player_index(self):
        # The second item in the list is "Player 3" in form numbering
        # (the booking member is Player 1, first additional is Player 2)
        players = [
            PlayerInput(name='A', handicap=14.0),
            PlayerInput(name='B', handicap=999.0),
        ]
        err = validate_player_handicaps(players)
        assert err is not None
        assert 'Player 3' in err.message


class TestCreateGeneralBooking:
    """create_general_booking persists a booking and any group players."""

    def test_member_booking_persists(self, db, tee_time, member_user):
        booking = create_general_booking(
            tee_time=tee_time, group_size=1, member=member_user
        )
        db.session.commit()
        assert booking.id is not None
        assert booking.member_id == member_user.id
        assert booking.visitor_id is None
        assert booking.group_size == 1

    def test_visitor_booking_persists(self, db, tee_time, visitor):
        booking = create_general_booking(
            tee_time=tee_time, group_size=1, visitor_id=visitor.id
        )
        db.session.commit()
        assert booking.id is not None
        assert booking.visitor_id == visitor.id
        assert booking.member_id is None

    def test_group_players_persisted(self, db, tee_time, member_user):
        players = [
            PlayerInput(name='Alice', handicap=14.0),
            PlayerInput(name='Bob', handicap=-2.0),
        ]
        booking = create_general_booking(
            tee_time=tee_time, group_size=3, member=member_user, players=players
        )
        db.session.commit()
        assert booking.players.count() == 2
        names = sorted(p.player_name for p in booking.players)
        assert names == ['Alice', 'Bob']

    def test_empty_player_name_skipped(self, db, tee_time, member_user):
        # An additional player slot left blank should not produce a row
        players = [
            PlayerInput(name='', handicap=14.0),
            PlayerInput(name='Bob', handicap=10.0),
        ]
        booking = create_general_booking(
            tee_time=tee_time, group_size=3, member=member_user, players=players
        )
        db.session.commit()
        assert booking.players.count() == 1
        assert booking.players.first().player_name == 'Bob'

    def test_neither_member_nor_visitor_raises(self, db, tee_time):
        with pytest.raises(ValueError, match='Provide exactly one'):
            create_general_booking(tee_time=tee_time, group_size=1)

    def test_both_member_and_visitor_raises(
        self, db, tee_time, member_user, visitor
    ):
        with pytest.raises(ValueError, match='Provide exactly one'):
            create_general_booking(
                tee_time=tee_time,
                group_size=1,
                member=member_user,
                visitor_id=visitor.id,
            )

    def test_caller_must_commit(self, db, tee_time, member_user):
        # The service does not commit; the caller is responsible.
        create_general_booking(
            tee_time=tee_time, group_size=1, member=member_user
        )
        db.session.rollback()
        assert GeneralBooking.query.filter_by(
            member_id=member_user.id
        ).first() is None
