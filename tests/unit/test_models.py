"""Unit tests for the Member model."""
from app.models import Member


class TestMemberModel:
    """Tests for the Member model."""

    def test_create_member(self, db):
        """Test creating a new member."""
        member = Member(
            username='newuser',
            email='new@test.com',
            first_name='New',
            last_name='User',
            telephone='07700900077',
            membership_type='Full Year',
        )
        member.set_password('password123')
        db.session.add(member)
        db.session.commit()

        assert member.id is not None
        assert member.username == 'newuser'
        assert member.full_name == 'New User'
        assert member.is_admin is False
        assert member.is_active is True

    def test_password_hashing(self, db):
        """Test that passwords are properly hashed."""
        member = Member(
            username='hashtest', email='hash@test.com',
            first_name='Hash', last_name='Test', telephone='07700900066',
            membership_type='Full Year',
        )
        member.set_password('mysecret')
        assert member.password_hash != 'mysecret'
        assert member.check_password('mysecret') is True
        assert member.check_password('wrongpassword') is False

    def test_member_handicap(self, db):
        """Test handicap as decimal."""
        member = Member(
            username='hcptest', email='hcp@test.com',
            first_name='Hcp', last_name='Test', telephone='07700900055',
            membership_type='Full Year', handicap=14.3,
        )
        db.session.add(member)
        db.session.commit()

        fetched = Member.query.filter_by(username='hcptest').first()
        assert float(fetched.handicap) == 14.3

    def test_admin_flag(self, admin_user):
        """Test that admin users have the is_admin flag."""
        assert admin_user.is_admin is True

    def test_user_is_authenticated(self, member_user):
        """Test Flask-Login integration."""
        assert member_user.is_authenticated is True
