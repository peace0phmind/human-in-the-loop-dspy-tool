"""
DSPy Human-in-the-Loop ReAct Agent Demo

Run this file to see usage instructions for both console and web interfaces.
"""
import sys


def main():
    print("🍕 DSPy Human-in-the-Loop ReAct Agent")
    print("=" * 40)
    print()
    print("This project demonstrates how to create DSPy ReAct agents that can")
    print("pause execution and request human input during their reasoning loop.")
    print()
    print("📋 Available demos:")
    print()
    print("1. Console Demo (terminal-based interaction):")
    print("   uv run python console_demo.py")
    print()
    print("2. Web Demo (browser-based interface):")
    print("   uv run python web_app.py")
    print("   Then open: http://localhost:8000")
    print()
    print("🔧 Setup Notes:")
    print("- You'll need to configure DSPy with an LLM model")
    print("- See DSPy documentation for configuration options")
    print("- The demos use a pizza ordering scenario to demonstrate human input")
    print()
    print("📁 Key files:")
    print("- input_provider.py: Core InputProvider protocol and implementations")
    print("- agent.py: DSPy ReAct agent setup with human input tools")
    print("- console_demo.py: Terminal-based demo")
    print("- web_app.py: FastAPI web interface with SSE")
    print()


if __name__ == "__main__":
    main()
