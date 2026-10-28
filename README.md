<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1E1E2E,4C4F69,7287FD&height=220&section=header&text=GitHub%20Codebase%20Explainer&fontSize=38&fontColor=ffffff&fontAlignY=38&desc=AI-Powered%20Repository%20Inspection%20%26%20Beginner-Friendly%20Code%20Analysis&descSize=16&descAlignY=62&descAlign=50" width="100%" alt="GitHub Codebase Explainer Header Banner"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Category-Generative%20AI-blueviolet?style=for-the-badge" alt="GenAI"/> <img src="https://img.shields.io/badge/LLM-Gemini%20API%20%7C%20Ollama-8A2BE2?style=for-the-badge" alt="LLM"/> <img src="https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit" alt="Streamlit"/> <img src="https://img.shields.io/badge/Parser-Python%20AST-3776AB?style=for-the-badge" alt="AST"/>
</p>


## 📌 Table of Contents
- [📖 Executive Summary](#-executive-summary)
- [✨ Key Features & Capabilities](#-key-features--capabilities)
- [🏗️ System Architecture & Workflow](#️-system-architecture--workflow)
- [🛠️ Tech Stack Breakdown](#️-tech-stack-breakdown)
- [⚙️ Reproducible Quickstart & Setup](#️-reproducible-quickstart--setup)
- [📂 Project Directory Layout](#-project-directory-layout)
- [👩‍💻 Author & Contributions](#-author--contributions)

---

## 📖 Executive Summary
### Problem Statement
Exploring unfamiliar open-source GitHub repositories is intimidating for students and junior developers due to fragmented documentation, undocumented functions, and complex folder structures.

### Motivation & Solution Overview
GitHub Codebase Explainer is a full-stack GenAI web application that parses public GitHub repositories, extracts Abstract Syntax Trees (AST) and directory structures, and leverages LLMs (Google Gemini API / Ollama) to synthesize beginner-friendly codebase walkthroughs.

---

## ✨ Key Features & Capabilities
- **Repository Ingestion:** Ingests any public GitHub repository URL and extracts file hierarchies.
- **AST Code Parsing:** Inspects classes, functions, and import graphs using Python's native `ast` module.
- **Dual LLM Support:** Seamlessly switches between cloud LLMs (Google Gemini 1.5/2.0) and local offline LLMs (Ollama).
- **Beginner-Friendly Summaries:** Formats technical breakdowns with analogies, architectural workflows, and setup tips.

---

## 🏗️ System Architecture & Workflow
```mermaid
flowchart LR
    URL[Public GitHub Repo URL] --> Ingest[Repo Processor: File Tree & AST]
    Ingest --> Filter[Language & File Filtering]
    Filter --> Prompt[Context Assembly & Prompt Builder]
    Prompt --> LLM[LLM Engine: Gemini / Ollama]
    LLM --> UI[Streamlit Interactive Walkthrough]
```

---

## 🛠️ Tech Stack Breakdown
| Component | Technologies |
|---|---|
| **Web Interface** | Streamlit |
| **Language & Parsing** | Python 3.10+, AST (Abstract Syntax Tree) |
| **AI Models** | Google Gemini API, Ollama (Local Models) |
| **API Integration** | Google GenAI SDK, Requests, GitPython |

---

## ⚙️ Reproducible Quickstart & Setup
### Prerequisites
- Python 3.10+
- Google Gemini API key (optional for cloud mode) or Ollama (for local mode)

### Setup Steps
```bash
git clone https://github.com/Bhumikaravi/github-code-explainers.git
cd github-code-explainers

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

streamlit run backend/main.py
```

---

## 📂 Project Directory Layout
```text
github-code-explainers/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
└── backend/
    ├── github_processor.py
    ├── llm.py
    └── main.py
```

---

## 👩‍💻 Author & Contributions
Developed by **Bhumika Ravi** ([@Bhumikaravi](https://github.com/Bhumikaravi)), Bachelor of Computer Applications (BCA) at **Alliance University, Bengaluru**.

- 💻 **GitHub Profile:** [github.com/Bhumikaravi](https://github.com/Bhumikaravi)
- 🔗 **LinkedIn:** [linkedin.com/in/bhumika-ravi-b5a01b326](https://www.linkedin.com/in/bhumika-ravi-b5a01b326/)
- 📬 **Email Contact:** [bhumikaravi2006@gmail.com](mailto:bhumikaravi2006@gmail.com)

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1E1E2E,4C4F69,7287FD&height=100&section=footer" width="100%" alt="Footer Banner"/>
</p>
