# Autonomous SDLC Orchestrator

The **Autonomous SDLC (Software Development Life Cycle) Orchestrator** is a cutting-edge platform designed to automate and self-heal the software engineering process. By leveraging a FastAPI backend, advanced AI agents (CrewAI & AutoGen), and UiPath's robotic process automation and testing capabilities, this system achieves autonomous planning, code generation, execution, validation, and remediation.

---

## 🏗 Architecture Overview

The system is organized into a microservices-like architecture powered by an LLM-driven core:

- **FastAPI Backend (Orchestrator Core)**: Exposes endpoints for the complete SDLC pipeline. It routes AI tasks to specialized agents (Architects, Developers, QA) depending on the stage of the lifecycle.
- **AI Agents**:
  - **CrewAI**: Handles the requirements analysis, security scoping, and architecture planning.
  - **AutoGen**: Drives the self-healing loop. It generates Dockerfiles, test manifests, and automatically attempts remediation when tests fail.
- **UiPath Test Cloud & Action Center**: Triggers the robotic tests, validates the deployed artifacts, and invokes human-in-the-loop approvals for production deployments.

---

## 🔌 API Endpoints Reference

The FastAPI service runs a dynamic endpoints system (`Services Menu`). Below are the primary endpoints exposed for the orchestrator:

### `POST /analyze`
**Role:** Requirements Analysis & Architecture
- **Description:** Receives the user prompt and delegates to CrewAI to formulate a technical architecture plan.
- **Input Payload:**
  ```json
  {
    "prompt": "Deploy a secure Node.js application.",
    "risk_level": "High",
    "environment": "dev"
  }
  ```
- **Output:** `{"status": "success", "plan": "..."}`

### `POST /generate-artifacts`
**Role:** Artifact Generation
- **Description:** Takes the architecture plan and incident ID, and triggers the AutoGen loop to generate the required scripts and Dockerfiles in a dedicated sandbox environment.
- **Input Payload:**
  ```json
  {
    "plan": "...",
    "incident_id": "REQ-12345"
  }
  ```
- **Output:** `{"status": "success", "result": "..."}`

### `POST /validate`
**Role:** Test Execution
- **Description:** Runs a validation script simulating the test environment execution. It triggers the testing suite and captures logs (STDOUT/STDERR).
- **Input Payload:**
  ```json
  {
    "script_path": "/workspace_agents/REQ-12345/test.sh"
  }
  ```
- **Output:** `{"status": "success", "returncode": 0, "logs": "..."}`

### `POST /remediate`
**Role:** Auto-Remediation & Feedback Loop
- **Description:** When validation fails, this endpoint takes the error logs and triggers a remediation agent to analyze the stack trace and fix the generated code iteratively.
- **Input Payload:**
  ```json
  {
    "incident_id": "REQ-12345",
    "logs": "Error: port 8080 already in use"
  }
  ```
- **Output:** `{"status": "success", "result": "..."}`

---

## 🤖 UiPath Integration

The orchestrator integrates directly with a UiPath project via `Main.xaml`. The Robot executes the entire lifecycle by making sequential HTTP POST calls to the FastAPI backend.

### Key UiPath Configurations:
1. **Timeout Configured**: As LLM operations (generation/remediation) can be time-consuming, all `ui:HttpClient` activities enforce a `TimeoutMS` of `300000` (5 minutes) to prevent premature disconnects.
2. **Strict Data Parsing**: Since `Main.xaml` uses the Portable framework (.NET 6+), XML structures for JSON mapping (`<JObject>`) have been explicitly omitted. JSON serialization is handled gracefully via `Newtonsoft.Json.JsonConvert.SerializeObject`.
3. **Self-Healing Loop**: The `Main.xaml` process evaluates the result of the `/validate` endpoint. If the test returns a `FAILED` status, it conditionally executes the `/remediate` endpoint without crashing, saving the `Fixed_Code.md` artifact locally for traceability.

---

## 🚀 Setup & Execution

### Prerequisites
- Python 3.10+
- Uvicorn & FastAPI installed
- Docker (for executing generated artifacts)
- UiPath Studio (Version 23.10+ or 26+)

### 1. Start the Backend Server
Make sure to copy the `.env.example` to `.env` and provide your API keys for the LLM providers (OpenAI, Groq, or your local Ollama address).

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Upon startup, the terminal will print a matrix identifying the active LLM Engine (e.g., `OLLAMA (Local)`, `GROQ`, or `OPENAI`).

### 2. Run the UiPath Robot
The `Orchestrateur_Final` project must be executed via `UiRobot`. Ensure the project is compiled into a `.nupkg` since it's a Portable framework project.

```bash
"C:\Users\Administrateur\AppData\Local\Programs\UiPathPlatform\Studio\26.0.196-cloud.23786\UiRobot.exe" execute --file "C:\DEVPOST.Hackathon\UiPath AgentHack\UiPath\Orchestrateur_Final\pkg\Orchestrateur_Final.1.0.0.nupkg"
```

## 🧹 Housekeeping
A `/rollback` endpoint is provided as a "Red Button" to instantly kill and wipe any lingering Docker containers and reset the `workspace_agents` folder in case of a critical failure.
