Here’s the updated **Markdown plan** with the **Databricks Apps custom UI** added into the MVP scope (Week 4). I’ve revised the architecture and roadmap so the project doesn’t rely on Playground for the final demo — instead, users will interact through a **custom Databricks App UI** that wraps the Claude + MCP workflow.

---

# Project Plan: Databricks AI Agent with Claude Code SDK, MCP Integration, and Custom UI

## Overview and Objectives

This project builds a **Databricks-native AI Copilot** powered by **Claude Code SDK** and **Model Context Protocol (MCP)**. It helps **Data Engineers** and **ML Engineers** analyze existing notebooks/jobs and generate **Databricks Asset Bundles (DABs)**, unit tests, and CI/CD scaffolds.

**Key objectives:**

* **MVP (Hackathon, 4 weeks)**

  * Use Claude Code SDK + MCP to analyze and operate on **existing notebooks/jobs**.
  * Deploy a **custom Databricks App UI** as the interactive interface (instead of Playground).
  * Secure API keys via Databricks secrets.
  * Support **Serverless compute** first, fallback to clusters.
  * MVP deployment scope: **dev environment only** (with unit test generation).

* **Phase 2 (Post-MVP)**

  * Automatic job prioritization (metadata-driven).
  * Bootstrap **new DABs projects** (jobs, pipelines).
  * CI/CD with GitHub Actions for staging/prod.
  * More advanced agent autonomy and recommendations.

---

## Updated Architecture (with Custom App UI)

```
[User in Databricks Workspace (Custom App UI)]
        │
        ▼
 [Claude Code SDK Agent]
 (prompt + tool orchestration)
        │
        ▼
 [Databricks MCP Servers]
   ├─ Managed MCP (UC Functions, Genie, Vector Search)
   └─ Custom MCP (App exposing jobs/notebooks tools)
        │
        ▼
 [Databricks Workspace Services]
   - Jobs API
   - Notebooks API
   - DLT / SQL
   - Unity Catalog (governance)
```

### New Component: **Databricks App UI**

* **Built with React/TypeScript** (or FastAPI + minimal JS if faster).
* **UI Features:**

  * Chat panel for user-agent interaction.
  * Resource selector (list notebooks/jobs, choose which to analyze).
  * Bundle preview (generated `bundle.yml`, unit test scaffolds).
  * “Run” and “Deploy” buttons for triggering jobs.
* **Deployment:**

  * Packaged as a **Databricks App** so it runs serverlessly in the workspace.
  * OAuth + UC ensures users only see what they have permission to.

---

## 4-Week Timeline (Revised with UI in MVP)

### Week 1 – Setup & Foundations

* Configure **Unity Catalog** + serverless.
* Store **Claude API key in secret scope**.
* Prototype Claude SDK call in notebook.
* Prototype MCP tool call (managed UC functions).
* Deliverables: dev env + skeleton Claude integration.

### Week 2 – Custom MCP Server Core

* Build **Databricks App (MCP server)** exposing:

  * `list_jobs`, `run_job`
  * `list_notebooks`, `export_notebook`
* Deploy app via `databricks apps deploy`.
* Wire Claude agent to call MCP tools.
* Unit tests for MCP handlers.
* Deliverables: Claude can list/run jobs through MCP.

### Week 3 – Expand & Polish

* Add **export\_notebook** + summarization.
* Improve system prompt + tool descriptions.
* Harden security (whitelist tools, error handling).
* Deliverables: full toolset for MVP, stable agent loop.

### Week 4 – **Custom Databricks App UI**

* Build **interactive UI** in Databricks Apps:

  * Chat interface with Claude.
  * Notebook/job picker component.
  * Generated DAB preview window.
  * “Deploy bundle” button (dev only).
* Connect UI to Claude agent backend.
* Test end-to-end (user selects notebook → agent analyzes → outputs DAB + unit tests).
* Deliverables: fully functional **Databricks App UI** as hackathon demo.

---

## UI Design Recommendations

### Layout Structure
```
┌─────────────────────────────────────────────────────────┐
│  Header: Databricks AI Copilot                         │
│  [Status: Connected] [User: xxx] [Workspace: xxx]      │
├─────────────────┬───────────────────┬──────────────────┤
│                 │                   │                  │
│  Resource       │   Chat Interface  │  Output Panel    │
│  Explorer       │                   │                  │
│  (25%)          │      (45%)        │     (30%)        │
│                 │                   │                  │
│ ┌─────────────┐ │ ┌───────────────┐ │ ┌──────────────┐│
│ │Jobs         │ │ │ Agent: Ready  │ │ │Preview:      ││
│ │├─ETL_Daily  │ │ │ to help...    │ │ │bundle.yml    ││
│ │├─ML_Train   │ │ └───────────────┘ │ │              ││
│ │└─Reports    │ │                   │ │targets:      ││
│ │             │ │ ┌───────────────┐ │ │  dev:        ││
│ │Notebooks    │ │ │User: Analyze  │ │ │    mode:... ││
│ │├─/Analysis  │ │ │ETL_Daily job  │ │ └──────────────┘│
│ │├─/Models    │ │ └───────────────┘ │                  │
│ │└─/Utils     │ │                   │ [Tabs: DAB|Tests]│
│ └─────────────┘ │ [Send] [Clear]    │ [Deploy] [Save] │
└─────────────────┴───────────────────┴──────────────────┘
```

