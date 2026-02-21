from ..extensions import db


class Coach(db.Model):
    """Golf coach profile."""
    __tablename__ = 'coaches'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    speciality = db.Column(db.String(200), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    coaching_times = db.relationship(
        'CoachingTime', backref='coach', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<Coach {self.first_name} {self.last_name}>'


class CoachingTime(db.Model):
    """Available coaching lesson time slot."""
    __tablename__ = 'coaching_times'

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(
        db.Integer, db.ForeignKey('coaches.id'), nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration_mins = db.Column(db.Integer, default=60, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    booking = db.relationship(
        'CoachingBooking', backref='coaching_time', uselist=False
    )

    def __repr__(self):
        return f'<CoachingTime Coach {self.coach_id} - {self.date} {self.time}>'


class CoachingBooking(db.Model):
    """Booking for an individual coaching lesson."""
    __tablename__ = 'coaching_bookings'

    id = db.Column(db.Integer, primary_key=True)
    coaching_time_id = db.Column(
        db.Integer, db.ForeignKey('coaching_times.id'),
        nullable=False, unique=True
    )
    member_id = db.Column(
        db.Integer, db.ForeignKey('members.id'), nullable=True
    )
    visitor_id = db.Column(
        db.Integer, db.ForeignKey('visitors.id'), nullable=True
    )
    booked_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<CoachingBooking {self.id}>'
