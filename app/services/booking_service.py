"""Booking validation and creation logic for general-play tee times.

Centralises the rules so the member HTML form, the visitor HTML form, and
the JSON API (planned) all enforce the same constraints. Validation
functions return None on success or a BookingValidationError on failure;
the caller decides how to surface the error (flash, HTTP response, etc.).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from ..extensions import db
from ..models import BookingPlayer, GeneralBooking, Member, TeeTime


@dataclass
class PlayerInput:
    """A non-primary player on a group booking."""
    name: str
    handicap: Optional[float] = None


@dataclass
class BookingValidationError:
    """Why a booking attempt was rejected. `code` is machine-readable."""
    code: str
    message: str


def parse_handicap(raw):
    """Parse a handicap input (e.g. '+2.0', '14.3') into a float.

    Plus-handicaps (better than scratch) are stored as negative floats by
    convention in this app. Returns None for empty or unparseable input.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    is_plus = s.startswith('+')
    try:
        n = float(s.replace('+', ''))
        return -abs(n) if is_plus else n
    except ValueError:
        return None


def validate_general_booking(
    tee_time: TeeTime,
    group_size: int,
    member: Optional[Member] = None,
) -> Optional[BookingValidationError]:
    """Validate a general tee-time booking attempt.

    Common rules across member and visitor paths: tee time must not be in
    the past and must have enough remaining slots. When a member is
    provided, additionally checks they are not already booked on this slot
    (either as primary booker or as a named player on another booking).
    """
    now = datetime.now()
    tee_dt = datetime.combine(tee_time.date, tee_time.time)
    if tee_dt <= now:
        return BookingValidationError(
            'tee_time_past', 'This tee time has already passed.'
        )

    if group_size > tee_time.slots_remaining:
        return BookingValidationError(
            'not_enough_slots',
            'Not enough slots available for your group size.',
        )

    if member is not None:
        existing = GeneralBooking.query.join(TeeTime).filter(
            TeeTime.id == tee_time.id,
            db.or_(
                GeneralBooking.member_id == member.id,
                GeneralBooking.players.any(
                    BookingPlayer.player_name == member.full_name
                ),
            ),
        ).first()
        if existing:
            return BookingValidationError(
                'already_booked', 'You are already booked for this tee time.'
            )

    return None


def validate_player_handicaps(
    players: Optional[Sequence[PlayerInput]],
) -> Optional[BookingValidationError]:
    """Check that all supplied player handicaps fall within (-10, 54).

    The legal range is the same as that enforced by the member admin form.
    None handicaps are skipped (treated as "not provided").
    """
    if not players:
        return None
    for i, p in enumerate(players, start=1):
        if p.handicap is not None and (p.handicap < -10 or p.handicap > 54):
            return BookingValidationError(
                'invalid_player_handicap',
                f'Player {i + 1} handicap must be between -10 and 54.',
            )
    return None


def create_general_booking(
    tee_time: TeeTime,
    group_size: int,
    member: Optional[Member] = None,
    visitor_id: Optional[int] = None,
    players: Optional[Sequence[PlayerInput]] = None,
) -> GeneralBooking:
    """Create a GeneralBooking and any associated BookingPlayer rows.

    Exactly one of `member` or `visitor_id` must be provided. The caller
    is responsible for committing the session, so this can be batched with
    related operations (e.g. creating a Visitor row first and flushing to
    obtain its id).
    """
    if (member is None) == (visitor_id is None):
        raise ValueError("Provide exactly one of member or visitor_id")

    booking = GeneralBooking(
        tee_time_id=tee_time.id,
        member_id=member.id if member else None,
        visitor_id=visitor_id,
        group_size=group_size,
    )
    db.session.add(booking)

    if players:
        for p in players:
            if p.name:
                db.session.add(BookingPlayer(
                    booking=booking,
                    player_name=p.name,
                    handicap=p.handicap,
                ))

    return booking