### Core UI Components

#### 1. **Resource Explorer Panel** (Left)
* **Tree view** of workspace assets:
  * Jobs (with run status indicators)
  * Notebooks (with last modified dates)
  * Pipelines (DLT)
  * SQL Dashboards
* **Quick actions** on hover:
  * Analyze
  * Generate DAB
  * Create tests
* **Search/filter** bar at top
* **Multi-select** checkboxes for batch operations

#### 2. **Chat Interface** (Center)
* **Message history** with:
  * User queries in light bubbles
  * Agent responses in colored bubbles
  * Code snippets with syntax highlighting
  * Collapsible sections for long outputs
* **Input area** with:
  * Rich text editor
  * Slash commands (e.g., `/analyze`, `/generate-dab`)
  * File attachment support
  * Voice input option
* **Context indicators**:
  * Currently selected resources
  * Active MCP tools being used
  * Processing status spinner

#### 3. **Output Panel** (Right)
* **Tabbed interface**:
  * **DAB Preview**: YAML with syntax highlighting
  * **Unit Tests**: Generated test code
  * **Execution Log**: Tool calls and results
  * **Recommendations**: Agent suggestions
* **Actions toolbar**:
  * Deploy to Dev
  * Save to Repo
  * Copy to Clipboard
  * Download as ZIP
* **Diff view** for comparing before/after

### Visual Design Guidelines

#### Color Scheme
* **Primary**: Databricks Orange (#FF3621)
* **Secondary**: Deep Blue (#1B3A57)
* **Background**: Light Gray (#F7F7F7)
* **Success**: Green (#00A972)
* **Warning**: Amber (#FDB515)
* **Error**: Red (#D13438)

#### Typography
* **Font Family**: Inter or Segoe UI
* **Headers**: 16-20px, semi-bold
* **Body**: 14px, regular
* **Code**: JetBrains Mono, 13px

#### Interactive Elements
* **Buttons**: Rounded corners (4px), hover effects
* **Cards**: Subtle shadows, 8px padding
* **Loading states**: Skeleton screens
* **Tooltips**: On hover for all actions
* **Keyboard shortcuts**: Cmd+K for quick actions

### Advanced Features (MVP)

#### 1. **Smart Suggestions**
* Autocomplete for common tasks
* Recently used resources
* Suggested next actions based on context

#### 2. **Progress Tracking**
* Visual progress bar for long operations
* Step-by-step breakdown of agent actions
* ETA for completion

#### 3. **Error Handling**
* Clear error messages with recovery options
* Retry mechanisms for failed operations
* Fallback to manual mode if needed

#### 4. **Collaboration Features**
* Share chat sessions via URL
* Export conversation history
* Save and load chat templates

### Technical Implementation

#### Frontend Stack
* **Framework**: React 18 with TypeScript
* **State Management**: Zustand or Redux Toolkit
* **UI Library**: Ant Design or Material-UI
* **Styling**: Tailwind CSS or Styled Components
* **WebSocket**: Socket.io for real-time updates

#### Backend Integration
* **API Gateway**: FastAPI or Express
* **Authentication**: Databricks OAuth
* **Session Management**: Redis or in-memory
* **File Handling**: Streaming for large notebooks

### Accessibility Requirements
* WCAG 2.1 AA compliance
* Keyboard navigation support
* Screen reader compatibility
* High contrast mode option
* Adjustable font sizes

---

## In-Scope vs Out-of-Scope (MVP)

| **In Scope (MVP)**                            | **Out of Scope (MVP)**                        |
| --------------------------------------------- | --------------------------------------------- |
| Claude SDK integration (dev key via secret)   | Production CI/CD pipelines (GitHub Actions)   |
| MCP custom server with jobs/notebooks tools   | Auto-prioritization of jobs/notebooks         |
| Databricks App UI (chat + resource selector)  | Creating brand new projects/DABs from scratch |
| Unit test scaffolds for analyzed code         | Multi-user scaling & advanced caching         |
| Dev environment deploy (serverless preferred) | Prod/staging deploy pipelines                 |

---

## Checklist Summary

**Before coding:**

* [ ] Unity Catalog enabled workspace.
* [ ] Serverless compute available.
* [ ] Secret scope with Claude API key.
* [ ] GitHub repo created.

**By end of Week 2:**

* [ ] Custom MCP server deployed via Databricks Apps.
* [ ] Tools: list/run jobs, list/export notebooks.
* [ ] Claude agent connected & calling tools.

**By end of Week 4 (MVP demo):**

* [ ] Custom Databricks App UI deployed.
* [ ] Chat + job/notebook selection in UI.
* [ ] Bundle + unit tests preview in UI.
* [ ] End-to-end demo: select → analyze → generate bundle.

---

Would you like me to also **mock up the Databricks App UI** (React component structure + rough layout) so you can see how the chat panel, resource selector, and bundle preview would fit together?
