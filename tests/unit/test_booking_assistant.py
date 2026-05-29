"""Unit tests for the natural-language booking assistant.

These cover the deterministic parts — the rule-based stub extractor, the slot
matching, and the API endpoint wired to the stub. They do NOT exercise a real
model (that is the evaluation harness's job); they prove the plumbing and the
safety boundary (the model only proposes; deterministic code matches/executes).
"""
import os
from datetime import date, time, timedelta

import pytest

from app.extensions import db as _db
from app.models import TeeTime
from app.services.booking_assistant import (
    BookingIntent,
    OllamaIntentExtractor,
    StubIntentExtractor,
    find_candidate_slots,
    get_intent_extractor,
)


# ---------- StubIntentExtractor (pure, no app needed) ----------

class TestStubExtractor:
    def test_parses_fourball_saturday_morning(self):
        today = date(2026, 6, 1)
        intent = StubIntentExtractor().extract("book a 4-ball saturday morning", today=today)
        assert intent.group_size == 4
        assert intent.period == "morning"
        assert intent.date.weekday() == 5  # Saturday
        assert 0 <= (intent.date - today).days <= 6

    def test_parses_two_ball_tomorrow_afternoon(self):
        today = date(2026, 6, 1)
        intent = StubIntentExtractor().extract("a two-ball tomorrow afternoon", today=today)
        assert intent.group_size == 2
        assert intent.period == "afternoon"
        assert intent.date == today + timedelta(days=1)

    def test_sane_defaults_when_unspecified(self):
        today = date(2026, 6, 1)
        intent = StubIntentExtractor().extract("I'd like to play", today=today)
        assert intent.group_size == 1
        assert intent.period == "any"
        assert intent.date == today

    @pytest.mark.parametrize("junk", ["", "   ", "%%%", "book 999 players never-day", "🏌️⛳"])
    def test_never_crashes_and_stays_in_range(self, junk):
        intent = StubIntentExtractor().extract(junk, today=date(2026, 6, 1))
        assert 1 <= intent.group_size <= 4
        assert intent.period in ("morning", "afternoon", "any")


# ---------- provider registry ----------

class TestProviderRegistry:
    def test_defaults_to_stub(self, monkeypatch):
        monkeypatch.delenv("BOOKING_ASSISTANT_PROVIDER", raising=False)
        assert isinstance(get_intent_extractor(), StubIntentExtractor)

    def test_selects_ollama_when_configured(self, monkeypatch):
        monkeypatch.setenv("BOOKING_ASSISTANT_PROVIDER", "ollama")
        assert isinstance(get_intent_extractor(), OllamaIntentExtractor)

    def test_unknown_provider_falls_back_to_stub(self, monkeypatch):
        monkeypatch.setenv("BOOKING_ASSISTANT_PROVIDER", "does-not-exist")
        assert isinstance(get_intent_extractor(), StubIntentExtractor)


# ---------- find_candidate_slots (needs app/db context) ----------

class TestCandidateMatching:
    def test_filters_by_period_and_capacity(self, db):
        d = date.today() + timedelta(days=3)
        _db.session.add_all([
            TeeTime(date=d, time=time(9, 0), max_players=4, is_available=True),
            TeeTime(date=d, time=time(14, 0), max_players=4, is_available=True),
        ])
        _db.session.commit()

        morning = find_candidate_slots(BookingIntent(date=d, period="morning", group_size=2))
        assert [s.time for s in morning] == [time(9, 0)]

        any_period = find_candidate_slots(BookingIntent(date=d, period="any", group_size=2))
        assert {s.time for s in any_period} == {time(9, 0), time(14, 0)}

    def test_excludes_slots_without_enough_capacity(self, db):
        d = date.today() + timedelta(days=3)
        _db.session.add(TeeTime(date=d, time=time(9, 0), max_players=1, is_available=True))
        _db.session.commit()
        assert find_candidate_slots(BookingIntent(date=d, period="any", group_size=2)) == []

    def test_excludes_slots_the_member_already_booked(self, db, member_user):
        from app.services.booking_service import create_general_booking

        d = date.today() + timedelta(days=3)
        tt1 = TeeTime(date=d, time=time(9, 0), max_players=4, is_available=True)
        tt2 = TeeTime(date=d, time=time(10, 0), max_players=4, is_available=True)
        _db.session.add_all([tt1, tt2])
        _db.session.commit()
        create_general_booking(tee_time=tt1, group_size=1, member=member_user)
        _db.session.commit()

        times = {s.time for s in find_candidate_slots(
            BookingIntent(date=d, period="any", group_size=1), member=member_user,
        )}
        assert time(10, 0) in times      # free slot proposed
        assert time(9, 0) not in times   # already booked -> excluded


