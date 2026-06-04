"""Unit tests for the v1 JSON API."""
import pytest
from datetime import time

from app.extensions import db as _db
from app.models import Competition, GeneralBooking, TeeTime


# ---------- helpers ----------

def _auth_header(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def member_token(client, member_user):
    """A valid bearer token for the seeded testmember account."""
    resp = client.post('/api/v1/auth/token', json={
        'username': 'testmember',
        'password': 'testpass123',
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()['access_token']


# ---------- auth ----------

class TestAuthToken:
    """POST /api/v1/auth/token issues bearer tokens."""

    def test_valid_credentials_returns_token(self, client, member_user):
        resp = client.post('/api/v1/auth/token', json={
            'username': 'testmember',
            'password': 'testpass123',
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['token_type'] == 'Bearer'
        assert body['expires_in'] == 3600
        assert isinstance(body['access_token'], str) and len(body['access_token']) > 0

    def test_wrong_password_returns_401(self, client, member_user):
        resp = client.post('/api/v1/auth/token', json={
            'username': 'testmember',
            'password': 'wrong',
        })
        assert resp.status_code == 401
        assert resp.get_json()['code'] == 'invalid_credentials'

    def test_unknown_username_returns_401(self, client, db):
        resp = client.post('/api/v1/auth/token', json={
            'username': 'nobody',
            'password': 'whatever',
        })
        assert resp.status_code == 401

    def test_missing_fields_rejected(self, client):
        resp = client.post('/api/v1/auth/token', json={'username': 'x'})
        assert resp.status_code == 422

    def test_null_byte_in_username_rejected_cleanly(self, client, db):
        # A NUL byte encodes to UTF-8 fine but Postgres text columns reject
        # it; without validation this reaches the DB and 500s. Expect 422.
        resp = client.post('/api/v1/auth/token', json={
            'username': 'a\x00b',
            'password': 'x',
        })
        assert resp.status_code == 422

    def test_lone_surrogate_in_username_rejected_cleanly(self, client, db):
        resp = client.post('/api/v1/auth/token', json={
            'username': '\ud800',
            'password': 'x',
        })
        assert resp.status_code == 422


# ---------- tee times ----------

class TestListTeeTimes:
    """GET /api/v1/tee-times — bearer auth required."""

    def test_without_token_returns_401(self, client, db):
        resp = client.get('/api/v1/tee-times')
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client, db):
        resp = client.get(
            '/api/v1/tee-times', headers=_auth_header('not-a-real-token')
        )
        assert resp.status_code == 401

    def test_returns_available_tee_times(self, client, tee_time, member_token):
        resp = client.get('/api/v1/tee-times', headers=_auth_header(member_token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert isinstance(body, list)
        ids = [tt['id'] for tt in body]
        assert tee_time.id in ids

    def test_includes_slots_remaining(self, client, tee_time, member_token):
        resp = client.get('/api/v1/tee-times', headers=_auth_header(member_token))
        assert resp.status_code == 200
        body = resp.get_json()
        match = next(tt for tt in body if tt['id'] == tee_time.id)
        assert match['slots_remaining'] == 4
        assert match['max_players'] == 4

    def test_filter_by_date(self, client, db, future_date, member_token):
        tt = TeeTime(
            date=future_date, time=time(9, 0),
            max_players=4, is_available=True,
        )
        _db.session.add(tt)
        _db.session.commit()
        resp = client.get(
            f'/api/v1/tee-times?date={future_date.isoformat()}',
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert all(t['date'] == future_date.isoformat() for t in body)

    def test_excludes_unavailable(self, client, db, future_date, member_token):
        tt = TeeTime(
            date=future_date, time=time(11, 0),
            max_players=4, is_available=False,
        )
        _db.session.add(tt)
        _db.session.commit()
        resp = client.get(
            f'/api/v1/tee-times?date={future_date.isoformat()}',
            headers=_auth_header(member_token),
        )
        ids = [t['id'] for t in resp.get_json()]
        assert tt.id not in ids


class TestGetTeeTime:
    """GET /api/v1/tee-times/{id} — bearer auth required."""

    def test_without_token_returns_401(self, client, tee_time):
        resp = client.get(f'/api/v1/tee-times/{tee_time.id}')
        assert resp.status_code == 401

    def test_returns_single_tee_time(self, client, tee_time, member_token):
        resp = client.get(
            f'/api/v1/tee-times/{tee_time.id}',
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['id'] == tee_time.id
        assert body['max_players'] == 4

    def test_unknown_id_returns_404(self, client, db, member_token):
        resp = client.get(
            '/api/v1/tee-times/9999999',
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 404


# ---------- competitions ----------

class TestListCompetitions:
    """GET /api/v1/competitions — bearer auth required."""

    def test_without_token_returns_401(self, client, db):
        resp = client.get('/api/v1/competitions')
        assert resp.status_code == 401

    def test_returns_upcoming_competitions(self, client, competition, member_token):
        resp = client.get(
            '/api/v1/competitions', headers=_auth_header(member_token)
        )
        assert resp.status_code == 200
        body = resp.get_json()
        ids = [c['id'] for c in body]
        assert competition.id in ids

    def test_excludes_past_competitions(self, client, db, past_date, member_token):
        comp = Competition(name='Old', date=past_date, format='Medal')
        _db.session.add(comp)
        _db.session.commit()
        resp = client.get(
            '/api/v1/competitions', headers=_auth_header(member_token)
        )
        ids = [c['id'] for c in resp.get_json()]
        assert comp.id not in ids


# ---------- members/me (auth required) ----------

class TestMembersMe:
    """GET /api/v1/members/me — bearer auth required."""

    def test_without_token_returns_401(self, client, db):
        resp = client.get('/api/v1/members/me')
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client, db):
        resp = client.get(
            '/api/v1/members/me', headers=_auth_header('not-a-real-token')
        )
        assert resp.status_code == 401

    def test_valid_token_returns_profile(self, client, member_user, member_token):
        resp = client.get(
            '/api/v1/members/me', headers=_auth_header(member_token)
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['id'] == member_user.id
        assert body['username'] == 'testmember'
        assert body['email'] == 'testmember@test.com'


# ---------- book a tee time (auth required) ----------

class TestBookTeeTimeApi:
    """POST /api/v1/tee-times/{id}/bookings"""

    def test_without_token_returns_401(self, client, tee_time):
        resp = client.post(
            f'/api/v1/tee-times/{tee_time.id}/bookings',
            json={'group_size': 1},
        )
        assert resp.status_code == 401

    def test_creates_booking(self, client, tee_time, member_user, member_token):
        resp = client.post(
            f'/api/v1/tee-times/{tee_time.id}/bookings',
            json={'group_size': 2, 'players': [
                {'name': 'Alice', 'handicap': 14.0},
            ]},
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 201, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body['tee_time_id'] == tee_time.id
        assert body['member_id'] == member_user.id
        assert body['group_size'] == 2

        # Persisted?
        booking = GeneralBooking.query.get(body['id'])
        assert booking is not None
        assert booking.players.count() == 1

    def test_rejects_past_tee_time(self, client, db, past_date, member_token):
        tt = TeeTime(
            date=past_date, time=time(10, 0),
            max_players=4, is_available=True,
        )
        _db.session.add(tt)
        _db.session.commit()
        resp = client.post(
            f'/api/v1/tee-times/{tt.id}/bookings',
            json={'group_size': 1},
            headers=_auth_header(member_token),
        )
        # Conflict with current state -> 409, not 400
        assert resp.status_code == 409
        assert resp.get_json()['code'] == 'tee_time_past'

    def test_rejects_too_large_group(self, client, tee_time, member_token):
        # tee_time fixture has max_players=4; group_size=4 still fits, 5 doesn't
        # but the schema also caps group_size at 4, so 5 hits the schema (422)
        resp = client.post(
            f'/api/v1/tee-times/{tee_time.id}/bookings',
            json={'group_size': 5},
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 422

    def test_rejects_not_enough_slots(
        self, client, tee_time, member_token, db, other_member
    ):
        # Fill the tee_time with a booking from another member
        _db.session.add(GeneralBooking(
            tee_time_id=tee_time.id, member_id=other_member.id, group_size=3,
        ))
        _db.session.commit()
        # Now only 1 slot remains; requesting 2 should conflict
        resp = client.post(
            f'/api/v1/tee-times/{tee_time.id}/bookings',
            json={'group_size': 2},
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 409
        assert resp.get_json()['code'] == 'not_enough_slots'

    def test_rejects_already_booked(
        self, client, tee_time, member_user, member_token, db
    ):
        _db.session.add(GeneralBooking(
            tee_time_id=tee_time.id, member_id=member_user.id, group_size=1,
        ))
        _db.session.commit()
        resp = client.post(
            f'/api/v1/tee-times/{tee_time.id}/bookings',
            json={'group_size': 1},
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 409
        assert resp.get_json()['code'] == 'already_booked'

    def test_rejects_invalid_player_handicap(
        self, client, tee_time, member_token
    ):
        # Handicap range is now part of the schema, so an out-of-range value
        # is rejected at the validation layer as 422 (not the service 400).
        resp = client.post(
            f'/api/v1/tee-times/{tee_time.id}/bookings',
            json={'group_size': 2, 'players': [
                {'name': 'BadHandicap', 'handicap': 999.0},
            ]},
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 422

    def test_unknown_tee_time_returns_404(self, client, member_token):
        resp = client.post(
            '/api/v1/tee-times/9999999/bookings',
            json={'group_size': 1},
            headers=_auth_header(member_token),
        )
        assert resp.status_code == 404


# ---------- OpenAPI spec + docs ----------

class TestOpenApiArtifacts:
    """The auto-generated spec and Swagger UI are served."""

    def test_openapi_json_reachable(self, client):
        resp = client.get('/api/v1/openapi.json')
        assert resp.status_code == 200
        spec = resp.get_json()
        assert spec['openapi'].startswith('3.')
        assert spec['info']['title'] == "Adam's Golf Club API"
        # Spot-check that our endpoints appear (paths include the url_prefix)
        paths = spec['paths']
        assert '/api/v1/auth/token' in paths
        assert '/api/v1/tee-times' in paths
        assert '/api/v1/tee-times/{tee_time_id}/bookings' in paths

    def test_openapi_spec_marks_read_endpoints_as_auth_required(self, client):
        # Regression guard: the three read endpoints below were public until
        # the explore_agent's auth-bypass pass surfaced six anonymous-read
        # 200s. The decorator stack on each route is the source of truth for
        # APIFlask's generated security stanza; if any of these decorators
        # are dropped, the spec loses the BearerAuth requirement and this
        # test fails.
        resp = client.get('/api/v1/openapi.json')
        spec = resp.get_json()
        for path, method in [
            ('/api/v1/tee-times', 'get'),
            ('/api/v1/tee-times/{tee_time_id}', 'get'),
            ('/api/v1/competitions', 'get'),
            ('/api/v1/members/me', 'get'),
            ('/api/v1/tee-times/{tee_time_id}/bookings', 'post'),
            ('/api/v1/booking-assistant', 'post'),
        ]:
            op = spec['paths'][path][method]
            assert op.get('security') == [{'BearerAuth': []}], (
                f"{method.upper()} {path} should require BearerAuth; "
                f"got security={op.get('security')!r}"
            )

    def test_swagger_ui_reachable(self, client):
        resp = client.get('/api/v1/docs')
        assert resp.status_code == 200
        assert b'swagger' in resp.data.lower() or b'openapi' in resp.data.lower()
