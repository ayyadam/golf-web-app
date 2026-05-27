"""Unit tests for member routes."""
from app.models import (
    Member, GeneralBooking, CompetitionBooking,
    RangeBooking, CoachingBooking
)


class TestMemberRoutes:
    """Test member-facing routes and flows."""

    def test_member_dashboard_loads(self, auth_client):
        resp = auth_client.get('/member/dashboard')
        assert resp.status_code == 200
        assert b'dashboard' in resp.data.lower() or b'Dashboard' in resp.data

    def test_member_coaching_page_loads(self, auth_client):
        resp = auth_client.get('/member/coaching')
        assert resp.status_code == 200

    def test_book_tee_time_page_loads(self, auth_client):
        resp = auth_client.get('/member/book-tee-time')
        assert resp.status_code == 200

    def test_book_tee_time_success(self, auth_client, tee_time, member_user):
        resp = auth_client.post('/member/book-tee-time', data={
            'tee_time_id': tee_time.id,
            'group_size': '1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Tee time booked successfully' in resp.data

        booking = GeneralBooking.query.filter_by(tee_time_id=tee_time.id).first()
        assert booking is not None
        assert booking.member_id == member_user.id

    def test_book_tee_time_group_with_players(self, auth_client, tee_time):
        resp = auth_client.post('/member/book-tee-time', data={
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

    def test_book_tee_time_not_enough_slots(self, auth_client, tee_time, visitor):
        # Fill the tee time
        booking = GeneralBooking(tee_time_id=tee_time.id, visitor_id=visitor.id, group_size=4)
        from app.extensions import db
        db.session.add(booking)
        db.session.commit()

        resp = auth_client.post('/member/book-tee-time', data={
            'tee_time_id': tee_time.id,
            'group_size': '1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Not enough slots available' in resp.data

    def test_book_tee_time_already_booked(self, auth_client, tee_time, member_user):
        booking = GeneralBooking(tee_time_id=tee_time.id, member_id=member_user.id, group_size=1)
        from app.extensions import db
        db.session.add(booking)
        db.session.commit()

        resp = auth_client.post('/member/book-tee-time', data={
            'tee_time_id': tee_time.id,
            'group_size': '1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'already booked for this tee time' in resp.data

    def test_book_tee_time_past(self, auth_client, past_date):
        from app.models import TeeTime
        from datetime import time
        from app.extensions import db
        tt = TeeTime(date=past_date, time=time(10, 0), max_players=4, is_available=True)
        db.session.add(tt)
        db.session.commit()

        resp = auth_client.post('/member/book-tee-time', data={
            'tee_time_id': tt.id,
            'group_size': '1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'This tee time has already passed' in resp.data

    def test_search_members_returns_results(self, auth_client, db):
        m = Member(username='searchy', email='search@test.com', first_name='John', last_name='Smith', telephone='000')
        m.set_password('pw')
        db.session.add(m)
        db.session.commit()

        resp = auth_client.get('/member/api/members/search?q=John')
        assert resp.status_code == 200
        data = resp.json
        assert len(data['members']) > 0
        assert data['members'][0]['name'] == 'John Smith'

    def test_search_members_excludes_self(self, auth_client, member_user):
        resp = auth_client.get(f'/member/api/members/search?q={member_user.first_name}')
        assert resp.status_code == 200
        data = resp.json
        for m in data['members']:
            assert m['id'] != member_user.id

    def test_search_members_empty_query(self, auth_client):
        resp = auth_client.get('/member/api/members/search?q=')
        assert resp.status_code == 200
        assert resp.json['members'] == []

    def test_competitions_page_loads(self, auth_client):
        resp = auth_client.get('/member/competitions')
        assert resp.status_code == 200

    def test_book_competition_page_loads(self, auth_client, competition):
        resp = auth_client.get(f'/member/competitions/{competition.id}/book')
        assert resp.status_code == 200

    def test_book_competition_success(self, auth_client, comp_tee_time, member_user):
        resp = auth_client.post(f'/member/competitions/{comp_tee_time.competition_id}/book', data={
            'action': 'book',
            'comp_tee_time_id': comp_tee_time.id
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Competition tee time booked' in resp.data

        booking = CompetitionBooking.query.filter_by(comp_tee_time_id=comp_tee_time.id).first()
        assert booking is not None
        assert booking.member_id == member_user.id

    def test_book_competition_full(self, auth_client, comp_tee_time):
        # Fill it up with 3 throwaway members (FK enforcement requires real member rows)
        from app.extensions import db
        from app.models import Member
        for i in range(3):
            filler = Member(
                username=f'filler{i}',
                email=f'filler{i}@test.com',
                first_name=f'Filler{i}',
                last_name='Test',
                telephone=f'07700{i:06d}',
                membership_type='Full Year',
                is_active=True,
            )
            filler.set_password('fillerpass')
            db.session.add(filler)
            db.session.flush()
            db.session.add(CompetitionBooking(comp_tee_time_id=comp_tee_time.id, member_id=filler.id))
        db.session.commit()

        resp = auth_client.post(f'/member/competitions/{comp_tee_time.competition_id}/book', data={
            'action': 'book',
            'comp_tee_time_id': comp_tee_time.id
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'This tee time is fully booked' in resp.data

    def test_cancel_competition_booking(self, auth_client, comp_tee_time, member_user):
        from app.extensions import db
        db.session.add(CompetitionBooking(comp_tee_time_id=comp_tee_time.id, member_id=member_user.id))
        db.session.commit()

        resp = auth_client.post(f'/member/competitions/{comp_tee_time.competition_id}/cancel', follow_redirects=True)
        assert resp.status_code == 200
        assert b'competition booking has been cancelled' in resp.data
        assert CompetitionBooking.query.filter_by(member_id=member_user.id).first() is None

    def test_cancel_own_general_booking(self, auth_client, tee_time, member_user):
        from app.extensions import db
        b = GeneralBooking(tee_time_id=tee_time.id, member_id=member_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.post(f'/member/cancel-general-booking/{b.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert b'booking has been cancelled' in resp.data
        assert GeneralBooking.query.get(b.id) is None

    def test_cancel_general_booking_unauthorized(self, auth_client, tee_time, other_member):
        from app.extensions import db
        b = GeneralBooking(tee_time_id=tee_time.id, member_id=other_member.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.post(f'/member/cancel-general-booking/{b.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert b'Unauthorized' in resp.data

    def test_book_range_page_loads(self, auth_client):
        resp = auth_client.get('/member/book-range')
        assert resp.status_code == 200

    def test_book_range_success(self, auth_client, range_time, member_user):
        resp = auth_client.post('/member/book-range', data={
            'range_time_id': range_time.id
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Successfully booked' in resp.data

        booking = RangeBooking.query.filter_by(range_time_id=range_time.id).first()
        assert booking is not None
        assert booking.member_id == member_user.id

    def test_book_range_already_booked_slot(self, auth_client, range_time, visitor):
        from app.extensions import db
        db.session.add(RangeBooking(range_time_id=range_time.id, visitor_id=visitor.id))
        db.session.commit()

        resp = auth_client.post('/member/book-range', data={
            'range_time_id': range_time.id
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'is already booked' in resp.data

    def test_book_range_concurrent_same_time(self, auth_client, range_time, member_user):
        from app.extensions import db
        from app.models import RangeTime
        # User already has bay 1
        db.session.add(RangeBooking(range_time_id=range_time.id, member_id=member_user.id))

        # Try to book bay 2 at same time
        rt2 = RangeTime(date=range_time.date, time=range_time.time, bay_number=2, is_available=True)
        db.session.add(rt2)
        db.session.commit()

        resp = auth_client.post('/member/book-range', data={
            'range_time_id': rt2.id
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'already have a range bay booked' in resp.data

    def test_cancel_range_booking(self, auth_client, range_time, member_user):
        from app.extensions import db
        b = RangeBooking(range_time_id=range_time.id, member_id=member_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.post(f'/member/cancel-range-booking/{b.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert b'cancelled' in resp.data

    def test_cancel_range_booking_unauthorized(self, auth_client, range_time, other_member):
        from app.extensions import db
        b = RangeBooking(range_time_id=range_time.id, member_id=other_member.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.post(f'/member/cancel-range-booking/{b.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert b'Unauthorized' in resp.data

    def test_book_coaching_page_loads(self, auth_client, coach):
        resp = auth_client.get(f'/member/coaching/{coach.id}/book')
        assert resp.status_code == 200

    def test_book_coaching_success(self, auth_client, coaching_time, member_user):
        resp = auth_client.post(f'/member/coaching/{coaching_time.coach_id}/book', data={
            'coaching_time_id': coaching_time.id
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Coaching lesson booked' in resp.data

        booking = CoachingBooking.query.filter_by(coaching_time_id=coaching_time.id).first()
        assert booking is not None
        assert booking.member_id == member_user.id

    def test_book_coaching_already_taken(self, auth_client, coaching_time, visitor):
        from app.extensions import db
        db.session.add(CoachingBooking(coaching_time_id=coaching_time.id, visitor_id=visitor.id))
        db.session.commit()

        resp = auth_client.post(f'/member/coaching/{coaching_time.coach_id}/book', data={
            'coaching_time_id': coaching_time.id
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'already booked' in resp.data

    def test_profile_page_loads(self, auth_client):
        resp = auth_client.get('/member/profile')
        assert resp.status_code == 200

    def test_update_profile_success(self, auth_client, member_user):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_profile',
            'email': 'new@test.com',
            'telephone': '0987654321'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'details have been successfully updated' in resp.data

        from app.extensions import db
        db.session.refresh(member_user)
        assert member_user.email == 'new@test.com'

    def test_update_profile_invalid_email(self, auth_client):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_profile',
            'email': 'bademail',
            'telephone': '0987654321'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'valid email' in resp.data

    def test_update_profile_duplicate_email(self, auth_client, db):
        other = Member(username='other', email='other@test.com', first_name='O', last_name='O', telephone='000')
        other.set_password('pw')
        db.session.add(other)
        db.session.commit()

        resp = auth_client.post('/member/profile', data={
            'action': 'update_profile',
            'email': 'other@test.com',
            'telephone': '0987654321'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'already in use' in resp.data

    def test_change_password_success(self, auth_client, member_user):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_password',
            'current_password': 'testpass123',
            'new_password': 'NewPassword1',
            'confirm_password': 'NewPassword1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'password has been successfully updated' in resp.data

    def test_change_password_wrong_current(self, auth_client):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_password',
            'current_password': 'wrong',
            'new_password': 'NewPassword1',
            'confirm_password': 'NewPassword1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Current password is incorrect' in resp.data

    def test_change_password_too_short(self, auth_client):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_password',
            'current_password': 'testpass123',
            'new_password': 'Short1',
            'confirm_password': 'Short1'
        }, follow_redirects=True)
        assert b'at least 8 characters long' in resp.data

    def test_change_password_no_capital(self, auth_client):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_password',
            'current_password': 'testpass123',
            'new_password': 'nocapitals1',
            'confirm_password': 'nocapitals1'
        }, follow_redirects=True)
        assert b'1 capital letter' in resp.data

    def test_change_password_no_number(self, auth_client):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_password',
            'current_password': 'testpass123',
            'new_password': 'NoNumbersHere',
            'confirm_password': 'NoNumbersHere'
        }, follow_redirects=True)
        assert b'1 number' in resp.data

    def test_change_password_mismatch(self, auth_client):
        resp = auth_client.post('/member/profile', data={
            'action': 'update_password',
            'current_password': 'testpass123',
            'new_password': 'NewPassword1',
            'confirm_password': 'NewPassword2'
        }, follow_redirects=True)
        assert b'do not match' in resp.data
