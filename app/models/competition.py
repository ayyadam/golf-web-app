from ..extensions import db


class Competition(db.Model):
    """Internal club competition."""
    __tablename__ = 'competitions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    format = db.Column(
        db.String(50), nullable=False
    )  # 'Stableford', 'Medal', 'Matchplay', etc.
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    tee_times = db.relationship(
        'CompetitionTeeTime', backref='competition', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Competition {self.name} ({self.format})>'


class CompetitionTeeTime(db.Model):
    """Tee time slot for a competition."""
    __tablename__ = 'competition_tee_times'

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(
        db.Integer, db.ForeignKey('competitions.id'), nullable=False
    )
    time = db.Column(db.Time, nullable=False)
    max_players = db.Column(db.Integer, default=3, nullable=False)

    # Relationships
    bookings = db.relationship(
        'CompetitionBooking', backref='comp_tee_time', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @property
    def booked_count(self):
        return self.bookings.count()

    @property
    def slots_remaining(self):
        return self.max_players - self.booked_count

    def __repr__(self):
        return f'<CompTeeTime {self.competition_id} @ {self.time}>'


class CompetitionBooking(db.Model):
    """Booking for a competition tee time — members only."""
    __tablename__ = 'competition_bookings'

    id = db.Column(db.Integer, primary_key=True)
    comp_tee_time_id = db.Column(
        db.Integer, db.ForeignKey('competition_tee_times.id'), nullable=False
    )
    member_id = db.Column(
        db.Integer, db.ForeignKey('members.id'), nullable=False
    )
    booked_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<CompBooking {self.id} - Member {self.member_id}>'
