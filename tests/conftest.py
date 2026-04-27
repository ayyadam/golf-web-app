"""Shared test fixtures for the Adam's Golf Club test suite."""
import pytest
from datetime import date, time, timedelta
from app import create_app
from app.extensions import db as _db
from app.models import (
    Member, TeeTime, GeneralBooking, BookingPlayer,
    Competition, CompetitionTeeTime, CompetitionBooking,
    RangeTime, RangeBooking,
    Coach, CoachingTime, CoachingBooking,
    Visitor, MembershipRequest
)


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


@pytest.fixture
def future_date():
    """Return a date 7 days in the future."""
    return date.today() + timedelta(days=7)


@pytest.fixture
def past_date():
    """Return a date 7 days in the past."""
    return date.today() - timedelta(days=7)


@pytest.fixture
def tee_time(db, future_date):
    """Create an available tee time 7 days from now at 10:00."""
    tt = TeeTime(date=future_date, time=time(10, 0), max_players=4, is_available=True)
    db.session.add(tt)
    db.session.commit()
    return tt


@pytest.fixture
def competition(db, future_date):
    """Create a future competition."""
    comp = Competition(name='Test Medal', date=future_date, format='Medal')
    db.session.add(comp)
    db.session.commit()
    return comp


@pytest.fixture
def comp_tee_time(db, competition):
    """Create a competition tee time."""
    ctt = CompetitionTeeTime(competition_id=competition.id, time=time(8, 0), max_players=3)
    db.session.add(ctt)
    db.session.commit()
    return ctt


@pytest.fixture
def coach(db):
    """Create a coach."""
    c = Coach(first_name='Pro', last_name='Coach', speciality='Short Game', is_active=True)
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def coaching_time(db, coach, future_date):
    """Create an available coaching time."""
    ct = CoachingTime(coach_id=coach.id, date=future_date, time=time(14, 0), duration_mins=60)
    db.session.add(ct)
    db.session.commit()
    return ct


@pytest.fixture
def range_time(db, future_date):
    """Create an available range bay time."""
    rt = RangeTime(date=future_date, time=time(10, 0), bay_number=1, is_available=True)
    db.session.add(rt)
    db.session.commit()
    return rt


@pytest.fixture
def visitor(db):
    """Create a visitor record."""
    v = Visitor(first_name='Visitor', last_name='Test', email='visitor@test.com', telephone='07700900011')
    db.session.add(v)
    db.session.commit()
    return v
