"""View functions for the v1 JSON API."""
from datetime import date, datetime

from flask import jsonify, make_response

from ..extensions import db
from ..models import Competition, Member, TeeTime
from ..services.booking_assistant import (
    IntentParseError,
    find_candidate_slots,
    get_intent_extractor,
)
from ..services.booking_service import (
    PlayerInput,
    create_general_booking,
    validate_general_booking,
    validate_player_handicaps,
)
from . import api_bp
from .auth import TOKEN_TTL_SECONDS, issue_token, token_auth
from .schemas import (
    BookingAssistantRequest,
    BookingAssistantResponse,
    BookingOut,
    BookingRequest,
    CompetitionOut,
    MemberOut,
    TeeTimeOut,
    TeeTimeQuery,
    TokenRequest,
    TokenResponse,
)


# ---- Auth ----

@api_bp.post('/auth/token')
@api_bp.input(TokenRequest)
@api_bp.output(TokenResponse)
@api_bp.doc(
    summary='Issue a bearer token in exchange for username + password',
    responses={400: 'Malformed request body', 401: 'Invalid credentials'},
)
def issue_access_token(json_data):
    """Authenticate a member and return a signed bearer token."""
    member = Member.query.filter_by(
        username=json_data['username'], is_active=True
    ).first()
    if member is None or not member.check_password(json_data['password']):
        return make_response(jsonify(
            code='invalid_credentials',
            message='Username or password incorrect.',
        ), 401)
    return {
        'access_token': issue_token(member.id),
        'expires_in': TOKEN_TTL_SECONDS,
        'token_type': 'Bearer',
    }


# ---- Tee times ----

@api_bp.get('/tee-times')
@api_bp.input(TeeTimeQuery, location='query')
@api_bp.output(TeeTimeOut(many=True))
@api_bp.doc(summary='List available tee times (optionally filtered by date)')
def list_tee_times(query_data):
    """Return tee times that are available and not yet in the past."""
    q = TeeTime.query.filter(TeeTime.is_available.is_(True))
    if query_data.get('date'):
        q = q.filter(TeeTime.date == query_data['date'])
    else:
        q = q.filter(TeeTime.date >= date.today())

    tee_times = q.order_by(TeeTime.date, TeeTime.time).all()

    # Filter out slots that have already passed today
    now_time = datetime.now().time()
    today = date.today()
    return [
        tt for tt in tee_times
        if not (tt.date == today and tt.time <= now_time)
    ]


@api_bp.get('/tee-times/<int:tee_time_id>')
@api_bp.output(TeeTimeOut)
@api_bp.doc(summary='Get a single tee time by id', responses={404: 'Tee time not found'})
def get_tee_time(tee_time_id):
    """Return a tee time by id, or 404 if not found."""
    return TeeTime.query.get_or_404(tee_time_id)


# ---- Competitions ----

@api_bp.get('/competitions')
@api_bp.output(CompetitionOut(many=True))
@api_bp.doc(summary='List upcoming competitions')
def list_competitions():
    """Return active competitions scheduled for today or later."""
    return Competition.query.filter(
        Competition.date >= date.today(),
        Competition.is_active.is_(True),
    ).order_by(Competition.date).all()


# ---- Members ----

@api_bp.get('/members/me')
@api_bp.auth_required(token_auth)
@api_bp.output(MemberOut)
@api_bp.doc(summary='Return the profile of the authenticated member')
def get_current_member():
    return token_auth.current_user


# ---- Bookings ----

# Booking rejections that reflect a conflict with current resource state
# (rather than malformed input) are reported as 409 Conflict.
_CONFLICT_CODES = {'tee_time_past', 'not_enough_slots', 'already_booked'}


@api_bp.post('/tee-times/<int:tee_time_id>/bookings')
@api_bp.auth_required(token_auth)
@api_bp.input(BookingRequest)
@api_bp.output(BookingOut, status_code=201)
@api_bp.doc(
    summary='Book a tee time for the authenticated member',
    responses={
        400: 'Malformed request body',
        404: 'Tee time not found',
        409: 'Booking conflicts with current state (past tee time, full, or already booked)',
        422: 'Invalid input (e.g. player handicap out of range)',
    },
)
def book_tee_time(tee_time_id, json_data):
    """Create a general booking on the given tee time.

    The booking rules (past tee time, slot availability, double-booking,
    player handicap range) are enforced by the shared booking_service so
    the same constraints apply as for the HTML routes. Conflicts with
    current state return 409; malformed input returns 422.
    """
    tee_time = TeeTime.query.get_or_404(tee_time_id)
    member = token_auth.current_user

    players = [
        PlayerInput(name=p['name'], handicap=p.get('handicap'))
        for p in json_data.get('players', [])
    ]

    error = (
        validate_general_booking(tee_time, json_data['group_size'], member=member)
        or validate_player_handicaps(players)
    )
    if error:
        status = 409 if error.code in _CONFLICT_CODES else 422
        return make_response(jsonify(code=error.code, message=error.message), status)

    booking = create_general_booking(
        tee_time=tee_time,
        group_size=json_data['group_size'],
        member=member,
        players=players,
    )
    db.session.commit()
    return booking


# ---- Booking assistant (natural language) ----

@api_bp.post('/booking-assistant')
@api_bp.auth_required(token_auth)
@api_bp.input(BookingAssistantRequest)
@api_bp.output(BookingAssistantResponse)
@api_bp.doc(
    summary='Interpret a natural-language tee-time request and propose slots',
    description=(
        'The language model only extracts a structured intent from the text — it does '
        'not book anything. Returns the parsed intent plus bookable slots that match it; '
        'the member then books a chosen slot via POST /tee-times/{id}/bookings.'
    ),
    responses={
        400: 'Malformed request body',
        422: 'Could not interpret the request into a valid intent',
    },
)
def booking_assistant(json_data):
    """Turn free text into a structured intent, then propose matching slots.

    The model never mutates data: it only produces the intent, which is then
    validated and matched against genuinely bookable slots by deterministic
    code. This is the safety boundary against hallucinated/injected actions.
    """
    member = token_auth.current_user
    extractor = get_intent_extractor()
    try:
        intent = extractor.extract(json_data['text'])
    except IntentParseError as exc:
        return make_response(jsonify(code='unparseable_request', message=str(exc)), 422)

    candidates = find_candidate_slots(intent, member=member)
    return {'intent': intent, 'candidates': candidates}
