from referee.observe.tracing import get_tracer, reset_tracer


def setup_function():
    reset_tracer()


def test_friendly_exporter_prints_one_line_per_span(capsys):
    tracer = get_tracer({"observe": {"exporter": "console"}})
    with tracer.start_as_current_span("outer") as span:
        span.set_attribute("foo", "bar")

    output = capsys.readouterr().out
    assert "outer" in output
    assert "foo=bar" in output
    assert '"trace_id"' not in output, "should not fall back to raw OTel JSON output"
