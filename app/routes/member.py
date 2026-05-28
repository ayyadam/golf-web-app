from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ..extensions import db
from ..models import (
    Member,
    TeeTime, GeneralBooking, BookingPlayer,
    Competition, CompetitionTeeTime, CompetitionBooking,
    Coach, CoachingTime, CoachingBooking,
    RangeTime, RangeBooking
)
from ..services.booking_service import (
    PlayerInput, create_general_booking, parse_handicap,
    validate_general_booking, validate_player_handicaps,
)
from datetime import date, datetime, timedelta

member_bp = Blueprint('member', __name__)


@member_bp.before_request
@login_required
def require_login():
    """All member routes require authentication."""


@member_bp.route('/dashboard')
def dashboard():
    """Member dashboard — upcoming bookings overview."""
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    # General Tee Times
    upcoming_bookings = GeneralBooking.query.join(TeeTime).filter(
        db.or_(
            GeneralBooking.member_id == current_user.id,
            GeneralBooking.players.any(BookingPlayer.player_name == current_user.full_name)
        ),
        TeeTime.date >= today
    ).order_by(TeeTime.date, TeeTime.time).all()
    upcoming_bookings = [b for b in upcoming_bookings if not (
        b.tee_time.date == today and b.tee_time.time < current_time)]

    # Competitions
    upcoming_comp_bookings = CompetitionBooking.query.join(
        CompetitionTeeTime
    ).join(Competition).filter(
        CompetitionBooking.member_id == current_user.id,
        Competition.date >= today
    ).order_by(Competition.date).all()
    upcoming_comp_bookings = [b for b in upcoming_comp_bookings if not (
        b.comp_tee_time.competition.date == today and b.comp_tee_time.time < current_time)]

    # Coaching
    upcoming_coaching = CoachingBooking.query.join(
        CoachingTime
    ).filter(
        CoachingBooking.member_id == current_user.id,
        CoachingTime.date >= today
    ).order_by(CoachingTime.date, CoachingTime.time).all()
    upcoming_coaching = [b for b in upcoming_coaching if not (
        b.coaching_time.date == today and b.coaching_time.time < current_time)]

    # Range Bays
    upcoming_range_bookings = RangeBooking.query.join(
        RangeTime
    ).filter(
        RangeBooking.member_id == current_user.id,
        RangeTime.date >= today
    ).order_by(RangeTime.date, RangeTime.time).all()
    upcoming_range_bookings = [b for b in upcoming_range_bookings if not (
        b.range_time.date == today and b.range_time.time < current_time)]

    return render_template(
        'member/dashboard.html',
        upcoming_bookings=upcoming_bookings,
        upcoming_comp_bookings=upcoming_comp_bookings,
        upcoming_coaching=upcoming_coaching,
        upcoming_range_bookings=upcoming_range_bookings
    )


@member_bp.route('/coaching')
def coaching():
    """Browse available coaches."""
    coaches = Coach.query.filter_by(is_active=True).all()
    return render_template('member/coaching.html', coaches=coaches)


