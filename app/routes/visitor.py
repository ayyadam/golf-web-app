from flask import Blueprint, render_template, redirect, url_for, flash, request
from ..extensions import db
from ..models import (
    Visitor, TeeTime, GeneralBooking, MembershipRequest
)
from ..routes.member import _filter_available_tee_times
from ..services.booking_service import (
    PlayerInput, create_general_booking, parse_handicap, validate_general_booking,
)
from datetime import date

visitor_bp = Blueprint('visitor', __name__)


@visitor_bp.route('/book-tee-time', methods=['GET', 'POST'])
def book_tee_time():
    """Visitor tee time booking — requires visitor details."""
    if request.method == 'POST':
        tee_time_id = request.form.get('tee_time_id', type=int)
        group_size = request.form.get('group_size', 1, type=int)
        tee_time = TeeTime.query.get_or_404(tee_time_id)

        error = validate_general_booking(tee_time, group_size)
        if error:
            flash(error.message, 'danger')
            return redirect(url_for('visitor.book_tee_time'))

        # Validation passed — now persist the visitor and the booking together
        visitor = Visitor(
            first_name=request.form.get('first_name', '').strip(),
            last_name=request.form.get('last_name', '').strip(),
            email=request.form.get('email', '').strip(),
            telephone=request.form.get('telephone', '').strip(),
            handicap=parse_handicap(request.form.get('handicap')),
        )
        db.session.add(visitor)
        db.session.flush()  # obtain visitor.id

        players = [
            PlayerInput(
                name=request.form.get(f'player_{i}_name', '').strip(),
                handicap=parse_handicap(request.form.get(f'player_{i}_handicap')),
            )
            for i in range(1, group_size)
        ]

        booking = create_general_booking(
            tee_time=tee_time,
            group_size=group_size,
            visitor_id=visitor.id,
            players=players,
        )
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
