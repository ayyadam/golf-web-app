from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from ..extensions import db
from ..models import (
    Member, TeeTime, GeneralBooking,
    Competition, CompetitionTeeTime, CompetitionBooking,
    RangeTime, RangeBooking,
    Coach, CoachingTime, CoachingBooking,
    MembershipRequest
)
from .auth import admin_required
from datetime import date, datetime, time as dt_time
from ..services.tee_time_utils import generate_tee_time_slots

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@admin_required
def require_admin():
    """All admin routes require admin privileges."""
    pass


# ── Dashboard ──────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
def dashboard():
    """Admin dashboard — overview statistics."""
    stats = {
        'total_members': Member.query.filter_by(is_active=True).count(),
        'pending_requests': MembershipRequest.query.filter_by(status='pending').count(),
        'upcoming_competitions': Competition.query.filter(
            Competition.date >= date.today(),
            Competition.is_active == True  # noqa: E712
        ).count(),
        'todays_bookings': GeneralBooking.query.join(TeeTime).filter(
            TeeTime.date == date.today()
        ).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


# ── Membership Requests ───────────────────────────────────────────────────────

@admin_bp.route('/membership-requests')
def membership_requests():
    """View all membership requests."""
    requests_list = MembershipRequest.query.order_by(
        MembershipRequest.submitted_at.desc()
    ).all()
    return render_template(
        'admin/membership_requests.html', requests=requests_list
    )


@admin_bp.route('/membership-requests/<int:req_id>/approve', methods=['POST'])
def approve_membership(req_id):
    """Approve a membership request and create a new member."""
    req = MembershipRequest.query.get_or_404(req_id)
    if req.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('admin.membership_requests'))

    # Create member from request
    username = f"{req.first_name.lower()}.{req.last_name.lower()}"
    # Handle duplicate usernames
    base_username = username
    counter = 1
    while Member.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1

    member = Member(
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        telephone=req.telephone,
        username=username,
        membership_type=req.membership_type,
        membership_start=date.today(),
    )
    # Set a default password (admin should communicate to member to change it)
    member.set_password('Welcome123!')

    req.status = 'approved'
    req.reviewed_at = datetime.utcnow()

    db.session.add(member)
    db.session.commit()

    flash(
        f'Membership approved for {req.full_name}. '
        f'Username: {username}, Default password: Welcome123!',
        'success'
    )
    return redirect(url_for('admin.membership_requests'))


@admin_bp.route('/membership-requests/<int:req_id>/reject', methods=['POST'])
def reject_membership(req_id):
    """Reject a membership request."""
    req = MembershipRequest.query.get_or_404(req_id)
    req.status = 'rejected'
    req.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'Membership request from {req.full_name} rejected.', 'info')
    return redirect(url_for('admin.membership_requests'))


# ── Manage Members ─────────────────────────────────────────────────────────────

@admin_bp.route('/members', methods=['GET', 'POST'])
def manage_members():
    """View all members and create new ones."""
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone', '').strip()
        handicap = request.form.get('handicap', type=float)
        membership_type = request.form.get('membership_type', 'Full Year')

        if not all([first_name, last_name, email, telephone]):
            flash('First name, last name, email, and telephone are required.', 'danger')
            return redirect(url_for('admin.manage_members'))

        # Check for duplicate email
        if Member.query.filter_by(email=email).first():
            flash('A member with this email already exists.', 'danger')
            return redirect(url_for('admin.manage_members'))

        # Auto-generate username
        username = f"{first_name.lower()}.{last_name.lower()}"
        base_username = username
        counter = 1
        while Member.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        member = Member(
            first_name=first_name,
            last_name=last_name,
            email=email,
            telephone=telephone,
            handicap=handicap,
            username=username,
            membership_type=membership_type,
            membership_start=date.today(),
        )
        member.set_password('Welcome123!')
        db.session.add(member)
        db.session.commit()

        flash(
            f'Member created: {member.full_name}. '
            f'Username: {username}, Default password: Welcome123!',
            'success'
        )
        return redirect(url_for('admin.manage_members'))

    members = Member.query.order_by(Member.last_name).all()
    return render_template('admin/members.html', members=members)


@admin_bp.route('/members/<int:member_id>/delete', methods=['POST'])
def delete_member(member_id):
    """Delete a member from the system."""
    member = Member.query.get_or_404(member_id)
    
    # Prevent admin from deleting themselves
    if member.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.manage_members'))
        
    db.session.delete(member)
    db.session.commit()
    flash(f'{member.full_name} has been permanently removed.', 'success')
    return redirect(url_for('admin.manage_members'))


