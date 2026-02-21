"""Functional (browser) tests using Playwright.

These tests spin up a live Flask server and use a real browser to test
the UI flows end-to-end.
"""
import pytest
import threading
import time
from app import create_app
from app.extensions import db as _db
from app.models import Member


@pytest.fixture(scope='module')
def live_app():
    """Create and run a live Flask server in a background thread."""
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        # Create a test user
        user = Member(
            username='functest', email='func@test.com',
            first_name='Func', last_name='Test',
            telephone='07700900000', membership_type='Full Year',
            is_active=True,
        )
        user.set_password('testpass123')
        _db.session.add(user)
        _db.session.commit()

    server = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=5099, use_reloader=False)
    )
    server.daemon = True
    server.start()
    time.sleep(1)  # Wait for server to start
    yield 'http://127.0.0.1:5099'

    with app.app_context():
        _db.drop_all()


@pytest.fixture(scope='module')
def browser(live_app):
    """Create a Playwright browser instance."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


class TestHomePage:
    """Functional tests for the home page."""

    def test_home_loads(self, page, live_app):
        page.goto(live_app)
        assert page.title() == "Adam's Golf Club — Welcome"

    def test_navigation_links(self, page, live_app):
        page.goto(live_app)
        nav = page.locator('nav')
        assert nav.is_visible()
        # Check key navigation items exist
        assert page.locator('text=The Course').first.is_visible()
        assert page.locator('text=Membership').first.is_visible()


class TestLoginFlow:
    """Functional tests for the login flow."""

    def test_login_page_accessible(self, page, live_app):
        page.goto(f'{live_app}/auth/login')
        assert page.get_by_role('heading', name='Member Login').is_visible()

    def test_successful_login(self, page, live_app):
        page.goto(f'{live_app}/auth/login')
        page.fill('#username', 'functest')
        page.fill('#password', 'testpass123')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        # Should redirect to member dashboard
        assert 'dashboard' in page.url or 'Welcome' in page.content()

    def test_failed_login(self, page, live_app):
        page.goto(f'{live_app}/auth/login')
        page.fill('#username', 'functest')
        page.fill('#password', 'wrongpassword')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        assert page.locator('text=Invalid username or password').is_visible()


class TestVisitorBooking:
    """Functional tests for visitor tee time booking."""

    def test_visitor_booking_page_loads(self, page, live_app):
        page.goto(f'{live_app}/visitor/book-tee-time')
        assert page.get_by_role('heading', name='Book a Visitor Tee Time').is_visible()
