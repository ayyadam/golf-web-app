from ..extensions import db


class Hole(db.Model):
    """Golf course hole — 18 holes with details for the course walkthrough."""
    __tablename__ = 'holes'

    id = db.Column(db.Integer, primary_key=True)
    hole_number = db.Column(db.Integer, unique=True, nullable=False)
    par = db.Column(db.Integer, nullable=False)
    yards_blues = db.Column(db.Integer, nullable=False)
    yards_whites = db.Column(db.Integer, nullable=False)
    yards_yellows = db.Column(db.Integer, nullable=False)
    yards_reds = db.Column(db.Integer, nullable=False)
    stroke_index = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=True)  # Optional hole nickname
    description = db.Column(db.Text, nullable=True)
    tips = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Hole {self.hole_number} - Par {self.par}>'
