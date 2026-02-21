from datetime import date
from flask_login import UserMixin
from ..extensions import db, login_manager
import bcrypt


class Member(UserMixin, db.Model):
    """Member model — also serves as Admin when is_admin=True."""
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    handicap = db.Column(db.Numeric(3, 1), nullable=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    membership_type = db.Column(
        db.String(20), nullable=False, default='Full Year'
    )  # 'Full Year' or '6 Month'
    membership_start = db.Column(db.Date, nullable=False, default=date.today)
    membership_end = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), onupdate=db.func.now()
    )

    # Relationships
    general_bookings = db.relationship(
        'GeneralBooking', backref='member', lazy='dynamic', cascade="all, delete-orphan"
    )
    competition_bookings = db.relationship(
        'CompetitionBooking', backref='member', lazy='dynamic', cascade="all, delete-orphan"
    )
    range_bookings = db.relationship(
        'RangeBooking', backref='member', lazy='dynamic', cascade="all, delete-orphan"
    )
    coaching_bookings = db.relationship(
        'CoachingBooking', backref='member', lazy='dynamic', cascade="all, delete-orphan"
    )

    def set_password(self, password):
        """Hash and set the password."""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        """Verify the password against the stored hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<Member {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return Member.query.get(int(user_id))