@member_bp.route('/coaching/<int:coach_id>/book', methods=['GET', 'POST'])
def book_coaching(coach_id):
    """View available coaching slots and book a lesson."""
    coach = Coach.query.get_or_404(coach_id)

    if request.method == 'POST':
        coaching_time_id = request.form.get('coaching_time_id', type=int)
        ct = CoachingTime.query.get_or_404(coaching_time_id)

        # Validate slot is available
        if ct.booking:
            flash('This time slot is already booked.', 'danger')
            return redirect(url_for('member.book_coaching', coach_id=coach_id))

        # Prevent booking past slots
        now = datetime.now()
        slot_dt = datetime.combine(ct.date, ct.time)
        if slot_dt <= now:
            flash('This coaching slot has already passed.', 'danger')
            return redirect(url_for('member.book_coaching', coach_id=coach_id))

        booking = CoachingBooking(
            coaching_time_id=coaching_time_id,
            member_id=current_user.id
        )
        db.session.add(booking)
        db.session.commit()
        flash(
            f'Coaching lesson booked with {
                coach.full_name} at {
                ct.time.strftime("%H:%M")} on {
                ct.date.strftime("%d/%m/%Y")}!',
            'success')
        return redirect(url_for('member.dashboard'))

    # GET: show available time slots
    selected_date = request.args.get('date', date.today().isoformat())
    coaching_times = CoachingTime.query.filter(
        CoachingTime.coach_id == coach_id,
        CoachingTime.date == selected_date,
        CoachingTime.is_available == True  # noqa: E712
    ).order_by(CoachingTime.time).all()

    # Filter out past slots if viewing today
    if str(selected_date) == str(date.today()):
        now_time = datetime.now().time()
        coaching_times = [ct for ct in coaching_times if ct.time > now_time]

    # Check if member already has a coaching booking
    existing_booking = CoachingBooking.query.join(CoachingTime).filter(
        CoachingBooking.member_id == current_user.id,
        CoachingTime.date >= date.today()
    ).first()

    return render_template(
        'member/book_coaching.html',
        coach=coach,
        coaching_times=coaching_times,
        selected_date=selected_date,
        today=date.today().isoformat(),
        existing_booking=existing_booking
    )


def _filter_available_tee_times(selected_date):
    """Return available general-play tee times for the given date,
    filtering out past times and respecting competition-day rules."""
    now = datetime.now()
    today = date.today()

    # Base query: available tee times for the selected date
    query = TeeTime.query.filter(
        TeeTime.date == selected_date,
        TeeTime.is_available == True  # noqa: E712
    )

    # If selected date is today, exclude tee times that have already passed
    if str(selected_date) == str(today):
        query = query.filter(TeeTime.time > now.time())

    # If selected date is in the past, return nothing
    if str(selected_date) < str(today):
        return []

    tee_times = query.order_by(TeeTime.time).all()

    # Competition-day rule: general play only 30 min after last comp tee time
    competitions_on_date = Competition.query.filter(
        Competition.date == selected_date,
        Competition.is_active == True  # noqa: E712
    ).all()

    if competitions_on_date:
        # Find the latest competition tee time across all competitions on this date
        latest_comp_time = None
        for comp in competitions_on_date:
            for ctt in getattr(comp, 'tee_times', []):
                if latest_comp_time is None or ctt.time > latest_comp_time:
                    latest_comp_time = ctt.time

        if latest_comp_time is not None:
            # Pyre type assertion for combine function
            from datetime import time as dt_time
            if not isinstance(latest_comp_time, dt_time):
                return tee_times

            # General play allowed 30 min after the last competition tee time
            cutoff_dt = datetime.combine(today, latest_comp_time) + timedelta(minutes=30)
            cutoff_time = cutoff_dt.time()
            tee_times = [tt for tt in tee_times if tt.time >= cutoff_time]

    return tee_times


@member_bp.route('/book-tee-time', methods=['GET', 'POST'])
def book_tee_time():
    """Book a general play tee time."""
    if request.method == 'POST':
        tee_time_id = request.form.get('tee_time_id', type=int)
        group_size = request.form.get('group_size', 1, type=int)
        tee_time = TeeTime.query.get_or_404(tee_time_id)

        players = [
            PlayerInput(
                name=request.form.get(f'player_{i}_name', '').strip(),
                handicap=parse_handicap(request.form.get(f'player_{i}_handicap')),
            )
            for i in range(1, group_size)
        ]

        error = (
            validate_general_booking(tee_time, group_size, member=current_user)
            or validate_player_handicaps(players)
        )
        if error:
            category = 'warning' if error.code == 'already_booked' else 'danger'
            flash(error.message, category)
            return redirect(url_for(
                'member.book_tee_time', date=request.form.get('date')
            ))

        create_general_booking(
            tee_time=tee_time,
            group_size=group_size,
            member=current_user,
            players=players,
        )
        db.session.commit()
        flash('Tee time booked successfully!', 'success')
        return redirect(url_for('member.dashboard'))

    # GET: show available tee times (filtered for past times + competition rules)
    selected_date = request.args.get('date', date.today().isoformat())
    try:
        parsed_date = date.fromisoformat(selected_date)
    except ValueError:
        parsed_date = date.today()
        selected_date = parsed_date.isoformat()

    tee_times = _filter_available_tee_times(parsed_date)

    # Fetch user's existing bookings for this day to highlight them
    user_bookings = GeneralBooking.query.join(TeeTime).filter(
        TeeTime.date == parsed_date,
        db.or_(
            GeneralBooking.member_id == current_user.id,
            GeneralBooking.players.any(BookingPlayer.player_name == current_user.full_name)
        )
    ).all()

    return render_template(
        'member/book_tee_time.html',
        tee_times=tee_times,
        selected_date=selected_date,
        today=date.today().isoformat(),
        user_bookings=user_bookings
    )


