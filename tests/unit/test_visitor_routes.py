"""Unit tests for visitor routes."""
from app.models import GeneralBooking, MembershipRequest


class TestVisitorRoutes:
    """Test visitor-facing routes and flows."""

    def test_visitor_booking_page_loads(self, client):
        resp = client.get('/visitor/book-tee-time')
        assert resp.status_code == 200
        assert b'Book a Visitor Tee Time' in resp.data

    def test_visitor_booking_with_date(self, client, future_date):
        resp = client.get(f'/visitor/book-tee-time?date={future_date.isoformat()}')
        assert resp.status_code == 200

    def test_visitor_book_tee_time_success(self, client, tee_time):
        resp = client.post('/visitor/book-tee-time', data={
            'first_name': 'Test',
            'last_name': 'Visitor',
            'email': 'visitor@test.com',
            'telephone': '0123456789',
            'handicap': '18.0',
            'tee_time_id': tee_time.id,
            'group_size': '1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Tee time booked successfully' in resp.data

        booking = GeneralBooking.query.filter_by(tee_time_id=tee_time.id).first()
        assert booking is not None
        assert booking.visitor.first_name == 'Test'

    def test_visitor_book_group_with_players(self, client, tee_time):
        resp = client.post('/visitor/book-tee-time', data={
            'first_name': 'Test',
            'last_name': 'Visitor',
            'email': 'visitor@test.com',
            'telephone': '0123456789',
            'handicap': '18.0',
            'tee_time_id': tee_time.id,
            'group_size': '2',
            'player_1_name': 'Friend',
            'player_1_handicap': '20.0'
        }, follow_redirects=True)
        assert resp.status_code == 200

        booking = GeneralBooking.query.filter_by(tee_time_id=tee_time.id).first()
        assert booking is not None
        assert booking.group_size == 2
        assert booking.players.count() == 1
        assert booking.players.first().player_name == 'Friend'

    def test_visitor_book_full_tee_time(self, client, tee_time, visitor):
        # Fully book the tee time first
        booking = GeneralBooking(tee_time_id=tee_time.id, visitor_id=visitor.id, group_size=4)
        from app.extensions import db
        db.session.add(booking)
        db.session.commit()

        resp = client.post('/visitor/book-tee-time', data={
            'first_name': 'Test',
            'last_name': 'Visitor2',
            'email': 'visitor2@test.com',
            'telephone': '0123456789',
            'tee_time_id': tee_time.id,
            'group_size': '1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Not enough slots available' in resp.data

    def test_visitor_booking_confirmation_page(self, client, tee_time, visitor):
        from app.extensions import db
        booking = GeneralBooking(tee_time_id=tee_time.id, visitor_id=visitor.id, group_size=1)
        db.session.add(booking)
        db.session.commit()

        resp = client.get(f'/visitor/booking-confirmation/{booking.id}')
        assert resp.status_code == 200
        assert b'Booking Confirmed!' in resp.data

    def test_visitor_membership_request(self, client):
        resp = client.post('/visitor/membership-request', data={
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane@test.com',
            'telephone': '0123456789',
            'membership_type': 'Full Year',
            'message': 'Hello'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'membership request has been submitted' in resp.data

        req = MembershipRequest.query.filter_by(email='jane@test.com').first()
        assert req is not None
        assert req.status == 'pending'

    def test_visitor_book_past_tee_time(self, client, past_date):
        from app.models import TeeTime
        from datetime import time
        from app.extensions import db
        tt = TeeTime(date=past_date, time=time(10, 0), max_players=4, is_available=True)
        db.session.add(tt)
        db.session.commit()

        resp = client.post('/visitor/book-tee-time', data={
            'first_name': 'Test',
            'last_name': 'Visitor',
            'email': 'visitor@test.com',
            'telephone': '0123456789',
            'tee_time_id': tt.id,
            'group_size': '1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'This tee time has already passed' in resp.data
