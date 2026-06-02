# Deep Research Agent Platform 🔍🤖

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/LangGraph-Stateful_Agents-purple.svg)](https://github.com/langchain-ai/langgraph)
[![Next.js](https://img.shields.io/badge/Next.js-16.x-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An enterprise-grade, multi-agent research platform built with **LangGraph**, **FastAPI**, **Next.js**, and **PostgreSQL/SQLite**. It automates deep, web-scale research, verifies statements, drafts detailed reports, and incorporates explicit human-in-the-loop (HITL) approval gates.

---

## 🌟 Key Features

*   **Five-Agent Collaborative Team**:
    *   **Planner**: Formulates structured research plans (topics and target search queries).
    *   **Researcher**: Performs parallel web searches (Tavily/DuckDuckGo), scrapes raw page contents (BeautifulSoup), and extracts assertions.
    *   **Fact Checker**: Cross-references claims against raw scraped text to flag contradictions and prevent hallucinations.
    *   **Writer**: Drafts comprehensive Markdown reports with inline source citations.
    *   **Reviewer**: Evaluates report coverage and triggers revision cycles or final approvals.
*   **Human-in-the-Loop (HITL) Gates**: Pause points before Web Search (to edit/approve queries) and before publication (to review draft reports or request edits).
*   **Durable State Checkpointing**: Powered by database checkpointers (`PgSaver`/`AsyncSqliteSaver`), agent threads survive server restarts and network interruptions.
*   **Real-time Push Updates**: Logs, agent statuses, and visualization changes are streamed instantly from FastAPI to the Next.js client via WebSockets.
*   **Interactive Citations & Layout**: Clicking inline citations (e.g. `[Source S1]`) opens a sidebar showing the page title, URL link, and scraped passage snippet.
*   **Zero-Configuration Fallback**: Works out of the box with SQLite and free DuckDuckGo searches if Postgres, Redis, or API keys are not provided.

---

## 🏗️ System Workflow

The platform operates on a cyclic multi-agent graph with interrupts:

```mermaid
graph TD
    Start([User Input: Prompt]) --> Node_Planner[Planner Agent]
    Node_Planner --> Node_Plan_Interrupt{Interrupt: Plan Approval}
    Node_Plan_Interrupt -- Approved --> Node_Research[Research Agent]
    Node_Plan_Interrupt -- Rejected/Feedback --> Node_Planner
    
    Node_Research --> Node_FactChecker[Fact Checker Agent]
    Node_FactChecker --> Node_Writer[Writer Agent]
    Node_Writer --> Node_Reviewer[Reviewer Agent]
    
    Node_Reviewer --> Node_Review_Interrupt{Interrupt: Final Approval}
    Node_Review_Interrupt -- Approved --> End([Publish Report])
    Node_Review_Interrupt -- Needs Revision --> Node_Planner
```

---

## 🚀 Quick Start Guide

### Step 1: Clone and Set Up the Backend

1.  Navigate into the `backend` folder:
    ```bash
    cd backend
    ```
2.  Create and activate a Python virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure your environment variables:
    *   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Add your LLM API keys:
        ```env
        LLM_PROVIDER=google  # or openai
        GEMINI_API_KEY=your_gemini_key
        OPENAI_API_KEY=your_openai_key
        TAVILY_API_KEY=your_tavily_key
        ```
    *   *Note: If no database URLs or API keys are provided, the server defaults to SQLite checkpoints and DuckDuckGo search fallbacks.*
5.  Start the FastAPI backend server:
    ```bash
    python -m app.main
    ```

### Step 2: Set Up the Frontend

1.  Navigate into the `frontend` folder:
    ```bash
    cd ../frontend
    ```
2.  Install the node packages:
    ```bash
    npm install
    ```
3.  Start the Next.js development server:
    ```bash
    npm run dev
    ```
4.  Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

## 🐳 Docker Services (Optional)

To run the application with high-throughput persistent databases (PostgreSQL and Redis), launch the services in the root directory:

```bash
docker-compose up -d
```

Update your backend `.env` variables to connect:
```env
DATABASE_URL=postgresql://research_user:research_password@localhost:5432/deep_research_platform
REDIS_URL=redis://localhost:6379/0
```

---

## 📂 Project Structure

```text
├── docker-compose.yml       # Orchestrates Postgres and Redis containers
├── info.md                  # Detailed technical architecture documentation
├── prd.md                   # Product Requirements Document
├── README.md                # General overview and quickstart instructions
├── backend
│   ├── requirements.txt     # Python requirements file
│   ├── app
│   │   ├── config.py        # Settings and configurations loader
│   │   ├── db.py            # SQLAlchemy database models
│   │   ├── main.py          # FastAPI application & websocket managers
│   │   ├── services
│   │   │   └── search.py    # Tavily/DuckDuckGo searches & page scraper
│   │   └── agents
│   │       ├── state.py     # LangGraph shared state dictionary
│   │       └── graph.py     # Agents nodes and Compiled Workflow Graph
│   └── tests
│       ├── test_search.py   # Web search and scraping unit tests
│       ├── test_graph.py    # LangGraph compile & interrupt integration tests
│       ├── test_api.py      # FastAPI HTTP requests integration tests
│       └── test_e2e_flow.py # End-to-end full platform validation test
└── frontend
    ├── package.json         # Frontend packages config
    └── app
        ├── globals.css      # Premium layout styling CSS
        ├── layout.tsx       # Next.js root layout wrapper
        ├── page.tsx         # Dashboard landing page
        └── research
            └── [id]
                └── page.tsx # Workspace dynamic details page
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
