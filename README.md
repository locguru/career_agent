# Native MCP Client-Server Agent for Gmail Orchestration

A lightweight, production-grade implementation of the **Model Context Protocol (MCP)** built entirely from scratch in Python. This project demonstrates how to orchestrate a true Client-Server-AI execution loop over standard input/output (`stdio`) channels using raw JSON-RPC 2.0 communication pipelines—bypassing heavy third-party framework wrappers.

The agent securely spawns a local data server as an isolated background subprocess, executes a dynamic capability discovery handshake, maps schemas natively into the Google GenAI SDK, and uses **Gemini 2.0/2.5 Flash** to drive intelligent tool execution over a user's private Gmail repository.

---

## 🏗️ Architecture Overview

Unlike traditional web-hook-based plugin architectures that require public HTTP endpoints, this system relies on a local **Client-Server-DataSource** model using standard memory pipes:

              ┌──────────────────────────────────────────────┐
              │                 MCP CLIENT                   │
              │  (Manages state, maps protocol schemas,     │
              │   and orchestrates LLM context windows)      │
              └───────────────▲───────────────┬──────────────┘
                              │               │
                 JSON-RPC 2.0 │               │ JSON-RPC 2.0
                 stdout pipe  │               │ stdin pipe
                              │               │
              ┌───────────────┴───────────────▼──────────────┐
              │                 MCP SERVER                   │
              │  (Isolated subprocess tracking local data,   │
              │   authentication tokens, & systems logic)    │
              └───────────────────────▲──────────────────────┘
                                      │  Google API Core
                                      ▼
                               [ Gmail Secure API ]

## The Execution Loop:
1. **Handshake & Discovery:** The Client spawns the Server process and sends a `tools/list` request. The Server responds with its operational tool manifest.
2. **Intent Framing:** The Client registers the dynamic manifest schemas into the Gemini SDK and prompts the model with an executive task.
3. **Execution Routing:** Gemini evaluates the task, intercepts the tool layout, and returns a structural `function_call` intent. 
4. **Context Injection:** The Client intercepts that intent, wraps it into an MCP-compliant `tools/call` JSON-RPC message, pushes it down the Server's stdin pipe, reads the single-line execution result from stdout, and passes the raw text payload back to Gemini to render a finalized markdown report.

---

## ⚙️ Project Structure

* `main_agent_client.py` - The orchestrator client. Handles process isolation (`subprocess.Popen`), standard stream reading, model tool specification translating, and prompt routing.
* `career_mcp_server.py` - The protocol-compliant server loop. Manages OAuth2 tokens, executes iterative text parsers, and hosts the JSON-RPC message listener over `sys.stdin`.
* `requirements.txt` - Minimum dependencies required to host the runtime.

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have a modern Python environment and the required client frameworks:
```bash
python3 -m pip install google-genai google-api-python-client google-auth-oauthlib