@member_bp.route('/api/members/search')
def search_members():
    """API endpoint to search for members by name for autocomplete."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 1:
        return {'members': []}

    # Search by full name (first + last)
    search_term = f"%{query}%"
    members = Member.query.filter(
        db.or_(
            Member.first_name.ilike(search_term),
            Member.last_name.ilike(search_term),
            (Member.first_name + ' ' + Member.last_name).ilike(search_term)
        ),
        Member.is_active == True,  # noqa: E712
        Member.id != current_user.id  # Exclude current user
    ).limit(10).all()

    results = []
    for member in members:
        results.append({
            'id': member.id,
            'name': member.full_name,
            'handicap': float(member.handicap) if member.handicap else None
        })

    return {'members': results}


@member_bp.route('/competitions')
def competitions():
    """View upcoming competition schedule."""
    today = date.today()
    upcoming = Competition.query.filter(
        Competition.date >= today,
        Competition.is_active == True  # noqa: E712
    ).order_by(Competition.date).all()

    # Get user's bookings mapped by competition ID
    user_bookings_query = CompetitionBooking.query.join(
        CompetitionTeeTime
    ).filter(
        CompetitionBooking.member_id == current_user.id,
        CompetitionTeeTime.competition_id.in_([c.id for c in upcoming]) if upcoming else False
    ).all()

    user_bookings = {b.comp_tee_time.competition_id: b for b in user_bookings_query}

    return render_template('member/competitions.html', competitions=upcoming, user_bookings=user_bookings)


@member_bp.route('/competitions/<int:comp_id>/book', methods=['GET', 'POST'])
def book_competition(comp_id):
    """Book a competition tee time."""
    competition = Competition.query.get_or_404(comp_id)

    # Prevent booking past competitions
    if competition.date < date.today():
        flash('This competition has already passed.', 'danger')
        return redirect(url_for('member.competitions'))

    # Find existing booking for this competition (any tee time)
    all_ctt_ids = [ctt.id for ctt in competition.tee_times]
    existing_booking = CompetitionBooking.query.filter(
        CompetitionBooking.comp_tee_time_id.in_(all_ctt_ids),
        CompetitionBooking.member_id == current_user.id
    ).first() if all_ctt_ids else None

    if request.method == 'POST':
        action = request.form.get('action', 'book')

        if action == 'cancel':
            if existing_booking:
                db.session.delete(existing_booking)
                db.session.commit()
                flash('Your competition booking has been cancelled.', 'success')
            return redirect(url_for('member.book_competition', comp_id=comp_id))

        # action == 'book' (or swap)
        comp_tee_time_id = request.form.get('comp_tee_time_id', type=int)
        comp_tee_time = CompetitionTeeTime.query.get_or_404(comp_tee_time_id)

        # Prevent booking past competition tee times
        now = datetime.now()
        comp_tee_dt = datetime.combine(competition.date, comp_tee_time.time)
        if comp_tee_dt <= now:
            flash('This competition tee time has already passed.', 'danger')
            return redirect(url_for('member.book_competition', comp_id=comp_id))

        # If already booked for same tee time, nothing to do
        if existing_booking and existing_booking.comp_tee_time_id == comp_tee_time_id:
            flash('You are already booked for this tee time.', 'info')
            return redirect(url_for('member.book_competition', comp_id=comp_id))

        # If already booked for a different tee time, swap
        if existing_booking:
            old_time = existing_booking.comp_tee_time.time.strftime('%H:%M')
            db.session.delete(existing_booking)
            db.session.flush()  # ensure slot is freed before re-checking

        if comp_tee_time.slots_remaining <= 0:
            flash('This tee time is fully booked.', 'danger')
            return redirect(url_for('member.book_competition', comp_id=comp_id))

        booking = CompetitionBooking(
            comp_tee_time_id=comp_tee_time_id,
            member_id=current_user.id
        )
        db.session.add(booking)
        db.session.commit()

        if existing_booking:
            flash(f'Switched from {old_time} to {comp_tee_time.time.strftime("%H:%M")}.', 'success')
        else:
            flash('Competition tee time booked!', 'success')
        return redirect(url_for('member.book_competition', comp_id=comp_id))

    # GET: show competition tee times, filtering out past ones if today
    comp_tee_times = CompetitionTeeTime.query.filter_by(
        competition_id=comp_id
    ).order_by(CompetitionTeeTime.time).all()

    # If competition is today, filter out past tee times
    if competition.date == date.today():
        now = datetime.now().time()
        comp_tee_times = [ctt for ctt in comp_tee_times if ctt.time > now]

    return render_template(
        'member/book_competition.html',
        competition=competition,
        comp_tee_times=comp_tee_times,
        existing_booking=existing_booking
    )


@member_bp.route('/competitions/<int:comp_id>/cancel', methods=['POST'])
@login_required
def cancel_competition_booking(comp_id):
    """Cancel the current user's competition booking."""
    competition = Competition.query.get_or_404(comp_id)
    all_ctt_ids = [ctt.id for ctt in competition.tee_times]
    booking = CompetitionBooking.query.filter(
        CompetitionBooking.comp_tee_time_id.in_(all_ctt_ids),
        CompetitionBooking.member_id == current_user.id
    ).first()
    if booking:
        db.session.delete(booking)
        db.session.commit()
        flash('Your competition booking has been cancelled.', 'success')
    else:
        flash('No booking found to cancel.', 'warning')
    return redirect(url_for('member.dashboard'))