# ---------- API endpoint (wired to the stub) ----------

@pytest.fixture
def member_token(client, member_user):
    resp = client.post('/api/v1/auth/token', json={
        'username': 'testmember', 'password': 'testpass123',
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()['access_token']


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


class TestBookingAssistantEndpoint:
    def test_requires_authentication(self, client, db):
        resp = client.post('/api/v1/booking-assistant', json={'text': 'a round tomorrow'})
        assert resp.status_code in (401, 403)

    def test_returns_intent_and_candidates(self, client, member_token):
        resp = client.post(
            '/api/v1/booking-assistant',
            json={'text': 'a 4-ball saturday morning'},
            headers=_auth(member_token),
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body['intent']['group_size'] == 4
        assert body['intent']['period'] == 'morning'
        assert isinstance(body['candidates'], list)

    def test_proposes_a_real_bookable_slot(self, client, member_token):
        d = date.today() + timedelta(days=2)
        _db.session.add(TeeTime(date=d, time=time(9, 0), max_players=4, is_available=True))
        _db.session.commit()
        # 'tomorrow' won't match d; target the slot's date via an absolute-ish phrasing
        # the stub understands: use the weekday name of d.
        weekday_name = d.strftime('%A').lower()
        resp = client.post(
            '/api/v1/booking-assistant',
            json={'text': f'a single {weekday_name} morning'},
            headers=_auth(member_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert any(c['time'] == '09:00:00' for c in body['candidates'])

    @pytest.mark.parametrize("junk", ["%%%", "asdkjfh", "book 9999 players yesteryear"])
    def test_robust_to_junk_text_never_5xx(self, client, member_token, junk):
        resp = client.post('/api/v1/booking-assistant', json={'text': junk}, headers=_auth(member_token))
        assert resp.status_code == 200  # stub always parses; never crashes

    def test_rejects_empty_text(self, client, member_token):
        resp = client.post('/api/v1/booking-assistant', json={'text': ''}, headers=_auth(member_token))
        assert resp.status_code == 422

    def test_rejects_null_byte_text_cleanly(self, client, member_token):
        resp = client.post('/api/v1/booking-assistant', json={'text': 'a\x00b'}, headers=_auth(member_token))
        assert resp.status_code == 422


# ---------- real-model smoke (local only; skipped in CI) ----------

@pytest.mark.skipif(
    os.getenv("RUN_OLLAMA_TESTS") != "1",
    reason="real Ollama smoke; requires a local model. Set RUN_OLLAMA_TESTS=1 to run.",
)
def test_ollama_extractor_returns_valid_shape():
    """Structural smoke against the real model — asserts SHAPE, not meaning.

    Semantic correctness (did it understand the request?) is non-deterministic
    and belongs in the evaluation harness, not a pass/fail test. This just
    proves the provider is wired and returns a well-formed intent.
    """
    from app.services.booking_assistant import OllamaIntentExtractor

    intent = OllamaIntentExtractor().extract("a 4-ball next Saturday morning", today=date(2026, 6, 1))
    assert isinstance(intent.date, date)
    assert intent.period in ("morning", "afternoon", "any")
    assert 1 <= intent.group_size <= 4
