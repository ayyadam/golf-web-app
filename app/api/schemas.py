"""Request and response schemas for the v1 JSON API.

These schemas drive both runtime validation (via APIFlask's @input/@output
decorators) and the auto-generated OpenAPI spec served at
/api/v1/openapi.json. Keep them aligned with the route signatures in
views.py — drift here would cause contract-test failures.
"""
from apiflask import Schema
from apiflask.fields import (
    Boolean, Date, DateTime, Float, Integer, List, Nested, String, Time,
)
from apiflask.validators import Length, Range
from marshmallow import ValidationError, post_dump


def safe_text(value):
    """Reject strings the database cannot store: invalid UTF-8 or NUL bytes.

    Two classes of input reach the DB layer and crash with a 500 otherwise:
    - lone surrogates, which cannot be encoded to UTF-8
    - NUL (0x00) bytes, which encode fine but Postgres text columns reject
    Validating up front turns both into a clean 422. Both were found by
    contract fuzzing against Postgres (not reproducible on SQLite).
    """
    if "\x00" in value:
        raise ValidationError("Must not contain null bytes.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError("Must be valid UTF-8 text.") from exc


# ---- Auth ----

class TokenRequest(Schema):
    username = String(required=True, validate=safe_text, metadata={'description': 'Member username'})
    password = String(required=True, validate=safe_text, metadata={'description': 'Member password'})


class TokenResponse(Schema):
    access_token = String(metadata={'description': 'Bearer token for subsequent API calls'})
    expires_in = Integer(metadata={'description': 'Seconds until token expiry'})
    token_type = String(metadata={'description': 'Always "Bearer"'})


# ---- Tee times ----

class TeeTimeOut(Schema):
    id = Integer()
    date = Date()
    time = Time()
    max_players = Integer()
    slots_remaining = Integer()
    is_available = Boolean()


class TeeTimeQuery(Schema):
    date = Date(load_default=None, metadata={
        'description': 'Optional date filter (YYYY-MM-DD). Defaults to all upcoming dates.'
    })


# ---- Competitions ----

class CompetitionOut(Schema):
    id = Integer()
    name = String()
    date = Date()
    format = String()
    is_active = Boolean()


# ---- Members ----

class MemberOut(Schema):
    id = Integer()
    username = String()
    first_name = String()
    last_name = String()
    email = String()
    # Float (not Decimal) so it serializes as a JSON number, matching the
    # 'number' type the spec declares for this field.
    handicap = Float(allow_none=True)
    membership_type = String()


# ---- Bookings ----

class PlayerInputSchema(Schema):
    name = String(required=True, validate=[Length(min=1, max=200), safe_text])
    # Handicap range is part of the contract: -10 (plus handicap) to 54.
    handicap = Float(allow_none=True, load_default=None, validate=Range(min=-10, max=54))


class BookingRequest(Schema):
    group_size = Integer(required=True, validate=Range(min=1, max=4))
    players = List(Nested(PlayerInputSchema), load_default=list)


class BookingOut(Schema):
    id = Integer()
    tee_time_id = Integer()
    member_id = Integer(allow_none=True)
    visitor_id = Integer(allow_none=True)
    group_size = Integer()
    booked_at = DateTime()

    @post_dump
    def _utc_timestamps(self, data, **kwargs):
        # booked_at is stored as a naive UTC datetime (server default now()).
        # A bare ISO string without an offset is not a valid RFC 3339
        # date-time, which the spec declares. Treat it as UTC and append 'Z'.
        ba = data.get("booked_at")
        if isinstance(ba, str) and ba and not (ba.endswith("Z") or "+" in ba[10:]):
            data["booked_at"] = ba + "Z"
        return data


# ---- Booking assistant (natural language) ----

class BookingAssistantRequest(Schema):
    text = String(
        required=True,
        validate=[Length(min=1, max=500), safe_text],
        metadata={'description': 'Natural-language tee-time request, e.g. "a 4-ball Saturday morning"'},
    )


class BookingIntentOut(Schema):
    """The structured intent the model extracted from the text."""
    date = Date()
    period = String(metadata={'description': "'morning', 'afternoon', or 'any'"})
    group_size = Integer()
    players = List(String())
    not_before = Time(
        format='%H:%M', allow_none=True,
        metadata={'description': 'earliest acceptable tee time (HH:MM), or null'},
    )
    not_after = Time(
        format='%H:%M', allow_none=True,
        metadata={'description': 'latest acceptable tee time (HH:MM), or null'},
    )


class BookingAssistantResponse(Schema):
    intent = Nested(BookingIntentOut, metadata={'description': 'Parsed interpretation of the request'})
    candidates = List(Nested(TeeTimeOut), metadata={'description': 'Bookable slots matching the intent'})


# ---- Errors ----

class ApiError(Schema):
    code = String(metadata={'description': 'Machine-readable error code'})
    message = String(metadata={'description': 'Human-readable error message'})
