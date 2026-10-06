from __future__ import annotations

import os
import sys
import time
import requests
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.github_processor import (
    cleanup_repository,
    clone_repository,
    fetch_repository_fast,
    scan_and_extract_code,
)
from backend.llm import generate_gemini_explanation

# Backend configuration for local mode
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="GitHub Repository Code Explainer",
    layout="wide",
)

# Custom Styling: Warm Peach Theme
st.markdown(
    """
    <style>
    /* Main App Peach Theme */
    .stApp {
        background-color: #FFF3EB !important;
        color: #2D2320 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #FFEADB !important;
        border-right: 1px solid #F5C6AA !important;
    }

    [data-testid="stSidebar"] * {
        color: #2D2320 !important;
    }

    [data-testid="stSidebar"] code {
        background-color: #FFF3EB !important;
        color: #A34828 !important;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* Main Title & Typography */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 4px;
        color: #2D2320;
        text-transform: uppercase;
    }

    .hero-subtitle {
        font-size: 1.05rem;
        color: #6E534B;
        margin-bottom: 24px;
    }

    /* Status Badges */
    .status-card-container {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 24px;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
    }

    .badge-ollama {
        background-color: #FFE6D5;
        color: #9A4325;
        border: 1px solid #F4C4A8;
    }

    .badge-model {
        background-color: #FEDDCC;
        color: #8C3B1E;
        border: 1px solid #F2BBA0;
    }

    .status-note {
        font-size: 0.85rem;
        color: #6E534B;
        max-width: 480px;
        line-height: 1.35;
    }

    /* Input Section */
    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #2D2320;
    }

    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        color: #2D2320 !important;
        border: 1px solid #EBB89E !important;
        border-radius: 8px !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #E07A5F !important;
        box-shadow: 0 0 0 1px #E07A5F !important;
    }

    /* Primary Action Button */
    div.stButton > button {
        background-color: #E07A5F !important;
        border-color: #E07A5F !important;
        color: #FFFFFF !important;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 24px;
    }

    div.stButton > button:hover {
        background-color: #C85A32 !important;
        border-color: #C85A32 !important;
    }

    /* Timing Banner */
    .timing-banner {
        background-color: #E9F7EF;
        border: 1px solid #82C99B;
        color: #1E6B37;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.95rem;
        margin-top: 14px;
        margin-bottom: 20px;
    }

    /* Repository Overview Banner */
    .repo-banner {
        margin-top: 10px;
        margin-bottom: 20px;
    }

    .repo-heading {
        font-size: 1.6rem;
        font-weight: 700;
        color: #2D2320;
    }

    .repo-meta {
        font-size: 0.95rem;
        color: #6E534B;
        margin-top: 4px;
    }

    .repo-meta a {
        color: #D45D3B;
        text-decoration: none;
        font-weight: 500;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F5C6AA !important;
        border-radius: 10px !important;
        padding: 14px 18px !important;
        box-shadow: 0 1px 4px rgba(45, 35, 32, 0.05);
    }

    div[data-testid="stMetricValue"] {
        color: #C85A32 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        border-bottom: 1px solid #F3D0BC;
    }

    .stTabs [data-baseweb="tab"] {
        color: #6E534B;
        font-weight: 500;
        padding-bottom: 10px;
    }

    .stTabs [aria-selected="true"] {
        color: #E07A5F !important;
        border-bottom-color: #E07A5F !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------- SIDEBAR: Local Ollama Setup -----------------
with st.sidebar:
    st.subheader("Local Ollama Setup")
    st.write("Every user uses their own local AI model:")
    
    st.markdown("**1. Install Ollama** from [ollama.com](https://ollama.com).")
    
    st.markdown("**2. Download Qwen 2.5:**")
    st.code("ollama pull qwen2.5-coder:1.5b", language="bash")
    
    st.markdown("**3. Start Ollama with Browser Access:**")
    st.caption("Windows (PowerShell):")
    st.code('$env:OLLAMA_ORIGINS="*"\nollama serve', language="powershell")
    st.caption("Mac / Linux:")
    st.code('OLLAMA_ORIGINS="*" ollama serve', language="bash")
    
    st.markdown("**4. Paste any public repository URL, and analyze!**")
    
    st.markdown("---")
    st.caption("No external server dependencies or rate limits when running locally.")

# ----------------- BACKEND & PROVIDER DETECTION -----------------
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

backend_online = False
ollama_ready = False
health_message = ""
active_model_name = "Qwen 2.5"

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

# ----------------- MAIN HEADER -----------------
st.markdown('<div class="hero-title">GitHub Repository Code Explainer</div>', unsafe_allow_html=True)
subtitle_model = "Gemini AI" if gemini_key else f"local Ollama + {active_model_name}"
st.markdown(f'<div class="hero-subtitle">Understand any public GitHub repository using {subtitle_model}.</div>', unsafe_allow_html=True)

# Status Badges
ollama_status_text = "Local Ollama: Ready" if ollama_ready else ("Cloud AI: Active" if gemini_key else "Local Ollama: Standby")
model_badge_text = f"{active_model_name}: Active" if (ollama_ready or gemini_key) else f"{active_model_name}: Ready"

st.markdown(
    f"""
    <div class="status-card-container">
        <div class="status-badge badge-ollama">
            <span>●</span>
            <span>{ollama_status_text}</span>
        </div>
        <div class="status-badge badge-model">
            <span>ℹ</span>
            <span>{model_badge_text}</span>
        </div>
        <div class="status-note">
            Each user uses their OWN laptop's Ollama instance. No shared cloud server or paid API keys required.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- INPUT SECTION -----------------
st.markdown('<div class="section-title">Analyze Any Public GitHub Repository</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([4, 1])

with col_input:
    repo_url = st.text_input(
        "Enter Public GitHub Repository URL:",
        placeholder="https://github.com/Bhumikaravi/github-code-explainers",
        label_visibility="visible",
    )

with col_btn:
    st.write("<div style='height: 28px'></div>", unsafe_allow_html=True)
    analyze_clicked = st.button("Analyze Repository", type="primary", use_container_width=True)

# Helpers for classification and structure
def parse_repo_owner_name(url: str) -> tuple[str, str]:
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "Repository", "Project"

def classify_repo(languages: list[str], file_tree: list[str]) -> str:
    langs_lower = [l.lower() for l in languages]
    files_lower = [f.lower() for f in file_tree]

    has_python = "python" in langs_lower
    has_js = any(l in langs_lower for l in ["javascript", "typescript"])
    has_web = any("app.py" in f or "main.py" in f or "index.html" in f or "package.json" in f for f in files_lower)

    if has_python and has_web:
        return "Python Web Application / API"
    elif has_js and has_web:
        return "Full-Stack Web Application"
    elif has_python:
        return "Python Software Package"
    elif "java" in langs_lower:
        return "Java Application"
    elif "c++" in langs_lower or "c" in langs_lower:
        return "Systems Software / Native Application"
    elif languages:
        return f"{languages[0]} Software Project"
    return "Software Project"

def build_structure_overview(file_tree: list[str]) -> str:
    top_dirs = set()
    root_files = []
    for path in file_tree:
        parts = path.split("/")
        if len(parts) > 1:
            top_dirs.add(parts[0] + "/")
        else:
            root_files.append(parts[0])

    lines = []
    lines.append("[Root Directory]")
    for d in sorted(top_dirs):
        lines.append(f"  ├── [DIR] {d}")
    for idx, f in enumerate(sorted(root_files)):
        prefix = "  └── " if idx == len(root_files) - 1 else "  ├── "
        lines.append(f"{prefix}{f}")
    return "\n".join(lines)

# ----------------- EXECUTION FLOW -----------------
@st.cache_data(show_spinner=False, ttl=3600)
def analyze_repo_fast(clean_url: str, gemini_key: str | None, backend_url: str, active_model: str) -> dict:
    if gemini_key:
        # === CLOUD MODE (Gemini AI) ===
        repo_path = None
        extracted = fetch_repository_fast(clean_url)
        if not extracted or not extracted.get("success"):
            repo_path, clone_err = clone_repository(clean_url)
            if clone_err:
                raise RuntimeError(clone_err)
            extracted = scan_and_extract_code(repo_path)
            if not extracted.get("success"):
                raise RuntimeError(str(extracted.get("error", "No supported source files found.")))

        file_tree = list(extracted.get("file_tree", []))
        code_files = dict(extracted.get("code_files", {}))
        files_analyzed = int(extracted.get("files_analyzed", 0))
        total_files = int(extracted.get("total_files", 0))
        languages = list(extracted.get("languages", []))

        try:
            explanation = generate_gemini_explanation(file_tree, code_files, gemini_key)
        finally:
            if repo_path:
                cleanup_repository(repo_path)

        return {
            "explanation": explanation,
            "files_analyzed": files_analyzed,
            "total_files": total_files,
            "languages": languages,
            "file_list": file_tree,
            "repo_url": clean_url,
            "model": "Gemini AI",
        }

    # === LOCAL MODE (FastAPI + Ollama) ===
    response = requests.post(
        f"{backend_url}/explain",
        json={"repo_url": clean_url},
        timeout=240,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Backend error ({response.status_code}): {response.text}")

    result = response.json()
    if not result.get("success", False):
        raise RuntimeError(str(result.get("error", "Analysis failed.")))

    return {
        "explanation": str(result.get("explanation", "")),
        "files_analyzed": int(result.get("files_analyzed", 0)),
        "total_files": int(result.get("total_files", 0)),
        "languages": list(result.get("languages", [])),
        "file_list": list(result.get("files", [])),
        "repo_url": clean_url,
        "model": active_model,
    }


if analyze_clicked:
    clean_url = repo_url.strip()

    if not clean_url:
        st.error("Please enter a GitHub repository URL.")
        st.stop()

    if not (clean_url.startswith("https://github.com/") or clean_url.startswith("http://github.com/")):
        st.error("Please enter a valid GitHub repository URL (e.g. https://github.com/owner/repository).")
        st.stop()

    if not gemini_key and not backend_online:
        st.error("Cannot connect to backend. Please start your local backend or configure GEMINI_API_KEY.")
        st.stop()

    start_time = time.time()
    with st.spinner("Analyzing repository structure and code..."):
        try:
            result_data = analyze_repo_fast(clean_url, gemini_key, BACKEND_URL, active_model_name)
            elapsed = time.time() - start_time
            res = dict(result_data)
            res["elapsed"] = elapsed
            st.session_state["result_data"] = res
        except Exception as exc:
            st.error(f"Processing error: {str(exc)}")
            st.stop()

# ----------------- DISPLAY RESULTS IN TABS -----------------
if "result_data" in st.session_state:
    data = st.session_state["result_data"]
    owner, repo_name = parse_repo_owner_name(data["repo_url"])
    classification = classify_repo(data["languages"], data["file_list"])

    # Timing notification
    st.markdown(
        f'<div class="timing-banner">Analysis complete in {data["elapsed"]:.2f}s!</div>',
        unsafe_allow_html=True,
    )

    # 5 Tabs matching friend's layout
    tab_overview, tab_struct, tab_files, tab_ai, tab_tech = st.tabs([
        "Overview",
        "Repository Structure",
        "Files & Folders",
        "AI Explanation",
        "Technical Details",
    ])

    with tab_overview:
        st.markdown(
            f"""
            <div class="repo-banner">
                <div class="repo-heading">Repository: {owner} / {repo_name}</div>
                <div class="repo-meta">
                    Classification: <strong>{classification}</strong> | URL: <a href="{data['repo_url']}" target="_blank">{data['repo_url']}</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Total Discovered Files", data["total_files"])
        with col_m2:
            st.metric("Analyzed Source Files", data["files_analyzed"])
        with col_m3:
            st.metric("Primary Languages", ", ".join(data["languages"]) if data["languages"] else "None")

        st.markdown("### Quick Summary")
        st.write(
            f"This project is a **{classification}** containing **{data['total_files']} files**. "
            f"Key code was scanned across {', '.join(data['languages']) if data['languages'] else 'detected files'} "
            f"and summarized using {data['model']}."
        )

    with tab_struct:
        st.markdown("### Visual Directory Tree")
        st.code(build_structure_overview(data["file_list"]), language="text")

    with tab_files:
        st.markdown(f"### Discovered Project Files ({len(data['file_list'])})")
        st.code("\n".join(data["file_list"]), language="text")

    with tab_ai:
        st.markdown("### Comprehensive AI Codebase Explanation")
        st.markdown(data["explanation"])

        col_dl, col_clr = st.columns([3, 1])
        with col_dl:
            st.download_button(
                label="Download Explanation as Markdown",
                data=data["explanation"],
                file_name=f"{repo_name}_explanation.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_clr:
            if st.button("Clear Result", use_container_width=True):
                del st.session_state["result_data"]
                st.rerun()

    with tab_tech:
        st.markdown("### Technical Diagnostics")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write(f"- **AI Model Engine**: `{data['model']}`")
            st.write(f"- **Analysis Elapsed Time**: `{data['elapsed']:.2f} seconds`")
            st.write(f"- **Target URL**: `{data['repo_url']}`")
        with col_t2:
            st.write(f"- **Total Files**: `{data['total_files']}`")
            st.write(f"- **Key Files Analyzed**: `{data['files_analyzed']}`")
            st.write(f"- **Detected Stacks**: `{', '.join(data['languages'])}`")

st.markdown("---")
st.caption("Powered by GitPython • Streamlit • Local Ollama / Gemini AI")
