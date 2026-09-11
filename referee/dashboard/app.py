"""Local Streamlit dashboard, launched by `referee dashboard`.

Reads only local files: ./reports/*.json and ./referee.yaml. Nothing here
is hosted by us, matching the local-first design principle. Run directly
with `streamlit run referee/dashboard/app.py` from a project directory
that has at least one report in ./reports.
"""

import json
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import yaml

st.set_page_config(page_title="Agent Referee Dashboard", page_icon="🧑‍⚖️")


def _latest_report(pattern: str):
    """Return (parsed_json, filename) for the most recent reports/<pattern> file, or None."""
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return None
    matches = sorted(reports_dir.glob(pattern), reverse=True)
    if not matches:
        return None
    return json.loads(matches[0].read_text()), matches[0].name


def _load_referee_config():
    """Load ./referee.yaml if present, else {} (the dashboard still works without it)."""
    config_path = Path("referee.yaml")
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text()) or {}


st.title("Agent Referee Dashboard")
st.caption("Local only — reads files from ./reports and ./referee.yaml. Nothing here is hosted by us.")

eval_report = _latest_report("eval_run_*.json")
guardrail_report = _latest_report("guardrails_run_*.json")

if eval_report is None and guardrail_report is None:
    st.info(
        "No reports found yet. Run `referee eval run` or `referee guardrails test` in this "
        "directory first, then reload this page."
    )

st.header("Latest evaluation")
if eval_report is None:
    st.write("No evaluation report yet — run `referee eval run`.")
else:
    report, filename = eval_report
    st.caption(f"From {filename}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Pass rate", f"{report['pass_rate'] * 100:.0f}%")
    col2.metric("Passed", f"{report['passed']}/{report['total_tests']}")
    col3.metric("Critical failures", report["critical_failures"])
    st.dataframe(
        [
            {
                "id": r["id"],
                "category": r["category"],
                "severity": r["severity"],
                "passed": r["passed"],
                "reason": r["reason"],
            }
            for r in report["results"]
        ],
        use_container_width=True,
    )

st.header("Latest guardrail test")
if guardrail_report is None:
    st.write("No guardrail test report yet — run `referee guardrails test`.")
else:
    report, filename = guardrail_report
    st.caption(f"From {filename}")
    col1, col2 = st.columns(2)
    col1.metric("Attacks blocked", f"{report['blocked']}/{report['total_attacks']}")
    col2.metric(
        "Status", "All blocked" if report["blocked"] == report["total_attacks"] else "Some got through"
    )
    st.dataframe(report["results"], use_container_width=True)

st.header("Observability")
config = _load_referee_config()
observe_config = config.get("observe", {})

if observe_config.get("exporter") == "otlp":
    endpoint = observe_config.get("otlp_endpoint", "")
    parsed = urlparse(endpoint)
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else endpoint
    st.write(
        "Traces are exporting to an external OTLP backend, not printed to console. "
        "Agent Referee doesn't rebuild a trace viewer — open your backend directly:"
    )
    st.markdown(f"[{base_url}]({base_url})")
else:
    st.write(
        "Traces are currently printing to the console (observe.exporter: console in "
        "referee.yaml). To see a persistent trace UI, point observe.exporter at an "
        "OTLP-compatible backend — for example Langfuse Cloud's free tier — and this "
        "page will link out to it instead."
    )
