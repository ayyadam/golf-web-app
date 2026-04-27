"""Seed data script — populates the database with initial data for development/demo."""
from datetime import date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    Member, Hole, Coach, TeeTime, Competition, CompetitionTeeTime,
    RangeTime
)


def seed():
    """Seed the database with sample data."""
    app = create_app()
    with app.app_context():
        print("Seeding database (clean reset)...")
        db.drop_all()
        db.create_all()

        # ── Admin user ──────────────────────────────────────────
        if not Member.query.filter_by(username='adam.nance').first():
            admin = Member(
                username='adam.nance',
                email='adam.nance@adamsgolfclub.com',
                first_name='Adam',
                last_name='Nance',
                telephone='01234567890',
                membership_type='Full Year',
                handicap=9.3,
                is_admin=True,
                is_active=True,
            )
            admin.set_password('Admin123')
            db.session.add(admin)
            print(f"  [OK] Admin user created (adam.nance / Admin123)")

        # ── Sample members ──────────────────────────────────────
        members_data = [
            ('john.smith', 'john.smith@example.com', 'John', 'Smith', '01234567890', 'Full Year', 12.3),
            ('emma.white', 'emma.white@example.com', 'Emma', 'White', '01234567890', 'Full Year', 8.7),
            ('rob.jones', 'rob.jones@example.com', 'Rob', 'Jones', '01234567890', '6 Month', 18.1),
            ('sarah.jacobs', 'sarah.jacobs@example.com', 'Sarah', 'Jacobs', '01234567890', '6 Month', 22.5),
            ('jon.nance', 'jon.nance@example.com', 'Jon', 'Nance', '01234567890', 'Full Year', 16.0),
        ]
        for uname, email, fn, ln, tel, mtype, hcp in members_data:
            if not Member.query.filter_by(username=uname).first():
                m = Member(
                    username=uname, email=email, first_name=fn, last_name=ln,
                    telephone=tel, membership_type=mtype, handicap=hcp,
                    is_active=True,
                )
                m.set_password('Password1')
                db.session.add(m)
        db.session.commit()
        print("  [OK] Sample members created")

        # ── Course holes ────────────────────────────────────────
        if not Hole.query.first():
            holes_data = [
                # (num, par, si, blues, whites, yellows, reds, name, description)
                (1, 4, 7, 385, 370, 355, 340, 'Greenside Rise', 'A sweeping dogleg left to a well-guarded green. Avoid the fairway bunkers on the right.'),
                (2, 3, 15, 165, 155, 145, 130, 'The Dell', 'A short par 3 over water. Club selection is key — the green slopes front to back.'),
                (3, 5, 3, 520, 505, 490, 470, 'Long Valley', 'The first par 5, reachable in two for big hitters. Beware the cross bunker at 230 yards.'),
                (4, 4, 11, 375, 362, 350, 330, 'Birch Avenue', 'Straightforward par 4 lined with silver birch trees. Keep it in play off the tee.'),
                (5, 4, 1, 435, 422, 410, 390, 'Heartbreak Hill', 'The number one stroke index — a long par 4 uphill to a plateau green. Tough approach.'),
                (6, 3, 17, 145, 136, 128, 115, 'Pond View', 'Short but tricky. Water right, bunkers left. The green is small and firm.'),
                (7, 4, 9, 400, 387, 375, 355, 'The Ridge', 'A tee shot over a ridge with a blind second to a tiered green. Local knowledge helps.'),
                (8, 5, 5, 545, 532, 520, 500, 'The Meadow', 'A wide-open par 5 offering birdie chances. Mind the out-of-bounds left.'),
                (9, 4, 13, 365, 352, 340, 320, 'Halfway House', 'A gentle par 4 to complete the front 9. Well-bunkered green with a false front.'),
                (10, 4, 6, 410, 397, 385, 365, 'Back Stretch', 'A strong opening to the back 9. The drive must carry the bunkers at 220 yards.'),
                (11, 3, 16, 175, 165, 155, 140, 'Hilltop', 'An elevated tee gives panoramic views. Take an extra club — the green is exposed to wind.'),
                (12, 5, 4, 535, 522, 510, 485, 'Eagle\'s Reach', 'A risk-reward par 5 with water guarding the green. Lay up or go for it?'),
                (13, 4, 2, 440, 427, 415, 395, 'The Quarry', 'Second hardest hole. A narrow fairway with quarry rough right. Accuracy over power.'),
                (14, 4, 10, 380, 367, 355, 335, 'Orchard Walk', 'An inviting par 4 through the old apple orchard. Favour the left side off the tee.'),
                (15, 3, 18, 135, 127, 120, 105, 'The Punchbowl', 'The shortest hole — a true punchbowl green. Anything on the surface feeds towards the pin.'),
                (16, 4, 8, 405, 392, 380, 360, 'Sunset Stretch', 'Play towards the setting sun. A two-tier green adds complexity to this late par 4.'),
                (17, 4, 12, 370, 357, 345, 325, 'Penultimate', 'A deceptive par 4 that plays longer than it looks. A pot bunker guards the front of the green.'),
                (18, 5, 14, 510, 495, 480, 460, 'The Finale', 'A fitting finish — a par 5 sweeping uphill to the clubhouse. Go low and finish strong.')
            ]
            for num, par, si, blues, whites, yellows, reds, name, desc in holes_data:
                hole = Hole(
                    hole_number=num, par=par, stroke_index=si,
                    yards_blues=blues, yards_whites=whites, yards_yellows=yellows, yards_reds=reds,
                    name=name, description=desc
                )
                db.session.add(hole)
            db.session.commit()
            print("  [OK] 18 holes created")

        # ── Coaches ─────────────────────────────────────────────
        if not Coach.query.first():
            coaches_data = [
                ('James', 'Murray', 'Full Swing', 'PGA Advanced Professional with 15 years teaching experience. Specialises in swing mechanics and ball flight correction.'),
                ('Claire', 'Davidson', 'Short Game', 'Renowned for her short game expertise. Has coached county-level juniors and club champions.'),
                ('Tom', 'Patel', 'Putting', 'Former touring professional turned coach. Expert in green reading and putting stroke analysis.'),
            ]
            for fn, ln, spec, bio in coaches_data:
                db.session.add(Coach(first_name=fn, last_name=ln, speciality=spec, bio=bio))
            db.session.commit()
            print("  [OK] Coaches created")

        # ── Tee times (next 7 days) ────────────────────────────
        if not TeeTime.query.first():
            from app.services.tee_time_utils import generate_tee_time_slots
            for day_offset in range(7):
                d = date.today() + timedelta(days=day_offset)
                slots = generate_tee_time_slots(d)
                for slot in slots:
                    db.session.add(TeeTime(
                        date=d, time=slot,
                        max_players=4, is_available=True
                    ))
            db.session.commit()
            print("  [OK] Tee times created (7 days, seasonal hours)")

        # ── Sample competition ──────────────────────────────────
        if not Competition.query.first():
            comp_date = date.today() + timedelta(days=14)
            comp = Competition(
                name='Monthly Stableford', date=comp_date,
                format='Stableford',
                description='Our regular monthly Stableford competition. All members welcome.'
            )
            db.session.add(comp)
            db.session.commit()
            from app.services.tee_time_utils import generate_comp_tee_time_slots
            comp_slots = generate_comp_tee_time_slots(comp_date)
            for slot in comp_slots:
                db.session.add(CompetitionTeeTime(
                    competition_id=comp.id,
                    time=slot,
                    max_players=3
                ))
            db.session.commit()
            print("  [OK] Sample competition created")

        # ── Range times (next 7 days) ──────────────────────────
        if not RangeTime.query.first():
            for day_offset in range(7):
                d = date.today() + timedelta(days=day_offset)
                for bay in range(1, 7):
                    for hour in range(7, 21):
                        for minute in [0, 30]:
                            db.session.add(RangeTime(
                                date=d, time=time(hour, minute),
                                bay_number=bay
                            ))
            db.session.commit()
            print("  [OK] Range times created (7 days, 6 bays)")

        print("Seeding complete!")


if __name__ == '__main__':
    seed()