@admin_bp.route('/members/<int:member_id>/edit', methods=['GET', 'POST'])
def edit_member(member_id):
    """Edit an existing member."""
    member = Member.query.get_or_404(member_id)

    if request.method == 'POST':
        member.first_name = request.form.get('first_name', member.first_name)
        member.last_name = request.form.get('last_name', member.last_name)
        member.email = request.form.get('email', member.email)
        member.telephone = request.form.get('telephone', member.telephone)
        member.handicap = request.form.get('handicap', type=float)
        member.membership_type = request.form.get(
            'membership_type', member.membership_type
        )
        member.is_active = request.form.get('is_active') == 'on'
        member.is_admin = request.form.get('is_admin') == 'on'
        db.session.commit()
        flash(f'Member {member.full_name} updated.', 'success')
        return redirect(url_for('admin.manage_members'))

    return render_template('admin/edit_member.html', member=member)


# ── Manage Tee Times ───────────────────────────────────────────────────────────

@admin_bp.route('/tee-times', methods=['GET', 'POST'])
def manage_tee_times():
    """View and create general play tee times."""
    if request.method == 'POST':
        action = request.form.get('action', 'create')

        if action == 'generate':
            # Generate seasonal tee times for the given date
            gen_date_str = request.form.get('generate_date')
            if gen_date_str:
                gen_date = date.fromisoformat(gen_date_str)
                slots = generate_tee_time_slots(gen_date)
                created: int = 0
                for slot in slots:
                    existing = TeeTime.query.filter_by(
                        date=gen_date, time=slot
                    ).first()
                    if not existing:
                        db.session.add(TeeTime(
                            date=gen_date, time=slot,
                            max_players=4, is_available=True
                        ))
                        created += 1
                db.session.commit()
                flash(f'{created} tee times generated for {gen_date.strftime("%d/%m/%Y")}.', 'success')
            return redirect(url_for('admin.manage_tee_times', date=gen_date_str))

        else:
            # Create a single custom tee time
            tee_date = request.form.get('date')
            tee_time = request.form.get('time')
            max_players = request.form.get('max_players', 4, type=int)

            new_tee_time = TeeTime(
                date=tee_date,
                time=tee_time,
                max_players=max_players,
            )
            db.session.add(new_tee_time)
            db.session.commit()
            flash('Tee time created.', 'success')
            return redirect(url_for('admin.manage_tee_times'))

    selected_date = request.args.get('date', date.today().isoformat())
    tee_times = TeeTime.query.filter(
        TeeTime.date == selected_date
    ).order_by(TeeTime.time).all()

    return render_template(
        'admin/tee_times.html',
        tee_times=tee_times,
        selected_date=selected_date
    )


@admin_bp.route('/tee-times/<int:tt_id>/edit', methods=['GET', 'POST'])
def edit_tee_time(tt_id):
    """Edit a tee time and its bookings."""
    tee_time = TeeTime.query.get_or_404(tt_id)

    if request.method == 'POST':
        action = request.form.get('action', 'update')

        if action == 'remove_booking':
            booking_id = request.form.get('booking_id', type=int)
            booking = GeneralBooking.query.get_or_404(booking_id)
            booker = ''
            if booking.member:
                booker = booking.member.full_name
            elif booking.visitor:
                booker = f'{booking.visitor.full_name} (Visitor)'
            db.session.delete(booking)
            db.session.commit()
            flash(f'Booking by {booker} removed.', 'success')
            return redirect(url_for('admin.edit_tee_time', tt_id=tt_id))

        elif action == 'delete_tee_time':
            tt_label = f'{tee_time.date.strftime("%d/%m/%Y")} {tee_time.time.strftime("%H:%M")}'
            db.session.delete(tee_time)
            db.session.commit()
            flash(f'Tee time {tt_label} deleted.', 'success')
            return redirect(url_for('admin.manage_tee_times'))

        else:
            # Default: update tee time settings
            tee_time.is_available = request.form.get('is_available') == 'on'
            tee_time.max_players = request.form.get('max_players', 4, type=int)
            db.session.commit()
            flash('Tee time updated.', 'success')
            return redirect(url_for('admin.manage_tee_times'))

    bookings = GeneralBooking.query.filter_by(tee_time_id=tt_id).all()
    return render_template(
        'admin/edit_tee_time.html', tee_time=tee_time, bookings=bookings
    )