@member_bp.route('/cancel-general-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_general_booking(booking_id):
    """Cancel a member's general tee time or remove them from it."""
    booking = GeneralBooking.query.get_or_404(booking_id)

    if booking.member_id == current_user.id:
        # Primary booker: delete entire booking
        db.session.delete(booking)
        db.session.commit()
        flash('Your tee time booking has been cancelled.', 'success')
        return redirect(url_for('member.dashboard'))

    # Check if they are an additional player
    player = booking.players.filter_by(player_name=current_user.full_name).first()
    if player:
        db.session.delete(player)
        booking.group_size -= 1
        db.session.commit()
        flash('You have been removed from the tee time.', 'success')
        return redirect(url_for('member.dashboard'))

    flash('Unauthorized.', 'danger')
    return redirect(url_for('member.dashboard'))


@member_bp.route('/book-range', methods=['GET', 'POST'])
def book_range():
    """Book a range bay."""
    selected_date_str = request.args.get('date', date.today().isoformat())
    try:
        selected_date = date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date = date.today()
        selected_date_str = selected_date.isoformat()

    if request.method == 'POST':
        range_time_id = request.form.get('range_time_id', type=int)
        rt = RangeTime.query.get_or_404(range_time_id)

        # Don't allow booking if already booked
        if rt.booking:
            flash(f'Bay {rt.bay_number} at {rt.time.strftime("%H:%M")} is already booked.', 'danger')
            return redirect(url_for('member.book_range', date=selected_date_str))

        # Prevent booking past times
        now = datetime.now()
        rt_dt = datetime.combine(rt.date, rt.time)
        if rt_dt < now:
            flash('Cannot book a time in the past.', 'danger')
            return redirect(url_for('member.book_range', date=selected_date_str))

        # Prevent concurrent bay bookings (same date, same time)
        existing_concurrent_booking = RangeBooking.query.join(RangeTime).filter(
            RangeBooking.member_id == current_user.id,
            RangeTime.date == rt.date,
            RangeTime.time == rt.time
        ).first()

        if existing_concurrent_booking:
            flash(f'You already have a range bay booked at {rt.time.strftime("%H:%M")}.', 'warning')
            return redirect(url_for('member.book_range', date=selected_date_str))

        booking = RangeBooking(
            range_time_id=rt.id,
            member_id=current_user.id
        )
        db.session.add(booking)
        db.session.commit()
        flash(f'Successfully booked Bay {rt.bay_number} for {rt.time.strftime("%H:%M")}', 'success')
        return redirect(url_for('member.dashboard'))

    # GET request
    range_times = RangeTime.query.filter_by(date=selected_date).order_by(RangeTime.time, RangeTime.bay_number).all()

    # Filter out past times for today
    if selected_date == date.today():
        now_time = datetime.now().time()
        range_times = [rt for rt in range_times if rt.time > now_time]

    # Group by time for the UI matrix
    times_dict = {}
    for rt in range_times:
        time_str = rt.time.strftime('%H:%M')
        if time_str not in times_dict:
            times_dict[time_str] = []
        times_dict[time_str].append(rt)

    # Get user's current bookings for this day to show a banner
    user_bookings = RangeBooking.query.join(RangeTime).filter(
        RangeBooking.member_id == current_user.id,
        RangeTime.date == selected_date
    ).all()

    return render_template(
        'member/book_range.html',
        selected_date=selected_date_str,
        today=date.today().isoformat(),
        times_dict=times_dict,
        user_bookings=user_bookings
    )


@member_bp.route('/cancel-range-booking/<int:booking_id>', methods=['POST'])
def cancel_range_booking(booking_id):
    """Cancel a member's own range booking from the dashboard."""
    booking = RangeBooking.query.get_or_404(booking_id)

    if booking.member_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('member.dashboard'))

    db.session.delete(booking)
    db.session.commit()
    flash('Your range booking has been cancelled.', 'success')
    return redirect(url_for('member.dashboard'))


