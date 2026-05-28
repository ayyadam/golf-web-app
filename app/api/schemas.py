"""Request and response schemas for the v1 JSON API.

These schemas drive both runtime validation (via APIFlask's @input/@output
decorators) and the auto-generated OpenAPI spec served at
/api/v1/openapi.json. Keep them aligned with the route signatures in
views.py — drift here would cause contract-test failures.
"""
from apiflask import Schema
from apiflask.fields import (
    Boolean, Date, DateTime, Decimal, Float, Integer, List, Nested, String, Time,
)
from apiflask.validators import Length, Range


# ---- Auth ----

class TokenRequest(Schema):
    username = String(required=True, metadata={'description': 'Member username'})
    password = String(required=True, metadata={'description': 'Member password'})


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
    handicap = Decimal(places=1, allow_none=True, as_string=True)
    membership_type = String()


# ---- Bookings ----

class PlayerInputSchema(Schema):
    name = String(required=True, validate=Length(min=1, max=200))
    handicap = Float(allow_none=True, load_default=None)


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


# ---- Errors ----

class ApiError(Schema):
    code = String(metadata={'description': 'Machine-readable error code'})
    message = String(metadata={'description': 'Human-readable error message'})