# ── Manage Competitions ────────────────────────────────────────────────────────

@admin_bp.route('/competitions', methods=['GET', 'POST'])
def manage_competitions():
    """View and create competitions."""
    if request.method == 'POST':
        action = request.form.get('action', 'create')

        if action == 'delete_competition':
            comp_id = request.form.get('comp_id', type=int)
            comp = Competition.query.get_or_404(comp_id)
            comp_name = comp.name
            db.session.delete(comp)
            db.session.commit()
            flash(f'Competition "{comp_name}" deleted.', 'success')
            return redirect(url_for('admin.manage_competitions'))

        # Default: create competition
        competition = Competition(
            name=request.form.get('name'),
            date=date.fromisoformat(request.form.get('date')),
            format=request.form.get('format'),
            description=request.form.get('description', ''),
        )
        db.session.add(competition)
        db.session.commit()
        flash(f'Competition "{competition.name}" created.', 'success')
        return redirect(url_for('admin.manage_competitions'))

    competitions = Competition.query.order_by(Competition.date.desc()).all()
    return render_template(
        'admin/competitions.html', competitions=competitions
    )


@admin_bp.route('/competitions/<int:comp_id>/tee-times', methods=['GET', 'POST'])
def manage_comp_tee_times(comp_id):
    """Manage competition tee times."""
    competition = Competition.query.get_or_404(comp_id)

    if request.method == 'POST':
        action = request.form.get('action', 'add')

        if action == 'generate':
            from ..services.tee_time_utils import generate_comp_tee_time_slots
            slots = generate_comp_tee_time_slots(competition.date)
            added = 0
            for slot in slots:
                exists = CompetitionTeeTime.query.filter_by(
                    competition_id=comp_id, time=slot
                ).first()
                if not exists:
                    db.session.add(CompetitionTeeTime(
                        competition_id=comp_id, time=slot, max_players=3
                    ))
                    added += 1
            db.session.commit()
            flash(f'{added} competition tee times generated.', 'success')
            return redirect(url_for('admin.manage_comp_tee_times', comp_id=comp_id))

        elif action == 'remove_booking':
            booking_id = request.form.get('booking_id', type=int)
            booking = CompetitionBooking.query.get_or_404(booking_id)
            member_name = booking.member.full_name if booking.member else 'Unknown'
            db.session.delete(booking)
            db.session.commit()
            flash(f'Booking by {member_name} removed.', 'success')
            return redirect(url_for('admin.manage_comp_tee_times', comp_id=comp_id))

        elif action == 'delete_comp_tee_time':
            ctt_id = request.form.get('ctt_id', type=int)
            ctt = CompetitionTeeTime.query.get_or_404(ctt_id)
            db.session.delete(ctt)
            db.session.commit()
            flash('Competition tee time deleted.', 'success')
            return redirect(url_for('admin.manage_comp_tee_times', comp_id=comp_id))

        else:
            # Default: add a single tee time
            from datetime import time as dt_time
            time_str = request.form.get('time')
            parts = time_str.split(':')
            tt_time = dt_time(int(parts[0]), int(parts[1]))

            # If after 11:50, also remove matching general play tee time
            if (tt_time.hour, tt_time.minute) > (11, 50):
                gp = TeeTime.query.filter_by(
                    date=competition.date, time=tt_time
                ).first()
                if gp:
                    db.session.delete(gp)

            comp_tt = CompetitionTeeTime(
                competition_id=comp_id,
                time=tt_time,
                max_players=request.form.get('max_players', 3, type=int),
            )
            db.session.add(comp_tt)
            db.session.commit()
            flash('Competition tee time added.', 'success')
            return redirect(url_for('admin.manage_comp_tee_times', comp_id=comp_id))

    comp_tee_times = CompetitionTeeTime.query.filter_by(
        competition_id=comp_id
    ).order_by(CompetitionTeeTime.time).all()

    return render_template(
        'admin/comp_tee_times.html',
        competition=competition,
        comp_tee_times=comp_tee_times
    )


# ── Manage Range ───────────────────────────────────────────────────────────────

