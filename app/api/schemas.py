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


def utf8_safe(value):
    """Reject strings that cannot be encoded to UTF-8 (e.g. lone surrogates).

    Without this, such a value reaches the database layer and raises an
    encoding error there, surfacing as a 500. Validating up front turns it
    into a clean 422. (Found by contract fuzzing against Postgres.)
    """
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError("Must be valid UTF-8 text.") from exc


# ---- Auth ----

class TokenRequest(Schema):
    username = String(required=True, validate=utf8_safe, metadata={'description': 'Member username'})
    password = String(required=True, validate=utf8_safe, metadata={'description': 'Member password'})


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
    name = String(required=True, validate=[Length(min=1, max=200), utf8_safe])
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


# ---- Errors ----

class ApiError(Schema):
    code = String(metadata={'description': 'Machine-readable error code'})
    message = String(metadata={'description': 'Human-readable error message'})
