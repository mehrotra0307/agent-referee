from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from referee.observe.console_summary import FriendlySpanExporter

_tracer = None
_configured_exporter = None


def _build_span_processor(observe_config: dict[str, Any]):
    """Build the OTel span processor for observe_config["exporter"]
    ('console', the zero-config default, or 'otlp')."""
    exporter_name = observe_config.get("exporter", "console")

    if exporter_name == "console":
        # Synchronous on purpose: console output has no network latency to batch
        # against, and BatchSpanProcessor's background flush thread otherwise
        # outlives short-lived scripts and warns on a closed stdout at exit.
        return SimpleSpanProcessor(FriendlySpanExporter())

    if exporter_name == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        endpoint = observe_config.get("otlp_endpoint")
        if not endpoint:
            raise ValueError(
                "observe.exporter is 'otlp' but observe.otlp_endpoint is missing from "
                "referee.yaml. Point it at any OTLP-compatible traces endpoint (e.g. a "
                "Langfuse Cloud project's /api/public/otel/v1/traces URL)."
            )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers=observe_config.get("otlp_headers", {}),
        )
        return BatchSpanProcessor(exporter)

    raise ValueError(f"Unknown observe.exporter '{exporter_name}' — expected 'console' or 'otlp'.")


def get_tracer(config: dict[str, Any], agent_name: str = "agent-referee"):
    """Get (or lazily build and cache) the process-wide tracer for config's
    observe.* section. Rebuilds only if the exporter type actually changed
    since the last call, so this is cheap to call on every request."""
    global _tracer, _configured_exporter

    observe_config = config.get("observe", {"exporter": "console"})
    exporter_name = observe_config.get("exporter", "console")

    if _tracer is not None and _configured_exporter == exporter_name:
        return _tracer

    provider = TracerProvider(resource=Resource.create({"service.name": agent_name}))
    provider.add_span_processor(_build_span_processor(observe_config))
    trace.set_tracer_provider(provider)

    _tracer = trace.get_tracer(agent_name)
    _configured_exporter = exporter_name
    return _tracer


def reset_tracer() -> None:
    """Drop the cached tracer so the next get_tracer() call rebuilds it. Mainly for tests."""
    global _tracer, _configured_exporter
    _tracer = None
    _configured_exporter = None
