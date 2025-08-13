# DSPy Human-in-the-Loop ReAct Agent

A demonstration of how to integrate human feedback and decision-making into automated [DSPy](https://github.com/stanfordnlp/dspy) ReAct agent workflows. This system allows AI agents to pause execution and request human input when they need clarification, approval, or additional context.

It might be simplest to start with the [blog post](https://joelgrus.com/2025/08/13/vibe-coding-7-human-in-the-loop-as-a-dspytool/).


## Demo: Pizza Ordering Agent

The included demo features a pizza ordering agent that:
- Takes natural language requests like "I want two large pizzas"
- Asks clarifying questions about toppings, sizes, and special instructions
- Builds structured order data through human interaction
- Works in both console and web interfaces

## Features

- **Seamless Integration**: Drop-in DSPy Tool that agents can use naturally
- **Multiple Interfaces**: Console (terminal) and web (browser) implementations
- **Real-time Communication**: Server-Sent Events (SSE) for live web updates
- **Concurrent Support**: Multiple browser tabs can connect simultaneously
- **Type Safety**: Full TypeScript-style typing with TypedDict
- **Production Ready**: Clean architecture with proper error handling

## Architecture

### Core Components

- **`human_in_the_loop.py`**: Core infrastructure using asyncio for coordination
- **`pizza_agent.py`**: DSPy signatures and types for the demo
- **`console_app.py`**: Terminal-based interface
- **`web_app.py`**: FastAPI web server with SSE streaming
- **`main.py`**: Usage instructions and entry point

### Design Pattern

The system uses a **Requester Pattern** where different transport mechanisms (console, web) implement the same async interface:

```python
# Create a human-input tool for any transport
tool = human_in_the_loop(requester_function)

# Use in DSPy ReAct agent
agent = dspy.ReAct(
    signature=OrderPizza,
    tools=[tool],
    max_iters=6
)
```

### Request Flow

1. **Agent asks question** - Creates `HumanInputRequest`
2. **Requester handles transport** - Console input() or web queue
3. **Human provides response** - Through terminal or browser
4. **Response delivered back** - Agent continues execution

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- OpenRouter API key (or other LLM provider)

### Installation

```bash
git clone <repository-url>
cd dspy-react-hitl
uv sync
```

### Configuration

Set your LLM provider credentials. The demo uses OpenRouter with Gemini 2.5 Flash:

```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

Or modify the LM configuration in the demo files:

```python
lm = dspy.LM('openrouter/google/gemini-2.5-flash')
# or use other providers like:
# lm = dspy.LM('openai/gpt-4')
# lm = dspy.LM('anthropic/claude-3-sonnet-20240229')
```

## Running the Demos

### Console Demo

Interactive terminal-based interface:

```bash
uv run python console_app.py
```

Example interaction:
```
DSPy Human-in-the-Loop Pizza Agent (Console Version)

What is your order?
> I want a large pizza

Agent is thinking about: 'I want a large pizza'

What toppings would you like on your large pizza?
> pepperoni and mushrooms

Your order:
  1. large pizza with pepperoni, mushrooms
```

### Web Demo

Browser-based interface with real-time updates:

```bash
uv run python web_app.py
```

Then open http://localhost:8000 in your browser.

Features:
- Pizza favicon
- Real-time question/response flow
- Multiple browser tabs supported
- Mobile-friendly responsive design
- Activity logging

## Integration Guide

### Basic Usage

```python
import dspy
from human_in_the_loop import human_in_the_loop, console_requester

# Create the tool
human_input = human_in_the_loop(console_requester)

# Use in any DSPy agent
agent = dspy.ReAct(
    signature=YourSignature,
    tools=[human_input, other_tools...],
    max_iters=10
)

# Agent can now ask humans questions
result = await agent.aforward(your_input="...")
```

### Custom Requesters

Implement your own transport mechanism:

```python
async def slack_requester(request: HumanInputRequest):
    # Send question to Slack
    await slack_client.send_message(request.question)
    
    # Set up webhook handler to call:
    # request.set_response(user_response)

async def email_requester(request: HumanInputRequest):
    # Send email with question
    # Set up email parser to call:
    # request.set_response(user_response)
```

### Custom Signatures

Define your own agent signatures:

```python
class CustomerSupport(dspy.Signature):
    """Agent that handles customer inquiries with human escalation"""
    customer_message = dspy.InputField()
    response: str = dspy.OutputField()
    escalated: bool = dspy.OutputField()

agent = dspy.ReAct(
    signature=CustomerSupport,
    tools=[human_in_the_loop(your_requester)],
    max_iters=8
)
```

## Testing

The system includes both unit-testable components and integration demos:

```bash
# Test console version
echo "medium pizza" | uv run python console_app.py

# Test web version
uv run python web_app.py
# Then visit http://localhost:8000
```

## Production Considerations

### Scalability

- **Current**: In-memory queues, single-server
- **Production**: Consider Redis pub/sub, database persistence, load balancing

### Security

- **Authentication**: Add user authentication for web interface
- **Rate Limiting**: Prevent abuse of human input requests
- **Input Validation**: Sanitize all human responses

### Monitoring

- **Metrics**: Track response times, abandonment rates
- **Logging**: Log all human interactions for audit
- **Alerting**: Monitor for stuck requests

## Technical Details

### Async Coordination

The system uses `asyncio.Future` for coordination between agent execution and human response:

```python
class HumanInputRequest:
    def __init__(self, question: str):
        self._response_future = asyncio.Future()
    
    async def response(self) -> str:
        return await self._response_future  # Blocks until response
    
    def set_response(self, response: str):
        self._response_future.set_result(response)  # Unblocks waiting agent
```

### Web Architecture

- **FastAPI**: Modern async web framework
- **Server-Sent Events**: Real-time updates without WebSocket complexity  
- **Broadcast Pattern**: Each browser tab gets its own event queue
- **Graceful Cleanup**: Proper handling of client disconnections

### Error Handling

- **Timeouts**: Removed to allow unlimited human response time
- **Network Issues**: Automatic SSE reconnection
- **Validation**: Type-safe request/response handling
- **Graceful Degradation**: Fallback behaviors for edge cases

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [DSPy](https://github.com/stanfordnlp/dspy) for the excellent framework
- [FastAPI](https://fastapi.tiangolo.com/) for the web infrastructure  
- The human-in-the-loop pattern inspiration from interactive ML systems

## Related Work

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Human-in-the-Loop Machine Learning](https://www.manning.com/books/human-in-the-loop-machine-learning)
- [ReAct: Reasoning and Acting with Language Models](https://arxiv.org/abs/2210.03629)