"""Unit tests for admin routes."""
from datetime import date
from app.models import Member, MembershipRequest, TeeTime, Competition, RangeTime, Coach


class TestAdminRoutes:
    """Test admin-facing routes and flows."""

    def test_admin_dashboard_loads(self, admin_client):
        resp = admin_client.get('/admin/dashboard')
        assert resp.status_code == 200
        assert b'Admin Dashboard' in resp.data

    def test_member_cannot_access_admin(self, auth_client):
        resp = auth_client.get('/admin/dashboard', follow_redirects=True)
        # Should redirect to home with danger flash
        assert b'Admin privileges required' in resp.data

    def test_membership_requests_page_loads(self, admin_client):
        resp = admin_client.get('/admin/membership-requests')
        assert resp.status_code == 200

    def test_approve_membership_request(self, admin_client, db):
        req = MembershipRequest(
            first_name='Req', last_name='Test', email='req@test.com',
            telephone='123', status='pending'
        )
        db.session.add(req)
        db.session.commit()

        resp = admin_client.post(f'/admin/membership-requests/{req.id}/approve', data={
            'handicap': '20.0'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Membership approved' in resp.data
        
        db.session.refresh(req)
        assert req.status == 'approved'
        assert Member.query.filter_by(email='req@test.com').first() is not None

    def test_approve_membership_invalid_handicap(self, admin_client, db):
        req = MembershipRequest(
            first_name='Req2', last_name='Test2', email='req2@test.com',
            telephone='123', status='pending'
        )
        db.session.add(req)
        db.session.commit()

        resp = admin_client.post(f'/admin/membership-requests/{req.id}/approve', data={
            'handicap': '99.0' # Invalid handicap
        }, follow_redirects=True)
        
        db.session.refresh(req)
        assert req.status == 'pending' # Should not be approved

    def test_reject_membership_request(self, admin_client, db):
        req = MembershipRequest(
            first_name='Req3', last_name='Test3', email='req3@test.com',
            telephone='123', status='pending'
        )
        db.session.add(req)
        db.session.commit()

        resp = admin_client.post(f'/admin/membership-requests/{req.id}/reject', follow_redirects=True)
        
        db.session.refresh(req)
        assert req.status == 'rejected'

    def test_manage_members_page_loads(self, admin_client):
        resp = admin_client.get('/admin/members')
        assert resp.status_code == 200

    def test_create_member_success(self, admin_client):
        resp = admin_client.post('/admin/members', data={
            'first_name': 'New',
            'last_name': 'Guy',
            'email': 'newguy@test.com',
            'telephone': '0123456',
            'handicap': '10.0',
            'membership_type': 'Full Year'
        }, follow_redirects=True)
        assert b'Member created' in resp.data
        assert Member.query.filter_by(email='newguy@test.com').first() is not None

    def test_create_member_missing_fields(self, admin_client):
        resp = admin_client.post('/admin/members', data={
            'first_name': 'New'
            # Missing fields
        }, follow_redirects=True)
        assert b'are required' in resp.data

    def test_create_member_duplicate_email(self, admin_client, member_user):
        resp = admin_client.post('/admin/members', data={
            'first_name': 'New',
            'last_name': 'Guy',
            'email': member_user.email,
            'telephone': '0123456',
            'handicap': '10.0'
        }, follow_redirects=True)
        assert b'already exists' in resp.data

    def test_edit_member_page_loads(self, admin_client, member_user):
        resp = admin_client.get(f'/admin/members/{member_user.id}/edit')
        assert resp.status_code == 200

    def test_edit_member_success(self, admin_client, member_user):
        resp = admin_client.post(f'/admin/members/{member_user.id}/edit', data={
            'first_name': 'Updated',
            'last_name': member_user.last_name,
            'email': member_user.email,
            'telephone': member_user.telephone,
            'handicap': '5.0',
            'is_active': 'on'
        }, follow_redirects=True)
        assert b'updated' in resp.data
        from app.extensions import db
        db.session.refresh(member_user)
        assert member_user.first_name == 'Updated'

    def test_delete_member_success(self, admin_client, db):
        m = Member(username='delete_me', email='del@test.com', first_name='D', last_name='D', telephone='000')
        m.set_password('pw')
        db.session.add(m)
        db.session.commit()

        resp = admin_client.post(f'/admin/members/{m.id}/delete', follow_redirects=True)
        assert b'permanently removed' in resp.data
        assert Member.query.get(m.id) is None

    def test_delete_self_prevented(self, admin_client, admin_user):
        resp = admin_client.post(f'/admin/members/{admin_user.id}/delete', follow_redirects=True)
        assert b'cannot delete your own account' in resp.data

    def test_manage_tee_times_page_loads(self, admin_client):
        resp = admin_client.get('/admin/tee-times')
        assert resp.status_code == 200

    def test_create_tee_time(self, admin_client, future_date):
        resp = admin_client.post('/admin/tee-times', data={
            'action': 'create',
            'date': future_date.isoformat(),
            'time': '12:00',
            'max_players': '4'
        }, follow_redirects=True)
        assert b'Tee time created' in resp.data
        from datetime import time
        assert TeeTime.query.filter_by(date=future_date, time=time(12, 0)).first() is not None

    def test_generate_tee_times(self, admin_client, future_date):
        resp = admin_client.post('/admin/tee-times', data={
            'action': 'generate',
            'generate_date': future_date.isoformat()
        }, follow_redirects=True)
        assert b'tee times generated' in resp.data
        assert TeeTime.query.filter_by(date=future_date).count() > 0

    def test_edit_tee_time_page_loads(self, admin_client, tee_time):
        resp = admin_client.get(f'/admin/tee-times/{tee_time.id}/edit')
        assert resp.status_code == 200

    def test_manage_competitions_page_loads(self, admin_client):
        resp = admin_client.get('/admin/competitions')
        assert resp.status_code == 200

    def test_create_competition(self, admin_client, future_date):
        resp = admin_client.post('/admin/competitions', data={
            'name': 'New Comp',
            'date': future_date.isoformat(),
            'format': 'Stableford'
        }, follow_redirects=True)
        assert b'created' in resp.data
        assert Competition.query.filter_by(name='New Comp').first() is not None

    def test_delete_competition(self, admin_client, competition):
        resp = admin_client.post('/admin/competitions', data={
            'action': 'delete_competition',
            'comp_id': competition.id
        }, follow_redirects=True)
        assert b'deleted' in resp.data
        assert Competition.query.get(competition.id) is None

    def test_manage_range_page_loads(self, admin_client):
        resp = admin_client.get('/admin/range')
        assert resp.status_code == 200

    def test_create_range_time(self, admin_client, future_date):
        resp = admin_client.post('/admin/range', data={
            'date': future_date.isoformat(),
            'time': '13:00',
            'bay_number': '2'
        }, follow_redirects=True)
        assert b'Range time created' in resp.data
        from datetime import time
        assert RangeTime.query.filter_by(date=future_date, time=time(13, 0), bay_number=2).first() is not None

    def test_manage_coaches_page_loads(self, admin_client):
        resp = admin_client.get('/admin/coaches')
        assert resp.status_code == 200

    def test_create_coach(self, admin_client):
        resp = admin_client.post('/admin/coaches', data={
            'first_name': 'Tiger',
            'last_name': 'Woods',
            'speciality': 'Everything'
        }, follow_redirects=True)
        assert b'created' in resp.data
        assert Coach.query.filter_by(first_name='Tiger').first() is not None
