from ..extensions import db


class RangeTime(db.Model):
    """Available time slot for a Trackman range bay."""
    __tablename__ = 'range_times'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    bay_number = db.Column(db.Integer, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    booking = db.relationship(
        'RangeBooking', backref='range_time', uselist=False
    )

    def __repr__(self):
        return f'<RangeTime Bay {self.bay_number} - {self.date} {self.time}>'

    __table_args__ = (
        db.UniqueConstraint(
            'date', 'time', 'bay_number', name='uq_range_time_slot'
        ),
    )


class RangeBooking(db.Model):
    """Booking for a range bay time slot."""
    __tablename__ = 'range_bookings'

    id = db.Column(db.Integer, primary_key=True)
    range_time_id = db.Column(
        db.Integer, db.ForeignKey('range_times.id'), nullable=False, unique=True
    )
    member_id = db.Column(
        db.Integer, db.ForeignKey('members.id'), nullable=True
    )
    visitor_id = db.Column(
        db.Integer, db.ForeignKey('visitors.id'), nullable=True
    )
    booked_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<RangeBooking {self.id}>'
