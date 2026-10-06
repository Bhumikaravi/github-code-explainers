from __future__ import annotations

import os
import requests
import streamlit as st

# Backend configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="GitHub Repository Code Explainer",
    page_icon="💻",
    layout="centered",
)

# Custom minimal styling
st.markdown(
    """
    <style>
    .main-header {
        text-align: center;
        padding-bottom: 1rem;
    }
    .metric-badge {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 8px 14px;
        display: inline-block;
        margin-right: 8px;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💻 GitHub Repository Code Explainer")
st.write(
    "Enter a public GitHub repository URL and get a simple AI-generated explanation of its codebase."
)

# Check backend health and local LLM status
backend_online = False
ollama_ready = False
health_message = ""
active_model_name = "local LLM"

try:
    health_resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if health_resp.status_code == 200:
        health_data = health_resp.json()
        if isinstance(health_data, dict):
            backend_online = True
            ollama_ready = bool(health_data.get("ollama_ready", False))
            health_message = str(health_data.get("message", ""))
            active_model_name = str(health_data.get("model", "qwen2.5-coder:1.5b"))
except Exception:
    backend_online = False

# Status banner
if not backend_online:
    st.warning(
        "⚠️ **FastAPI Backend is not running.**\n\n"
        "Start the backend in PowerShell with:\n"
        "```powershell\n"
        ".\\venv\\Scripts\\Activate.ps1\n"
        "uvicorn backend.main:app --reload\n"
        "```"
    )
elif not ollama_ready:
    st.warning(f"⚠️ **Backend is online, but Local LLM is not ready:**\n\n{health_message}")
else:
    st.success(f"✅ **System Ready:** FastAPI Backend and Local LLM ({active_model_name}) are connected.")

# Input Form
with st.form("repo_form"):
    repo_url = st.text_input(
        "Enter GitHub Repository URL",
        placeholder="https://github.com/Bhumikaravi/github-code-explainers",
        help="Paste any public GitHub repository link (e.g. https://github.com/owner/repository)",
    )
    submit_button = st.form_submit_button("Explain Repository", type="primary", use_container_width=True)

# Processing when button is clicked
if submit_button:
    clean_url = repo_url.strip()

    # 1. Frontend validation
    if not clean_url:
        st.error("Please enter a GitHub repository URL.")
        st.stop()

    if not (clean_url.startswith("https://github.com/") or clean_url.startswith("http://github.com/")):
        st.error("Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repository).")
        st.stop()

    # 2. Check backend connectivity
    if not backend_online:
        st.error("Cannot connect to the FastAPI backend. Please start the backend first.")
        st.stop()

    # 3. Call FastAPI backend with visual progress
    progress_placeholder = st.empty()
    status_box = st.status("Analyzing repository...", expanded=True)

    with status_box:
        st.write("🔗 Cloning repository...")
        st.write("📂 Analyzing source files...")
        st.write("🧠 Preparing code for the local LLM...")
        st.write("✨ Generating explanation...")

        try:
            response = requests.post(
                f"{BACKEND_URL}/explain",
                json={"repo_url": clean_url},
                timeout=300,
            )
        except requests.exceptions.ConnectionError:
            status_box.update(label="Connection Error", state="error", expanded=False)
            st.error(
                "Could not connect to FastAPI backend at http://127.0.0.1:8000. "
                "Ensure `uvicorn backend.main:app --reload` is running."
            )
            st.stop()
        except requests.exceptions.Timeout:
            status_box.update(label="Timeout Error", state="error", expanded=False)
            st.error(
                "The local LLM took too long to respond. "
                "Try analyzing a smaller repository or using a smaller model."
            )
            st.stop()
        except Exception as exc:
            status_box.update(label="Unexpected Error", state="error", expanded=False)
            st.error(f"Failed to communicate with backend: {str(exc)}")
            st.stop()

        # 4. Safe response validation (Never assume dictionary/string blindly)
        if response.status_code != 200:
            status_box.update(label="Backend Error", state="error", expanded=False)
            st.error(f"Backend returned error code {response.status_code}: {response.text}")
            st.stop()

        try:
            result = response.json()
        except Exception:
            status_box.update(label="Parsing Error", state="error", expanded=False)
            st.error("Backend did not return valid JSON. Please check backend logs.")
            st.stop()

        if not isinstance(result, dict):
            status_box.update(label="Format Error", state="error", expanded=False)
            st.error(f"Unexpected response format: expected JSON object, got {type(result).__name__}.")
            st.stop()

        # Check success field
        is_success = bool(result.get("success", False))
        if not is_success:
            err_msg = result.get("error", "Unknown error occurred.")
            status_box.update(label="Explanation Failed", state="error", expanded=False)
            st.error(str(err_msg))
            st.stop()

        status_box.update(label="Analysis complete!", state="complete", expanded=False)

    # 5. Extract results safely
    explanation = result.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        st.error("The local LLM returned an empty explanation. Please try again.")
        st.stop()

    files_analyzed = result.get("files_analyzed", 0)
    total_files = result.get("total_files", 0)
    languages = result.get("languages", [])
    file_list = result.get("files", [])

    # Store in session state for persistence
    st.session_state["result_data"] = {
        "explanation": explanation,
        "files_analyzed": files_analyzed,
        "total_files": total_files,
        "languages": languages,
        "file_list": file_list,
        "repo_url": clean_url,
    }

# Display results if available in session state
if "result_data" in st.session_state:
    data = st.session_state["result_data"]

    st.markdown("---")
    st.subheader("📊 Analysis Summary")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Files Analyzed", f"{data['files_analyzed']} of {data['total_files']}")
    with col2:
        lang_str = ", ".join(data["languages"]) if data["languages"] else "None detected"
        st.metric("Languages Detected", lang_str)

    st.markdown("---")
    st.subheader("📘 Project Explanation")
    st.markdown(data["explanation"])

    # File tree expander
    if data["file_list"]:
        with st.expander(f"📁 Repository Files List ({len(data['file_list'])})"):
            st.code("\n".join(data["file_list"]), language="text")

    # Download button
    st.download_button(
        label="⬇️ Download Explanation as Markdown",
        data=data["explanation"],
        file_name="repository_explanation.md",
        mime="text/markdown",
        use_container_width=True,
    )

    if st.button("🔄 Clear Result", use_container_width=True):
        del st.session_state["result_data"]
        st.rerun()

st.markdown("---")
st.caption("Powered by GitPython • FastAPI • Streamlit • Ollama (qwen2.5:3b)")
