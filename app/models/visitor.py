from ..extensions import db


class Visitor(db.Model):
    """Visitor model — non-members booking tee times or lessons."""
    __tablename__ = 'visitors'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    handicap = db.Column(db.Numeric(3, 1), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    general_bookings = db.relationship(
        'GeneralBooking', backref='visitor', lazy='dynamic'
    )
    range_bookings = db.relationship(
        'RangeBooking', backref='visitor', lazy='dynamic'
    )
    coaching_bookings = db.relationship(
        'CoachingBooking', backref='visitor', lazy='dynamic'
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<Visitor {self.first_name} {self.last_name}>'
