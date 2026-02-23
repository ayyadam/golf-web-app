from flask import Blueprint, render_template, redirect, url_for, flash, request
from ..extensions import db
from ..models import (
    Visitor, TeeTime, GeneralBooking, BookingPlayer,
    MembershipRequest
)
from ..routes.member import _filter_available_tee_times
from datetime import date, datetime

visitor_bp = Blueprint('visitor', __name__)


def _parse_hcp(v):
    """Helper to parse raw HTML input (e.g. +2.0) into the expected internal negative float structure."""
    if not v or not str(v).strip(): return None
    v = str(v).strip()
    is_plus = v.startswith('+')
    try:
        numeric = float(v.replace('+', ''))
        return -abs(numeric) if is_plus else numeric
    except ValueError:
        return None


@visitor_bp.route('/book-tee-time', methods=['GET', 'POST'])
def book_tee_time():
    """Visitor tee time booking — requires visitor details."""
    if request.method == 'POST':
        # Create or find visitor
        visitor = Visitor(
            first_name=request.form.get('first_name', '').strip(),
            last_name=request.form.get('last_name', '').strip(),
            email=request.form.get('email', '').strip(),
            telephone=request.form.get('telephone', '').strip(),
            handicap=_parse_hcp(request.form.get('handicap')),
        )
        db.session.add(visitor)
        db.session.flush()  # Get the visitor ID

        tee_time_id = request.form.get('tee_time_id', type=int)
        group_size = request.form.get('group_size', 1, type=int)
        tee_time = TeeTime.query.get_or_404(tee_time_id)

        # Prevent booking past tee times
        now = datetime.now()
        tee_dt = datetime.combine(tee_time.date, tee_time.time)
        if tee_dt <= now:
            flash('This tee time has already passed.', 'danger')
            db.session.rollback()
            return redirect(url_for('visitor.book_tee_time'))

        if group_size > tee_time.slots_remaining:
            flash('Not enough slots available for your group size.', 'danger')
            db.session.rollback()
            return redirect(url_for('visitor.book_tee_time'))

        booking = GeneralBooking(
            tee_time_id=tee_time_id,
            visitor_id=visitor.id,
            group_size=group_size
        )
        db.session.add(booking)

        # Add additional players
        for i in range(1, group_size):
            player_name = request.form.get(f'player_{i}_name', '').strip()
            player_handicap = _parse_hcp(request.form.get(f'player_{i}_handicap'))
            if player_name:
                player = BookingPlayer(
                    booking=booking,
                    player_name=player_name,
                    handicap=player_handicap
                )
                db.session.add(player)

        db.session.commit()
        flash('Tee time booked successfully! Enjoy your round.', 'success')
        return redirect(url_for('visitor.booking_confirmation', booking_id=booking.id))

    # GET: show date selection and available tee times (filtered)
    selected_date = request.args.get('date', date.today().isoformat())
    tee_times = _filter_available_tee_times(selected_date)

    return render_template(
        'visitor/book_tee_time.html',
        tee_times=tee_times,
        selected_date=selected_date,
        today=date.today().isoformat()
    )


@visitor_bp.route('/booking-confirmation/<int:booking_id>')
def booking_confirmation(booking_id):
    """Show booking confirmation to visitor."""
    booking = GeneralBooking.query.get_or_404(booking_id)
    return render_template('visitor/confirmation.html', booking=booking)


@visitor_bp.route('/membership-request', methods=['POST'])
def membership_request():
    """Submit a membership request from the public membership page."""
    req = MembershipRequest(
        first_name=request.form.get('first_name', '').strip(),
        last_name=request.form.get('last_name', '').strip(),
        email=request.form.get('email', '').strip(),
        telephone=request.form.get('telephone', '').strip(),
        membership_type=request.form.get('membership_type', 'Full Year'),
        message=request.form.get('message', '').strip(),
    )
    db.session.add(req)
    db.session.commit()
    flash(
        'Your membership request has been submitted! '
        'We will be in touch shortly.',
        'success'
    )
    return redirect(url_for('public.membership'))
