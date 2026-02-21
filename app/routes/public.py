from flask import Blueprint, render_template
from ..models import Hole

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def home():
    """Home page — club welcome and navigation."""
    return render_template('public/home.html')


@public_bp.route('/course')
def course_overview():
    """18-hole course overview and walkthrough."""
    holes = Hole.query.order_by(Hole.hole_number).all()
    return render_template('public/course.html', holes=holes)


@public_bp.route('/course/hole/<int:hole_number>')
def hole_detail(hole_number):
    """Individual hole detail page."""
    hole = Hole.query.filter_by(hole_number=hole_number).first_or_404()
    return render_template('public/hole_detail.html', hole=hole)


@public_bp.route('/course/scorecard')
def scorecard():
    """Full 18-hole scorecard."""
    holes = Hole.query.order_by(Hole.hole_number).all()
    return render_template('public/scorecard.html', holes=holes)


@public_bp.route('/membership')
def membership():
    """Membership overview — pricing and benefits."""
    return render_template('public/membership.html')


@public_bp.route('/trackman')
def trackman():
    """Trackman practice range overview."""
    return render_template('public/trackman.html')


@public_bp.route('/practice')
def practice():
    """Chipping and putting practice area overview."""
    return render_template('public/practice.html')


@public_bp.route('/coaching')
def coaching():
    """Coaching overview — coaches and booking."""
    from ..models import Coach
    coaches = Coach.query.filter_by(is_active=True).all()
    return render_template('public/coaching.html', coaches=coaches)
