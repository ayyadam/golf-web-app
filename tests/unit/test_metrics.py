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
