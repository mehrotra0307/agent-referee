import textwrap

import click
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

_WRAP_WIDTH = 78


class FriendlySpanExporter(SpanExporter):
    """Prints one readable block per span instead of raw OTel JSON.

    Built for a first-timer's terminal, not a machine — the console exporter
    is meant to teach, so it needs to be legible without knowing what a
    trace_id or resource_schema_url is. Each attribute gets its own
    indented, wrapped line rather than being crammed onto the span's line,
    since some attribute values (a guardrail's block reason, in
    particular) are full sentences, not short codes.
    """

    def export(self, spans):
        for span in spans:
            duration_ms = (span.end_time - span.start_time) / 1_000_000
            attrs = dict(span.attributes) if span.attributes else {}
            print(click.style(f"  · {span.name}", bold=True) + click.style(f"  ({duration_ms:.1f}ms)", dim=True))
            for key, value in attrs.items():
                wrapped = textwrap.wrap(f"{key} = {value}", width=_WRAP_WIDTH) or [f"{key} = {value}"]
                for i, line in enumerate(wrapped):
                    prefix = "      " if i == 0 else "        "
                    print(click.style(prefix + line, dim=True))
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
