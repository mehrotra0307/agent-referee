from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class FriendlySpanExporter(SpanExporter):
    """Prints one readable line per span instead of raw OTel JSON.

    Built for a first-timer's terminal, not a machine — the console exporter
    is meant to teach, so it needs to be legible without knowing what a
    trace_id or resource_schema_url is.
    """

    def export(self, spans):
        for span in spans:
            duration_ms = (span.end_time - span.start_time) / 1_000_000
            attrs = dict(span.attributes) if span.attributes else {}
            line = f"  · {span.name} ({duration_ms:.1f}ms)"
            if attrs:
                attr_str = " ".join(f"{k}={v}" for k, v in attrs.items())
                line += f" — {attr_str}"
            print(line)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
