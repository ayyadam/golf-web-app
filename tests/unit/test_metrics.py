"""Unit tests for the Prometheus metrics endpoint.

The /metrics endpoint is the integration surface the assurance harness's
observability stack (testing-system/observability/) scrapes. Verifying it
emits the expected shape (200 OK, prometheus text format, the standard
flask_http_request_* counters) is part of keeping that integration stable.
"""


def test_metrics_endpoint_returns_200(client):
    resp = client.get('/metrics')
    assert resp.status_code == 200


def test_metrics_endpoint_emits_prometheus_text_format(client):
    resp = client.get('/metrics')
    content_type = resp.headers.get('Content-Type', '')
    assert content_type.startswith('text/plain'), (
        f"expected prometheus text format, got Content-Type={content_type!r}"
    )


def test_metrics_endpoint_exposes_request_counter(client):
    # Generate a request to ensure the counter has at least one observed value.
    client.get('/')
    resp = client.get('/metrics')
    body = resp.get_data(as_text=True)
    # The Flask exporter emits flask_http_request_duration_seconds_count by default.
    assert 'flask_http_request_duration_seconds_count' in body
    # And the app-info gauge we registered in create_app().
    assert 'flask_app_info' in body


def test_metrics_endpoint_not_in_openapi_spec(client):
    """The /metrics endpoint is operational, not part of the v1 API contract.

    APIFlask auto-discovers app-level routes when building the OpenAPI spec
    and (before the spec_processor fix) emitted /metrics with the default
    application/json content type. The actual endpoint serves text/plain,
    so the spec was lying — caught by the testing-system contract gate.
    The spec_processor in create_app strips /metrics from the published
    spec so the v1 contract accurately describes only the v1 JSON API.
    """
    resp = client.get('/api/v1/openapi.json')
    assert resp.status_code == 200
    spec = resp.get_json()
    assert '/metrics' not in spec.get('paths', {}), (
        "/metrics leaked into the v1 OpenAPI spec — see F-010 / "
        "hide_operational_endpoints in app/__init__.py"
    )
