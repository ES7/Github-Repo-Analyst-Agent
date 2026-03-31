import sys
import os
import streamlit as st
from core import run_agent
from save_report import save_report

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="GitHub Repo Analyst",
    page_icon="🔍",
    layout="wide",
)

# ─────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────

st.markdown("""
<style>
    .step-card {
        background: #f8f9fa;
        border-left: 3px solid #0066cc;
        padding: 0.5rem 1rem;
        margin: 0.4rem 0;
        border-radius: 0 6px 6px 0;
        font-family: monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────

st.title("🔍 GitHub Repo Analyst Agent")
st.markdown(
    "Paste any public GitHub repo URL. "
    "The agent will read the code, analyze the structure, and generate a full report."
)
st.divider()

# ─────────────────────────────────────────────
# Input
# ─────────────────────────────────────────────

col1, col2 = st.columns([3, 1])

with col1:
    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/tiangolo/fastapi",
        label_visibility="collapsed",
    )

with col2:
    analyze_btn = st.button("Analyze Repo", type="primary", use_container_width=True)

st.caption("Try: `tiangolo/fastapi` · `pallets/flask` · `streamlit/streamlit` · your own repo")

# ─────────────────────────────────────────────
# Run agent
# ─────────────────────────────────────────────

if analyze_btn and repo_url:

    if not repo_url.startswith("https://"):
        repo_url = f"https://github.com/{repo_url}"

    st.divider()

    left, right = st.columns([1, 2])

    with left:
        st.subheader("Agent thinking")
        steps_container = st.container()

    with right:
        st.subheader("Analysis report")
        report_placeholder = st.empty()

    step_logs = []

    def on_step(step_info: dict):
        step_logs.append(step_info)
        with steps_container:
            if step_info["type"] == "tool_call":
                st.markdown(
                    f'<div class="step-card">'
                    f'<b>Step {step_info["step"]}</b> → {step_info["tool"]}<br>'
                    f'<span style="color:#666">{step_info.get("args", {})}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            elif step_info["type"] == "parse_error":
                st.warning(f"Step {step_info['step']}: parse error, retrying...")

    with st.spinner(f"Analyzing `{repo_url}`..."):
        try:
            result = run_agent(repo_url, on_step=on_step)
        except EnvironmentError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.stop()

    if result["success"]:
        with right:
            report_placeholder.empty()
            st.markdown(result["report"])
            st.divider()

            saved_path = save_report(repo_url, result["report"])
            with open(saved_path, "rb") as f:
                st.download_button(
                    label="Download report (.md)",
                    data=f,
                    file_name=os.path.basename(saved_path),
                    mime="text/markdown",
                )
            st.caption(f"Also saved locally: `{saved_path}`")

        with left:
            st.success(f"Done in {len(result['steps'])} steps")
    else:
        st.error(result.get("error", "Agent failed."))

elif analyze_btn and not repo_url:
    st.warning("Please enter a GitHub repo URL first.")

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────

st.divider()
st.caption("Built by Ebad Sayed · GitHub Repo Analyst Agent · Powered by Gemini Flash + PyGithub")