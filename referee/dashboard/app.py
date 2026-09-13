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

st.set_page_config(page_title="Agent Referee Dashboard", page_icon="🧑‍⚖️", layout="wide")

# A little visual identity, since this is the one place in the project with
# a real screen to work with instead of a terminal: an accent color, a
# rounded card feel for metrics, and colored left-border panels so a PASS
# and a FAIL read as different at a glance, not just different words.
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetric"] {
        background: rgba(127, 127, 127, 0.06);
        border: 1px solid rgba(127, 127, 127, 0.15);
        border-radius: 10px;
        padding: 14px 16px 10px;
    }
    .ref-panel {
        border-radius: 10px;
        padding: 14px 18px;
        margin: 6px 0 18px;
        border-left: 5px solid;
    }
    .ref-panel-ok { background: rgba(46, 160, 67, 0.10); border-color: #2ea043; }
    .ref-panel-bad { background: rgba(219, 68, 55, 0.10); border-color: #db4437; }
    .ref-panel-info { background: rgba(88, 166, 255, 0.10); border-color: #58a6ff; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _panel(kind: str, text: str) -> None:
    st.markdown(f'<div class="ref-panel ref-panel-{kind}">{text}</div>', unsafe_allow_html=True)


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


st.title("🧑‍⚖️ Agent Referee Dashboard")
st.caption("Local only — reads files from ./reports and ./referee.yaml. Nothing here is hosted by us.")

eval_report = _latest_report("eval_run_*.json")
guardrail_report = _latest_report("guardrails_run_*.json")

if eval_report is None and guardrail_report is None:
    _panel(
        "info",
        "No reports found yet. Run <code>referee eval run</code> or "
        "<code>referee guardrails test</code> in this directory first, then reload this page.",
    )

st.header("📋 Latest evaluation")
if eval_report is None:
    _panel("info", "No evaluation report yet — run <code>referee eval run</code>.")
else:
    report, filename = eval_report
    st.caption(f"From {filename}")

    all_passed = report["passed"] == report["total_tests"]
    if report["critical_failures"] > 0:
        _panel("bad", f"<b>{report['critical_failures']} critical failure(s)</b> — this would block a CI pipeline.")
    elif all_passed:
        _panel("ok", "<b>All test cases passed.</b>")
    else:
        _panel("bad", "<b>Some test cases failed</b> (none critical).")

    col1, col2, col3 = st.columns(3)
    col1.metric("Pass rate", f"{report['pass_rate'] * 100:.0f}%")
    col2.metric("Passed", f"{report['passed']}/{report['total_tests']}")
    col3.metric("Critical failures", report["critical_failures"])
    st.progress(report["pass_rate"])

    st.dataframe(
        [
            {
                "": "✅" if r["passed"] else "❌",
                "id": r["id"],
                "category": r["category"],
                "severity": r["severity"],
                "reason": r["reason"],
            }
            for r in report["results"]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.header("🛡️ Latest guardrail test")
if guardrail_report is None:
    _panel("info", "No guardrail test report yet — run <code>referee guardrails test</code>.")
else:
    report, filename = guardrail_report
    st.caption(f"From {filename}")

    all_blocked = report["blocked"] == report["total_attacks"]
    if all_blocked:
        _panel("ok", "<b>Every attack was blocked.</b>")
    else:
        missed = report["total_attacks"] - report["blocked"]
        _panel("bad", f"<b>{missed} attack(s) got through</b> — worth a look before you rely on this.")

    col1, col2 = st.columns(2)
    col1.metric("Attacks blocked", f"{report['blocked']}/{report['total_attacks']}")
    col2.metric("Status", "All blocked" if all_blocked else "Some got through")
    if report["total_attacks"]:
        st.progress(report["blocked"] / report["total_attacks"])

    st.dataframe(
        [
            {
                "": "✅" if r["blocked"] else "❌",
                "id": r["id"],
                "category": r["category"],
                "attack_description": r["attack_description"],
            }
            for r in report["results"]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.header("📡 Observability")
config = _load_referee_config()
observe_config = config.get("observe", {})

if observe_config.get("exporter") == "otlp":
    endpoint = observe_config.get("otlp_endpoint", "")
    parsed = urlparse(endpoint)
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else endpoint
    _panel(
        "info",
        "Traces are exporting to an external OTLP backend, not printed to console. "
        f"Agent Referee doesn't rebuild a trace viewer — open your backend directly: "
        f'<a href="{base_url}">{base_url}</a>',
    )
else:
    _panel(
        "info",
        "Traces are currently printing to the console (<code>observe.exporter: console</code> "
        "in referee.yaml). To see a persistent trace UI here instead, point "
        "<code>observe.exporter</code> at an OTLP-compatible backend — for example Langfuse "
        "Cloud's free tier — and this section will link out to it.",
    )
