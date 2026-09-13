import re

from referee.observe.tracing import get_tracer, reset_tracer

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def setup_function():
    reset_tracer()


def test_friendly_exporter_prints_one_line_per_span(capsys):
    tracer = get_tracer({"observe": {"exporter": "console"}})
    with tracer.start_as_current_span("outer") as span:
        span.set_attribute("foo", "bar")

    output = capsys.readouterr().out
    assert "outer" in output
    assert "foo = bar" in output
    assert '"trace_id"' not in output, "should not fall back to raw OTel JSON output"


def test_long_attribute_value_wraps_onto_its_own_lines(capsys):
    tracer = get_tracer({"observe": {"exporter": "console"}})
    long_value = "word " * 40
    with tracer.start_as_current_span("outer") as span:
        span.set_attribute("reason", long_value.strip())

    output = capsys.readouterr().out
    lines = [_ANSI.sub("", line) for line in output.splitlines() if line.strip()]
    assert all(len(line) <= 90 for line in lines), "no single printed line should run unreasonably long"
