from __future__ import annotations

import os
import sys
import requests
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.github_processor import (
    clone_repository,
    scan_and_extract_code,
    cleanup_repository,
)
from backend.llm import generate_gemini_explanation

# Backend configuration for local mode
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="GitHub Repository Code Explainer",
    layout="centered",
)

st.markdown(
    """
    <style>
    /* Main application peach background */
    .stApp {
        background-color: #FFF3EB;
        color: #2D2320;
    }

    [data-testid="stHeader"] {
        background-color: transparent;
    }

    /* Metric cards styling */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #F5C6AA;
        border-radius: 10px;
        padding: 12px 18px;
        box-shadow: 0 1px 4px rgba(45, 35, 32, 0.05);
    }

    div[data-testid="stMetricValue"] {
        color: #C85A32;
    }

    /* Primary buttons */
    button[kind="primary"] {
        background-color: #E07A5F !important;
        border-color: #E07A5F !important;
        color: #FFFFFF !important;
        font-weight: 600;
        border-radius: 8px;
    }

    button[kind="primary"]:hover {
        background-color: #C85A32 !important;
        border-color: #C85A32 !important;
    }

    /* Secondary / standard buttons */
    button[kind="secondary"] {
        background-color: #FFE5D4 !important;
        border: 1px solid #F5C6AA !important;
        color: #2D2320 !important;
        border-radius: 8px;
    }

    button[kind="secondary"]:hover {
        background-color: #FCD6BE !important;
        border-color: #E07A5F !important;
    }

    /* Form input styling */
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF;
        color: #2D2320;
        border: 1px solid #F0C4AB;
        border-radius: 8px;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #E07A5F;
        box-shadow: 0 0 0 1px #E07A5F;
    }

    /* Expander header styling */
    .streamlit-expanderHeader {
        background-color: #FFEADB;
        border-radius: 8px;
        color: #2D2320;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("GitHub Repository Code Explainer")
st.write(
    "Enter a public GitHub repository URL and get a simple AI-generated explanation of its codebase."
)

# 1. Check for Gemini API key (for Cloud Mode on Streamlit Community Cloud)
gemini_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        val = str(st.secrets["GEMINI_API_KEY"]).strip()
        if val and not val.startswith("YOUR_") and "pinggy" not in val:
            gemini_key = val
except Exception:
    pass

if not gemini_key:
    val = os.getenv("GEMINI_API_KEY", "").strip()
    if val and not val.startswith("YOUR_") and "pinggy" not in val:
        gemini_key = val

# 2. Check Local Backend health (for Local Mode on Laptop)
backend_online = False
ollama_ready = False
health_message = ""
active_model_name = "local LLM"

if not gemini_key:
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

# Status banner (only displays if service is unavailable)
if not gemini_key and not backend_online:
    st.warning(
        "FastAPI Backend is not running.\n\n"
        "- For Local Mode (Laptop): Start backend with `uvicorn backend.main:app --reload`\n"
        "- For Cloud Mode (Streamlit Cloud): Add `GEMINI_API_KEY` in Streamlit Cloud Secrets."
    )
elif not gemini_key and not ollama_ready:
    st.warning(f"Backend is online, but Local LLM is not ready:\n\n{health_message}")

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

    # 1. Validation
    if not clean_url:
        st.error("Please enter a GitHub repository URL.")
        st.stop()

    if not (clean_url.startswith("https://github.com/") or clean_url.startswith("http://github.com/")):
        st.error("Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repository).")
        st.stop()

    # 2. Check provider readiness
    if not gemini_key and not backend_online:
        st.error("Cannot connect to backend. Please start backend or configure GEMINI_API_KEY in Secrets.")
        st.stop()

    # 3. Process repository
    status_box = st.status("Analyzing repository...", expanded=True)

    with status_box:
        st.write("Cloning repository...")
        st.write("Scanning and detecting languages across repository...")

        if gemini_key:
            # === CLOUD MODE (Gemini AI on Streamlit Cloud) ===
            repo_path = None
            try:
                repo_path, clone_err = clone_repository(clean_url)
                if clone_err:
                    status_box.update(label="Clone Failed", state="error", expanded=False)
                    st.error(clone_err)
                    st.stop()

                extracted = scan_and_extract_code(repo_path)
                if not extracted.get("success"):
                    status_box.update(label="Analysis Failed", state="error", expanded=False)
                    st.error(str(extracted.get("error", "No supported source files found.")))
                    st.stop()

                file_tree = list(extracted.get("file_tree", []))
                code_files = dict(extracted.get("code_files", {}))
                files_analyzed = int(extracted.get("files_analyzed", 0))
                total_files = int(extracted.get("total_files", 0))
                languages = list(extracted.get("languages", []))

                st.write("Generating explanation with Cloud AI (Gemini)...")
                explanation = generate_gemini_explanation(file_tree, code_files, gemini_key)

                status_box.update(label="Analysis complete!", state="complete", expanded=False)

                st.session_state["result_data"] = {
                    "explanation": explanation,
                    "files_analyzed": files_analyzed,
                    "total_files": total_files,
                    "languages": languages,
                    "file_list": file_tree,
                    "repo_url": clean_url,
                }
            except Exception as exc:
                status_box.update(label="Error Occurred", state="error", expanded=False)
                st.error(f"Processing error: {str(exc)}")
                st.stop()
            finally:
                if repo_path:
                    cleanup_repository(repo_path)

        else:
            # === LOCAL MODE (FastAPI + Ollama) ===
            st.write("Preparing code for Local LLM...")
            st.write("Generating explanation via Local LLM...")
            try:
                response = requests.post(
                    f"{BACKEND_URL}/explain",
                    json={"repo_url": clean_url},
                    timeout=240,
                )
            except requests.exceptions.ConnectionError:
                status_box.update(label="Connection Error", state="error", expanded=False)
                st.error("Could not connect to FastAPI backend at http://127.0.0.1:8000.")
                st.stop()
            except requests.exceptions.Timeout:
                status_box.update(label="Timeout Error", state="error", expanded=False)
                st.error("The local LLM took too long to respond.")
                st.stop()
            except Exception as exc:
                status_box.update(label="Unexpected Error", state="error", expanded=False)
                st.error(f"Failed to communicate with backend: {str(exc)}")
                st.stop()

            if response.status_code != 200:
                status_box.update(label="Backend Error", state="error", expanded=False)
                st.error(f"Backend returned error code {response.status_code}: {response.text}")
                st.stop()

            try:
                result = response.json()
            except Exception:
                status_box.update(label="Parsing Error", state="error", expanded=False)
                st.error("Backend did not return valid JSON.")
                st.stop()

            if not isinstance(result, dict):
                status_box.update(label="Format Error", state="error", expanded=False)
                st.error("Unexpected response format.")
                st.stop()

            if not result.get("success", False):
                err_msg = result.get("error", "Unknown error occurred.")
                status_box.update(label="Explanation Failed", state="error", expanded=False)
                st.error(str(err_msg))
                st.stop()

            status_box.update(label="Analysis complete!", state="complete", expanded=False)

            st.session_state["result_data"] = {
                "explanation": str(result.get("explanation", "")),
                "files_analyzed": int(result.get("files_analyzed", 0)),
                "total_files": int(result.get("total_files", 0)),
                "languages": list(result.get("languages", [])),
                "file_list": list(result.get("files", [])),
                "repo_url": clean_url,
            }

# Display results if available in session state
if "result_data" in st.session_state:
    data = st.session_state["result_data"]

    st.markdown("---")
    st.subheader("Analysis Summary")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Files Analyzed", f"{data['files_analyzed']} of {data['total_files']} files")
    with col2:
        lang_str = ", ".join(data["languages"]) if data["languages"] else "None detected"
        st.metric("Languages Detected", lang_str)

    st.markdown("---")
    st.subheader("Project Explanation")
    st.markdown(data["explanation"])

    # File tree expander
    if data["file_list"]:
        with st.expander(f"Repository Files List ({len(data['file_list'])})"):
            st.code("\n".join(data["file_list"]), language="text")

    # Download button
    st.download_button(
        label="Download Explanation as Markdown",
        data=data["explanation"],
        file_name="repository_explanation.md",
        mime="text/markdown",
        use_container_width=True,
    )

    if st.button("Clear Result", use_container_width=True):
        del st.session_state["result_data"]
        st.rerun()

st.markdown("---")
provider_name = "Gemini Cloud AI" if gemini_key else f"FastAPI + Ollama ({active_model_name})"
st.caption(f"Powered by GitPython • Streamlit • {provider_name}")
