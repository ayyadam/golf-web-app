from ..extensions import db


class MembershipRequest(db.Model):
    """Membership contact/request form submission."""
    __tablename__ = 'membership_requests'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    membership_type = db.Column(
        db.String(20), nullable=False, default='Full Year'
    )
    message = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(20), nullable=False, default='pending'
    )  # 'pending', 'approved', 'rejected'
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())
    reviewed_at = db.Column(db.DateTime, nullable=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<MembershipRequest {self.first_name} {self.last_name} ({self.status})>'