@member_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Member profile and password management."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            email = request.form.get('email', '').strip()
            telephone = request.form.get('telephone', '').strip()

            if not email or '@' not in email or '.' not in email:
                flash('Please provide a valid email address.', 'danger')
                return redirect(url_for('member.profile'))

            if not telephone or len(telephone) < 7:
                flash('Please provide a valid telephone number.', 'danger')
                return redirect(url_for('member.profile'))

            # Check if email is available (not taken by another user)
            existing_user = Member.query.filter(Member.email == email, Member.id != current_user.id).first()
            if existing_user:
                flash('This email address is already in use by another account.', 'danger')
                return redirect(url_for('member.profile'))

            current_user.email = email
            current_user.telephone = telephone
            db.session.commit()
            flash('Your personal details have been successfully updated.', 'success')
            return redirect(url_for('member.profile'))

        elif action == 'update_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Basic validations
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('member.profile'))

            if not new_password or len(new_password) < 8:
                flash('New password must be at least 8 characters long.', 'danger')
                return redirect(url_for('member.profile'))

            if not any(c.isupper() for c in new_password):
                flash('New password must contain at least 1 capital letter.', 'danger')
                return redirect(url_for('member.profile'))

            if not any(c.isdigit() for c in new_password):
                flash('New password must contain at least 1 number.', 'danger')
                return redirect(url_for('member.profile'))

            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('member.profile'))

            # Update password
            current_user.set_password(new_password)
            db.session.commit()
            flash('Your password has been successfully updated.', 'success')
            return redirect(url_for('member.profile'))

    return render_template('member/profile.html')
