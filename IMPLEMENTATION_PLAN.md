# Human-in-the-Loop Guide for DSPy ReAct Agents

## Overview

### Goal
Enable DSPy ReAct agents to pause execution and request human input during their reasoning loop, supporting both console and web applications without blocking the event loop or losing agent state.

### Key Challenges
- ReAct agents run in a synchronous loop by default
- Human input is inherently asynchronous (could take seconds to hours)
- Different environments (console vs web) require different interaction patterns
- Need to maintain agent state while waiting for human response

### Solution Architecture
Use dependency injection with an `InputProvider` protocol that abstracts the human interaction mechanism, allowing the same agent code to work across different environments.

## Core Design: InputProvider Protocol

```python
from typing import Protocol
import asyncio

class InputProvider(Protocol):
    """Protocol for different human input mechanisms"""
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        """Request input from a human"""
        ...
    
    def provide_response(self, request_id: str, response: str) -> None:
        """Callback for async providers to receive human response"""
        ...
```

## Implementation Patterns

### 1. Console Application Provider

Simple synchronous input for command-line applications:

```python
class ConsoleInputProvider:
    """Simple console-based input provider"""
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        # For async compatibility, but actually synchronous
        return input(f"\n🤔 {question}\n> ")
    
    def provide_response(self, request_id: str, response: str) -> None:
        # Not needed for console - input() blocks until response
        pass
```

### 2. Web Application Provider (SSE + POST)

Asynchronous provider for web applications using Server-Sent Events:

```python
import uuid
import asyncio
from typing import Dict

class SSEInputProvider:
    """Web-based input provider using Server-Sent Events"""
    
    def __init__(self):
        self.pending_requests: Dict[str, dict] = {}
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        
        self.pending_requests[request_id] = {
            'future': future,
            'question': question,
            'metadata': metadata or {},
            'sent': False  # Track if we've sent this to client
        }
        
        # This will block until provide_response is called
        try:
            response = await future
            return response
        finally:
            # Cleanup
            self.pending_requests.pop(request_id, None)
    
    def provide_response(self, request_id: str, response: str) -> None:
        """Called when human provides input via web interface"""
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]['future']
            # Thread-safe way to set result
            loop = future.get_loop()
            loop.call_soon_threadsafe(future.set_result, response)
    
    def get_pending_requests(self):
        """Get unsent requests for SSE stream"""
        pending = []
        for request_id, data in self.pending_requests.items():
            if not data.get('sent'):
                pending.append({
                    'id': request_id,
                    'question': data['question'],
                    'metadata': data['metadata']
                })
                data['sent'] = True
        return pending
```

### 3. Creating the DSPy Tool

Use closures to inject the provider into the tool:

```python
import dspy

def create_human_input_tool(provider: InputProvider):
    """Factory function that creates a DSPy tool with the given provider"""
    
    async def ask_human(question: str) -> str:
        """Ask a human for clarification, additional information, or approval.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's response as a string
        """
        return await provider.get_input(question)
    
    # Create the DSPy tool
    return dspy.Tool(ask_human)
```

## Complete Examples

### Console Application

