"""Shared test fixtures for the Adam's Golf Club test suite."""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models import Member


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')
    yield app


@pytest.fixture(scope='function')
def db(app):
    """Create a fresh database for each test function."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    user = Member(
        username='testadmin',
        email='testadmin@test.com',
        first_name='Test',
        last_name='Admin',
        telephone='07700900099',
        membership_type='Full Year',
        is_admin=True,
        is_active=True,
    )
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def member_user(db):
    """Create and return a regular member."""
    user = Member(
        username='testmember',
        email='testmember@test.com',
        first_name='Test',
        last_name='Member',
        telephone='07700900088',
        membership_type='Full Year',
        handicap=14.3,
        is_active=True,
    )
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_client(client, member_user):
    """Return a test client logged in as a regular member."""
    client.post('/auth/login', data={
        'username': 'testmember',
        'password': 'testpass123',
    }, follow_redirects=True)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Return a test client logged in as an admin."""
    client.post('/auth/login', data={
        'username': 'testadmin',
        'password': 'testpass123',
    }, follow_redirects=True)
    return client
