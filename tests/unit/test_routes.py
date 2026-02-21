"""Unit tests for route access and responses."""


class TestPublicRoutes:
    """Test public-facing routes are accessible."""

    def test_home_page(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert b"Adam's Golf Club" in resp.data

    def test_course_page(self, client):
        resp = client.get('/course/')
        assert resp.status_code == 200

    def test_scorecard_page(self, client):
        resp = client.get('/scorecard/')
        assert resp.status_code == 200

    def test_membership_page(self, client):
        resp = client.get('/membership/')
        assert resp.status_code == 200

    def test_trackman_page(self, client):
        resp = client.get('/facilities/trackman/')
        assert resp.status_code == 200

    def test_practice_page(self, client):
        resp = client.get('/facilities/practice/')
        assert resp.status_code == 200

    def test_coaching_page(self, client):
        resp = client.get('/coaching/')
        assert resp.status_code == 200

    def test_login_page(self, client):
        resp = client.get('/auth/login')
        assert resp.status_code == 200


class TestAuthRoutes:
    """Test authentication flow."""

    def test_login_valid(self, client, member_user):
        resp = client.post('/auth/login', data={
            'username': 'testmember',
            'password': 'testpass123',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_invalid_password(self, client, member_user):
        resp = client.post('/auth/login', data={
            'username': 'testmember',
            'password': 'wrongpassword',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Invalid username or password' in resp.data

    def test_logout(self, auth_client):
        resp = auth_client.get('/auth/logout', follow_redirects=True)
        assert resp.status_code == 200


class TestProtectedRoutes:
    """Test that member/admin routes require authentication."""

    def test_member_dashboard_requires_login(self, client):
        resp = client.get('/member/dashboard', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_admin_dashboard_requires_login(self, client):
        resp = client.get('/admin/', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_member_can_access_dashboard(self, auth_client):
        resp = auth_client.get('/member/dashboard')
        assert resp.status_code == 200

    def test_admin_can_access_admin(self, admin_client):
        resp = admin_client.get('/admin/')
        assert resp.status_code == 200

    def test_member_cannot_access_admin(self, auth_client):
        resp = auth_client.get('/admin/', follow_redirects=False)
        assert resp.status_code in (302, 403)