@admin_bp.route('/range', methods=['GET', 'POST'])
def manage_range():
    """View and create range bay time slots."""
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'generate':
            from ..services.tee_time_utils import generate_range_bay_slots
            gen_date_str = request.form.get('generate_date')
            if gen_date_str:
                gen_date = date.fromisoformat(gen_date_str)
                slots = generate_range_bay_slots(gen_date)
                created: int = 0
                for slot in slots:
                    for bay_number in range(1, 7): # Bays 1 to 6
                        existing = RangeTime.query.filter_by(
                            date=gen_date, time=slot, bay_number=bay_number
                        ).first()
                        if not existing:
                            db.session.add(RangeTime(
                                date=gen_date, time=slot, bay_number=bay_number,
                                is_available=True
                            ))
                            created += 1
                db.session.commit()
                flash(f'{created} range bay times generated for {gen_date.strftime("%d/%m/%Y")}.', 'success')
            return redirect(url_for('admin.manage_range', date=gen_date_str))
            
        else:
            range_time = RangeTime(
                date=request.form.get('date'),
                time=request.form.get('time'),
                bay_number=request.form.get('bay_number', type=int),
            )
            db.session.add(range_time)
            db.session.commit()
            flash('Range time created.', 'success')
            return redirect(url_for('admin.manage_range'))

    selected_date = request.args.get('date', date.today().isoformat())
    range_times = RangeTime.query.filter(
        RangeTime.date == selected_date
    ).order_by(RangeTime.bay_number, RangeTime.time).all()

    return render_template(
        'admin/range.html',
        range_times=range_times,
        selected_date=selected_date
    )


# ── Manage Coaching ────────────────────────────────────────────────────────────

@admin_bp.route('/coaches', methods=['GET', 'POST'])
def manage_coaches():
    """View and create coaches."""
    if request.method == 'POST':
        coach = Coach(
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            bio=request.form.get('bio', ''),
            speciality=request.form.get('speciality', ''),
        )
        db.session.add(coach)
        db.session.commit()
        flash(f'Coach {coach.full_name} created.', 'success')
        return redirect(url_for('admin.manage_coaches'))

    coaches = Coach.query.order_by(Coach.last_name).all()
    return render_template('admin/coaches.html', coaches=coaches)


@admin_bp.route('/coaching-times', methods=['GET', 'POST'])
def manage_coaching_times():
    """View and create coaching time slots for a specific coach."""
    coach_id = request.args.get('coach_id', type=int)
    coach = Coach.query.get_or_404(coach_id) if coach_id else None

    if not coach:
        flash('Please select a coach first.', 'warning')
        return redirect(url_for('admin.manage_coaches'))

    if request.method == 'POST':
        action = request.form.get('action', 'create_slot')

        if action == 'delete_slot':
            ct_id = request.form.get('coaching_time_id', type=int)
            ct = CoachingTime.query.get_or_404(ct_id)
            selected = ct.date.isoformat()
            db.session.delete(ct)
            db.session.commit()
            flash('Coaching time slot removed.', 'success')
            return redirect(url_for('admin.manage_coaching_times', coach_id=coach.id, date=selected))

        if action == 'cancel_booking':
            ct_id = request.form.get('coaching_time_id', type=int)
            ct = CoachingTime.query.get_or_404(ct_id)
            selected = ct.date.isoformat()
            if ct.booking:
                db.session.delete(ct.booking)
                db.session.commit()
                flash('Coaching booking cancelled.', 'success')
            else:
                flash('No booking found for this slot.', 'warning')
            return redirect(url_for('admin.manage_coaching_times', coach_id=coach.id, date=selected))

        # Default: create_slot
        slot_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        slot_time = datetime.strptime(request.form['time'], '%H:%M').time()
        coaching_time = CoachingTime(
            coach_id=coach.id,
            date=slot_date,
            time=slot_time,
            duration_mins=request.form.get('duration_mins', 60, type=int),
        )
        db.session.add(coaching_time)
        db.session.commit()
        flash('Coaching time created.', 'success')
        return redirect(url_for('admin.manage_coaching_times', coach_id=coach.id, date=slot_date.isoformat()))

    selected_date = request.args.get('date', date.today().isoformat())
    coaching_times = CoachingTime.query.filter(
        CoachingTime.coach_id == coach.id,
        CoachingTime.date == selected_date
    ).order_by(CoachingTime.time).all()

    return render_template(
        'admin/coaching_times.html',
        coach=coach,
        coaching_times=coaching_times,
        selected_date=selected_date
    )
