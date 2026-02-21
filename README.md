# Adam's Golf Club 🏌️

A full-stack web application for managing a golf club — tee time bookings, competitions, coaching, Trackman range, and membership management.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python 3.12) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy + Alembic |
| Frontend | HTML/CSS/JS + Bootstrap 5 |
| Auth | Flask-Login + bcrypt |
| Tests | pytest + Playwright |
| CI/CD | GitHub Actions |
| Deploy | Docker + Docker Compose |

## Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Git

### Local Development (Docker)

```bash
# Clone and start
git clone <repo-url> && cd golf-web-app
docker compose up -d

# Seed the database
docker compose exec web python seed.py

# Visit http://localhost:5000
```

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Set environment variables (copy .env.example to .env and edit)
cp .env.example .env

# Run (requires PostgreSQL running locally)
python run.py
python seed.py  # Seed sample data
```

### Running Tests

```bash
# Start test database
docker compose -f docker-compose.test.yml up -d

# Run unit tests
pytest tests/unit/ -v --cov=app

# Run functional tests (requires Playwright)
python -m playwright install chromium
pytest tests/functional/ -v

# Stop test database
docker compose -f docker-compose.test.yml down
```

## Default Accounts (after seeding)

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Member | `jsmith` | `member123` |
| Member | `ewhite` | `member123` |

## Project Structure

```
golf-web-app/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Environment configs
│   ├── extensions.py        # Flask extensions
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Blueprint routes
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, images
├── tests/
│   ├── unit/                # pytest unit tests
│   └── functional/          # Playwright browser tests
├── .github/workflows/       # CI/CD pipeline
├── docker-compose.yml       # Dev environment
├── docker-compose.test.yml  # Test database
├── Dockerfile               # Production image
├── seed.py                  # Database seed data
└── requirements.txt         # Python dependencies
```

## CI/CD Pipeline

Push to `main` triggers: **Lint → Unit Tests → Functional Tests → Docker Build → GitHub Release → Deploy** (self-hosted runner).

Test reports are uploaded as GitHub Actions artifacts.

## License

Private — Adam's Golf Club.