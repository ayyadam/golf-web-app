from ..extensions import db


class TeeTime(db.Model):
    """Available tee time slot for general play."""
    __tablename__ = 'tee_times'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    max_players = db.Column(db.Integer, default=4, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    # selectin (not dynamic): booked_count sums this collection, and listing
    # many tee times would otherwise fire one bookings query per row (N+1).
    # selectin batch-loads all bookings for the loaded set in a single query.
    bookings = db.relationship(
        'GeneralBooking', backref='tee_time', lazy='selectin',
        cascade='all, delete-orphan'
    )

    @property
    def booked_count(self):
        """Number of players booked for this tee time."""
        return sum(b.group_size for b in self.bookings)

    @property
    def slots_remaining(self):
        """Number of slots still available."""
        return self.max_players - self.booked_count

    def __repr__(self):
        return f'<TeeTime {self.date} {self.time}>'

    __table_args__ = (
        db.UniqueConstraint('date', 'time', name='uq_tee_time_date_time'),
    )


class GeneralBooking(db.Model):
    """Booking for a general play tee time."""
    __tablename__ = 'general_bookings'

    id = db.Column(db.Integer, primary_key=True)
    tee_time_id = db.Column(
        db.Integer, db.ForeignKey('tee_times.id'), nullable=False
    )
    member_id = db.Column(
        db.Integer, db.ForeignKey('members.id'), nullable=True
    )
    visitor_id = db.Column(
        db.Integer, db.ForeignKey('visitors.id'), nullable=True
    )
    group_size = db.Column(db.Integer, default=1, nullable=False)
    booked_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    players = db.relationship(
        'BookingPlayer', backref='booking', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<GeneralBooking {self.id} - TeeTime {self.tee_time_id}>'


class BookingPlayer(db.Model):
    """Additional players in a group booking (2-ball, 3-ball, 4-ball)."""
    __tablename__ = 'booking_players'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer, db.ForeignKey('general_bookings.id'), nullable=False
    )
    player_name = db.Column(db.String(200), nullable=False)
    handicap = db.Column(db.Numeric(3, 1), nullable=True)

    def __repr__(self):
        return f'<BookingPlayer {self.player_name}>'
