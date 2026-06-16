import os
from apiflask import APIFlask
from .extensions import db, login_manager, csrf, metrics
from .config import config_by_name


def create_app(config_name=None):
    """Application factory for the Flask app.

    Uses APIFlask (a Flask subclass) so the JSON API blueprint can register
    its OpenAPI spec at /api/v1/openapi.json and Swagger UI at /api/v1/docs.
    Existing HTML routes are unaffected — APIFlask is API-compatible with
    plain Flask.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = APIFlask(
        __name__,
        title='Adam\'s Golf Club API',
        version='1.0.0',
        spec_path='/api/v1/openapi.json',
        docs_path='/api/v1/docs',
    )
    app.config.from_object(config_by_name[config_name])

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    metrics.init_app(app)
    metrics.info('flask_app_info', 'Application info', version='1.0.0')

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from .routes.public import public_bp
    from .routes.auth import auth_bp
    from .routes.member import member_bp
    from .routes.admin import admin_bp
    from .routes.visitor import visitor_bp
    from .api import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(member_bp, url_prefix='/member')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(visitor_bp, url_prefix='/visitor')
    app.register_blueprint(api_bp)  # url_prefix declared on the blueprint itself

    # API uses bearer tokens, not session cookies — exempt from CSRF
    csrf.exempt(api_bp)

    # APIFlask iterates over all blueprints when generating the OpenAPI spec
    # and reads .enable_openapi on each. Legacy Flask Blueprints don't have
    # that attribute, so we tag them as out-of-spec here.
    for bp_name, bp in app.blueprints.items():
        if not hasattr(bp, 'enable_openapi'):
            bp.enable_openapi = False

    # APIFlask supports a single spec_processor callback (registering a second
    # overwrites the first), so this one finalises the generated spec in two
    # passes: it hides operational endpoints, then declares OpenAPI links that
    # describe the referential relationships between operations.
    @app.spec_processor
    def finalise_openapi_spec(spec):
        # 1. /metrics is exposed by prometheus-flask-exporter for the assurance
        # harness's observability stack (testing-system/observability/). It is
        # registered directly on the app (not via a blueprint), so the
        # blueprint-level toggle above doesn't reach it; APIFlask therefore
        # discovers it and emits an OpenAPI entry declaring application/json,
        # while the endpoint actually serves text/plain (prometheus exposition
        # format). Remove it so the published v1 spec accurately describes ONLY
        # the v1 JSON API, not operational endpoints.
        spec.setdefault('paths', {}).pop('/metrics', None)

        # 2. OpenAPI links: declare that an id from the GET /tee-times list feeds
        # the operations parameterised by {tee_time_id}. This makes the
        # referential contract explicit in the spec itself (rather than only
        # known to clients), and lets spec-driven tools — e.g. Schemathesis'
        # stateful phase — chain list -> read/book without out-of-band knowledge
        # of how to obtain a valid id. operationRef (a JSON pointer to the
        # operation) is used because APIFlask does not emit operationIds.
        list_op = spec['paths'].get('/api/v1/tee-times', {}).get('get')
        if list_op is not None:
            tee_time_id = '$response.body#/0/id'  # first id from the returned list
            list_op.setdefault('responses', {}).setdefault('200', {})['links'] = {
                'GetTeeTimeById': {
                    'operationRef': '#/paths/~1api~1v1~1tee-times~1{tee_time_id}/get',
                    'parameters': {'tee_time_id': tee_time_id},
                    'description': 'Read a single tee time using an id from this list.',
                },
                'BookTeeTime': {
                    'operationRef': (
                        '#/paths/~1api~1v1~1tee-times~1{tee_time_id}~1bookings/post'
                    ),
                    'parameters': {'tee_time_id': tee_time_id},
                    'description': 'Book a tee time using an id from this list.',
                },
            }
        return spec

    # Create database tables (for development; migrations used in production)
    with app.app_context():
        db.create_all()

    @app.template_filter('format_handicap')
    def format_handicap(value):
        if value is None:
            return value
        try:
            val = float(str(value))
            if val < 0:
                return f"+{abs(val):.1f}"
            return f"{val:.1f}"
        except (ValueError, TypeError):
            return value

    return app
