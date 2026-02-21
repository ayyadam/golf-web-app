import os
from flask import Flask
from .extensions import db, login_manager, csrf
from .config import config_by_name


def create_app(config_name=None):
    """Application factory for the Flask app."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from .routes.public import public_bp
    from .routes.auth import auth_bp
    from .routes.member import member_bp
    from .routes.admin import admin_bp
    from .routes.visitor import visitor_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(member_bp, url_prefix='/member')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(visitor_bp, url_prefix='/visitor')

    # Create database tables (for development; migrations used in production)
    with app.app_context():
        db.create_all()

    return app
