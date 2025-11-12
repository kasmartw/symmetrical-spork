# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains two main LangGraph-based agent projects:

1. **Appointment Booking Agent** (`agent-appoiments/`) - A production-ready conversational AI agent for booking appointments
2. **LangGraph Template** (`path/example/`) - A starter template for building LangGraph agents

## Appointment Booking Agent (`agent-appoiments/`)

### Design Specification

**IMPORTANT:** Read `agent-appoiments/instruction_and_logic.md` for the complete logical specification. This document defines:
- State machine logic and conversation flow
- Why the system asks one question at a time
- Validation rules and error handling patterns
- The mandatory summary format before confirmation
- Business-agnostic design philosophy

The specification explains the "why" behind implementation decisions in `agent.py`.

### Running the Application

The appointment booking agent requires two processes running simultaneously:

1. **Start the Mock API Server** (Terminal 1):
   ```bash
   cd agent-appoiments
   python mock_api.py
   ```
   Server runs on `http://localhost:5000`

2. **Run the Agent** (Terminal 2):
   ```bash
   cd agent-appoiments
   python agent.py
   ```

### Testing
```bash
cd agent-appoiments
python test_agent.py
```

### Architecture

The agent uses a **tool-based architecture** with LangGraph orchestration:

- **Agent Core** (`agent.py`): Contains the LangGraph StateGraph with two nodes:
  - `agent`: LLM node that decides which tools to call
  - `tools`: ToolNode that executes selected tools

- **Conversation Flow**: The agent operates with a conditional edge pattern:
  1. User input → agent node
  2. Agent decides: call tools OR end conversation
  3. If tools → execute tools → return to agent node
  4. Agent generates response → back to user

- **State Management**: Uses `AgentState` TypedDict with:
  - `messages`: Annotated sequence with `add_messages` for message history
  - `context`: Dict for maintaining booking context across conversation

### Available Tools

Tools are decorated with `@tool` and bound to the LLM:

1. `get_services()` - Fetches available services from API
2. `get_availability(service_id, date_from)` - Gets time slots
3. `create_appointment(...)` - Creates booking with validation
4. `validate_email(email)` - Regex validation for email
5. `validate_phone(phone)` - Validates phone has ≥7 digits

### Configuration

All business logic is centralized in `config.py`:
- `SERVICES`: List of available services with durations
- `ASSIGNED_PERSON`: Provider information
- `LOCATION`: Office details
- `OPERATING_HOURS`: Business hours and slot duration
- `MOCK_API_BASE_URL` and `MOCK_API_PORT`: API configuration

### Mock API (`mock_api.py`)

Flask-based REST API with in-memory storage:

**Endpoints:**
- `GET /services` - List services
- `GET /availability?service_id=X&date_from=YYYY-MM-DD` - Available slots
- `POST /appointments` - Create appointment
- `GET /health` - Health check

**Important:** Mock API generates time slots dynamically for the next 7 days based on `OPERATING_HOURS` in `config.py`. Data resets on server restart.

### System Prompt Pattern

The agent uses a detailed system prompt (`SYSTEM_PROMPT` in `agent.py`) that defines:
- Personality and tone (friendly, uses emojis moderately)
- Step-by-step conversation flow (11 steps from greeting to confirmation)
- Summary format for appointment confirmation
- Important rules (ask one question at a time, validate before creating)
- Available tools and when to use them

This pattern ensures consistent behavior and guides the LLM through the booking flow.

## LangGraph Template (`path/example/`)

### Running the Template

This project uses **LangGraph CLI** for development:

```bash
cd path/example
pip install -e . "langgraph-cli[inmem]"
langgraph dev
```

This starts LangGraph Server and opens LangGraph Studio for visual debugging.

### Testing

```bash
# Run all tests
make test

# Run integration tests only
make integration_tests

# Run specific test file
make test TEST_FILE=tests/unit_tests/test_configuration.py
```

### Code Quality

```bash
# Format code
make format

# Run linters (ruff + mypy)
make lint
```

### Architecture

The template demonstrates a **minimal single-node graph**:

- **State** (`State` dataclass): Input structure for the graph
- **Context** (`Context` TypedDict): Runtime configuration parameters
- **Node** (`call_model`): Async function that processes state + runtime context
- **Graph**: Compiled StateGraph with context schema

**Key Pattern:** Runtime context allows configuring assistants without code changes. Access via `runtime.context` in node functions.

### Graph Definition (`src/agent/graph.py`)

The graph is defined declaratively:
```python
graph = (
    StateGraph(State, context_schema=Context)
    .add_node(call_model)
    .add_edge("__start__", "call_model")
    .compile(name="New Graph")
)
```

This pattern is the foundation for building more complex multi-node workflows.

### LangGraph Configuration (`langgraph.json`)

- `dependencies`: Points to project root for pip install
- `graphs`: Maps graph names to module paths (e.g., `"agent": "./src/agent/graph.py:graph"`)
- `env`: Environment file location
- `image_distro`: Container distribution (wolfi)

## Environment Variables

Both projects require a `.env` file. Create from `.env.example`:

**Required:**
- `OPENAI_API_KEY` - OpenAI API key for LLM access

**Optional (LangSmith tracing):**
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_ENDPOINT=https://api.smith.langchain.com`
- `LANGCHAIN_API_KEY` - LangSmith API key
- `LANGCHAIN_PROJECT` - Project name for tracing

## Key Dependencies

- **langgraph** - Agent orchestration framework
- **langchain** & **langchain-openai** - LLM framework and OpenAI integration
- **flask** & **flask-cors** - Mock API server (appointment agent only)
- **python-dotenv** - Environment variable management
- **requests** - HTTP client for API calls

## Important Patterns

### LangGraph State Management
Both projects use `add_messages` reducer for message history, which automatically appends new messages to the sequence while handling duplicates by message ID.

### Tool Execution Flow
In the appointment agent, tools return structured strings/JSON that the LLM processes. The `ToolNode` handles serialization automatically. Tool validation happens before business logic (e.g., validate email/phone before create_appointment).

### Conditional Edges
The appointment agent uses `should_continue()` to route between agent and tools based on `tool_calls` attribute in the last message. This is the standard pattern for tool-using agents.

### Error Handling
Both projects use try/except blocks in tools/nodes to catch API failures and return friendly error messages instead of raising exceptions, keeping the conversation flow intact.
