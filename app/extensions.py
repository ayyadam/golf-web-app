from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from prometheus_flask_exporter import PrometheusMetrics

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Prometheus metrics exporter — instantiated here so the harness's
# observability stack (testing-system/observability/) has a stable target
# at /metrics. Bound to the app in create_app(); see app/__init__.py.
metrics = PrometheusMetrics.for_app_factory()
