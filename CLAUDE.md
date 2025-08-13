# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a DSPy-based project implementing human-in-the-loop functionality for ReAct agents. The project allows DSPy agents to pause execution and request human input during their reasoning loop, supporting both console and web applications without blocking the event loop.

## Dependencies and Environment

- **Python**: Requires Python >=3.11
- **Package Manager**: Uses `uv` for dependency management (evidenced by uv.lock file)
- **Key Dependencies**:
  - `dspy>=2.6.27` - Core DSPy framework for building LLM applications
  - `fastapi>=0.116.1` - For web application components

## Development Commands

```bash
# Install dependencies
uv sync

# Run the main application
uv run python main.py

# Run any Python script
uv run python <script_name>.py

# Add new dependencies
uv add <package_name>

# Add development dependencies
uv add --dev <package_name>

# Remove dependencies
uv remove <package_name>

# Update dependencies
uv lock --upgrade

# Run tests (when implemented)
uv run pytest

# Format code (when formatter is added)
uv run black .
uv run ruff format .

# Lint code (when linter is added)
uv run ruff check .
```

## Architecture Overview

The project implements a protocol-based architecture using dependency injection:

### Core Design Pattern: InputProvider Protocol
- Uses an `InputProvider` protocol to abstract human interaction mechanisms
- Allows the same agent code to work across different environments (console vs web)
- Supports both synchronous (console) and asynchronous (web) input patterns

### Key Components
1. **InputProvider Protocol** - Abstract interface for human input mechanisms
2. **ConsoleInputProvider** - Simple synchronous input for command-line applications  
3. **SSEInputProvider** - Asynchronous provider for web apps using Server-Sent Events
4. **DSPy Tool Factory** - Creates DSPy tools with injected providers using closures

### Web Application Architecture
- FastAPI backend with SSE (Server-Sent Events) for real-time communication
- Asynchronous request/response pattern using futures and callbacks
- Built-in HTML demo interface for testing human-in-the-loop interactions

## Current State

Core functionality is implemented and ready for testing:
- `main.py` provides usage instructions for both demo modes
- Complete implementation following the plan in `IMPLEMENTATION_PLAN.md`
- Two working demos: console-based and web-based interfaces
- Pizza ordering agent that demonstrates human-in-the-loop interactions

## Implementation Notes

- Uses asyncio for async compatibility even in synchronous contexts
- Thread-safe operations for web providers using `call_soon_threadsafe`
- Request tracking with UUIDs and cleanup mechanisms
- Designed for production with considerations for state management, timeouts, and error recovery