```python
import asyncio
import dspy

def create_console_agent():
    # Create provider and tool
    provider = ConsoleInputProvider()
    human_tool = create_human_input_tool(provider)
    
    # Set up agent
    agent = dspy.ReAct(signature="question -> answer")
    agent.tools = [human_tool]  # Plus other tools as needed
    
    return agent

async def main():
    agent = create_console_agent()
    
    # Run the agent
    question = "What should I cook for dinner?"
    result = await agent.aforward(question=question)
    print(f"\nFinal answer: {result.answer}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Web Application (FastAPI)

#### Backend Implementation

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
import asyncio
import json
import dspy

app = FastAPI()

# Global provider instance (in production, use dependency injection)
provider = SSEInputProvider()

# Create the agent with human input capability
human_tool = create_human_input_tool(provider)
agent = dspy.ReAct(signature="question -> answer")
agent.tools = [human_tool]

class AgentRequest(BaseModel):
    question: str

class HumanResponse(BaseModel):
    request_id: str
    response: str

@app.post("/agent/start")
async def start_agent(request: AgentRequest):
    """Start an agent task that might require human input"""
    
    async def run_agent():
        try:
            result = await agent.aforward(question=request.question)
            return {"status": "complete", "answer": result.answer}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # Start the agent task in the background
    task = asyncio.create_task(run_agent())
    
    # Store task if you need to track it
    # app.state.tasks[task_id] = task
    
    return {"status": "started", "message": "Agent is running"}

@app.get("/events")
async def event_stream(request: Request):
    """SSE endpoint that pushes requests for human input to the client"""
    
    async def generate():
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break
            
            # Get any pending requests
            pending = provider.get_pending_requests()
            for req in pending:
                # Format as SSE
                data = json.dumps(req)
                yield f"data: {data}\n\n"
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )

@app.post("/respond")
async def provide_human_response(response: HumanResponse):
    """Endpoint for submitting human responses"""
    provider.provide_response(response.request_id, response.response)
    return {"status": "received"}

@app.get("/")
async def index():
    """Serve the demo UI"""
    return HTMLResponse(content=demo_html)

# Demo HTML interface
demo_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Human-in-the-Loop Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .request { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .question { font-weight: bold; margin-bottom: 10px; }
        input { width: 70%; padding: 5px; }
        button { padding: 5px 15px; margin-left: 10px; }
        #log { background: #e0e0e0; padding: 10px; height: 200px; overflow-y: auto; }
    </style>
</head>
<body>
    <h1>Human-in-the-Loop Agent Demo</h1>
    
    <div>
        <h2>Start Agent</h2>
        <input type="text" id="question" placeholder="Ask the agent something..." />
        <button onclick="startAgent()">Start</button>
    </div>
    
    <div id="requests"></div>
    
    <div>
        <h3>Log</h3>
        <div id="log"></div>
    </div>
    
    <script>
        let eventSource = null;
        
        function log(message) {
            const logDiv = document.getElementById('log');
            logDiv.innerHTML += `${new Date().toLocaleTimeString()}: ${message}<br>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function startAgent() {
            const question = document.getElementById('question').value;
            
            fetch('/agent/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question: question})
            })
            .then(r => r.json())
            .then(data => log(`Agent started: ${data.message}`));
            
            // Start listening for events if not already
            if (!eventSource) {
                startSSE();
            }
        }
        
        function startSSE() {
            eventSource = new EventSource('/events');
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                log(`Agent needs input: ${data.question}`);
                showRequest(data);
            };
            
            eventSource.onerror = function(error) {
                log('SSE error - reconnecting...');
            };
        }
        
        function showRequest(data) {
            const div = document.createElement('div');
            div.className = 'request';
            div.innerHTML = `
                <div class="question">${data.question}</div>
                <input type="text" id="response-${data.id}" placeholder="Your response..." />
                <button onclick="respond('${data.id}')">Send</button>
            `;
            document.getElementById('requests').appendChild(div);
        }
        
        function respond(requestId) {
            const response = document.getElementById(`response-${requestId}`).value;
            
            fetch('/respond', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    request_id: requestId,
                    response: response
                })
            })
            .then(r => r.json())
            .then(data => {
                log(`Response sent: ${response}`);
                // Remove the request div
                document.querySelector(`#response-${requestId}`).parentElement.remove();
            });
        }
        
        // Start SSE on page load
        window.onload = function() {
            startSSE();
        };
    </script>
