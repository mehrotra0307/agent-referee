import pytest

from referee.observe.tracing import get_tracer, reset_tracer


def setup_function():
    reset_tracer()


def test_console_exporter_needs_no_config():
    tracer = get_tracer({"observe": {"exporter": "console"}})
    with tracer.start_as_current_span("test_span") as span:
        span.set_attribute("foo", "bar")


def test_default_exporter_is_console_when_omitted():
    tracer = get_tracer({})
    assert tracer is not None


def test_otlp_without_endpoint_raises_helpful_error():
    reset_tracer()
    with pytest.raises(ValueError, match="otlp_endpoint"):
        get_tracer({"observe": {"exporter": "otlp"}})


def test_unknown_exporter_raises():
    reset_tracer()
    with pytest.raises(ValueError, match="Unknown observe.exporter"):
        get_tracer({"observe": {"exporter": "not_a_real_exporter"}})