</body>
</html>
"""
```

## Production Considerations

### 1. State Management

For production web applications, consider storing agent state in Redis or a database:

```python
import pickle
import redis

class PersistentSSEProvider(SSEInputProvider):
    def __init__(self, redis_client: redis.Redis):
        super().__init__()
        self.redis = redis_client
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        request_id = str(uuid.uuid4())
        
        # Store in Redis instead of memory
        self.redis.setex(
            f"request:{request_id}",
            3600,  # 1 hour TTL
            pickle.dumps({
                'question': question,
                'metadata': metadata,
                'status': 'pending'
            })
        )
        
        # Poll Redis for response
        while True:
            data = self.redis.get(f"request:{request_id}")
            if data:
                request_data = pickle.loads(data)
                if request_data.get('status') == 'answered':
                    return request_data['response']
            await asyncio.sleep(0.5)
```

### 2. Timeout Handling

Add timeouts to prevent indefinite waiting:

```python
class TimeoutInputProvider:
    def __init__(self, provider: InputProvider, timeout: float = 300.0):
        self.provider = provider
        self.timeout = timeout
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        try:
            return await asyncio.wait_for(
                self.provider.get_input(question, metadata),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            return "No response received (timeout)"
```

### 3. Error Recovery

Implement retry logic and fallback responses:

```python
class RobustInputProvider:
    def __init__(self, provider: InputProvider, max_retries: int = 3):
        self.provider = provider
        self.max_retries = max_retries
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        for attempt in range(self.max_retries):
            try:
                return await self.provider.get_input(question, metadata)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return f"Failed to get human input: {e}"
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 4. Authentication & Security

Add authentication to prevent unauthorized responses:

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    # Verify token logic here
    if not is_valid_token(token):
        raise HTTPException(status_code=403, detail="Invalid token")
    return token

@app.post("/respond")
async def provide_human_response(
    response: HumanResponse,
    token: str = Depends(verify_token)
):
    # Only authenticated users can provide responses
    provider.provide_response(response.request_id, response.response)
    return {"status": "received"}
```

### 5. Scaling Considerations

For multiple concurrent agents:

```python
class MultiAgentProvider:
    def __init__(self):
        self.providers = {}  # agent_id -> provider
    
    def get_provider_for_agent(self, agent_id: str) -> InputProvider:
        if agent_id not in self.providers:
            self.providers[agent_id] = SSEInputProvider()
        return self.providers[agent_id]
    
    def cleanup_agent(self, agent_id: str):
        """Clean up when agent completes"""
        self.providers.pop(agent_id, None)
```

## Testing

### Unit Testing the Provider

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_console_provider():
    provider = ConsoleInputProvider()
    # Mock input() for testing
    with patch('builtins.input', return_value='test response'):
        response = await provider.get_input("Test question?")
        assert response == 'test response'

@pytest.mark.asyncio
async def test_sse_provider():
    provider = SSEInputProvider()
    
    # Simulate async request/response
    async def request():
        return await provider.get_input("Test question?")
    
    async def respond():
        await asyncio.sleep(0.1)  # Small delay
        pending = provider.get_pending_requests()
        assert len(pending) == 1
        provider.provide_response(pending[0]['id'], 'test response')
    
    request_task = asyncio.create_task(request())
    respond_task = asyncio.create_task(respond())
    
    response = await request_task
    assert response == 'test response'
```

### Integration Testing

```python
from fastapi.testclient import TestClient

def test_human_input_flow():
    client = TestClient(app)
    
    # Start agent
    response = client.post("/agent/start", json={"question": "Test"})
    assert response.status_code == 200
    
    # Get events (would need async client for real SSE testing)
    # ...
    
    # Provide response
    response = client.post("/respond", json={
        "request_id": "test-id",
        "response": "test response"
    })
    assert response.status_code == 200
```

## Deployment Checklist

- [ ] **Environment Configuration**: Set up environment variables for provider selection
- [ ] **Logging**: Add comprehensive logging for debugging async flows
- [ ] **Monitoring**: Track metrics like response times and timeout rates
- [ ] **Error Handling**: Implement proper error boundaries and fallbacks
- [ ] **Security**: Add authentication and validate all inputs
- [ ] **Scaling**: Use Redis/database for state in multi-instance deployments
- [ ] **Testing**: Unit and integration tests for all providers
- [ ] **Documentation**: API documentation for frontend developers
- [ ] **Rate Limiting**: Prevent abuse of human input requests
- [ ] **Cleanup**: Implement proper cleanup for abandoned requests

## Common Pitfalls and Solutions

| Pitfall | Solution |
|---------|----------|
| Agent blocks forever waiting for input | Add timeouts with `asyncio.wait_for()` |
| Lost requests on server restart | Persist state to Redis/database |
| Multiple responses to same request | Use request IDs and track processed requests |
| SSE connection drops | Client auto-reconnect + server-side heartbeat |
| Memory leaks from pending requests | Implement TTL and cleanup old requests |
| Race conditions in web handler | Use thread-safe operations (`call_soon_threadsafe`) |

## Next Steps

1. **Extend providers**: Add Slack, Discord, or email providers
2. **Add context**: Include agent's reasoning chain with requests
3. **Batch requests**: Allow multiple questions at once
4. **Add priorities**: Urgent vs non-urgent human input
5. **Create UI library**: Reusable React/Vue components for human input
6. **Add approval workflows**: Multiple humans for critical decisions
7. **Implement audit trail**: Log all human interactions for compliance
