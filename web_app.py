"""
FastAPI web interface for human-in-the-loop DSPy agents.
"""
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
import asyncio
import json
import dspy
from input_provider import SSEInputProvider
from agent import create_pizza_agent

app = FastAPI(title="DSPy Human-in-the-Loop Demo")

# Global provider instance (in production, use dependency injection)
provider = SSEInputProvider()

# Create the agent with human input capability
agent = create_pizza_agent(provider)

# Track running tasks and their results
running_tasks = {}
task_results = {}

class AgentRequest(BaseModel):
    question: str

class HumanResponse(BaseModel):
    request_id: str
    response: str

@app.post("/agent/start")
async def start_agent(request: AgentRequest):
    """Start an agent task that might require human input"""
    
    import uuid
    task_id = str(uuid.uuid4())
    
    async def run_agent():
        try:
            result = await agent.aforward(question=request.question)
            task_results[task_id] = {"status": "complete", "answer": result.answer}
        except Exception as e:
            task_results[task_id] = {"status": "error", "error": str(e)}
        finally:
            # Clean up from running tasks
            running_tasks.pop(task_id, None)
    
    # Start the agent task in the background
    task = asyncio.create_task(run_agent())
    running_tasks[task_id] = task
    
    return {"status": "started", "message": "Agent is running", "task_id": task_id}

@app.get("/events")
async def event_stream(request: Request):
    """SSE endpoint that pushes requests for human input and task results to the client"""
    
    sent_results = set()
    
    async def generate():
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break
            
            # Get any pending human input requests
            pending = provider.get_pending_requests()
            for req in pending:
                # Format as SSE for human input
                data = json.dumps({"type": "human_input", **req})
                yield f"data: {data}\n\n"
            
            # Check for completed tasks
            for task_id, result in task_results.items():
                if task_id not in sent_results:
                    # Format as SSE for task completion
                    data = json.dumps({"type": "task_result", "task_id": task_id, **result})
                    yield f"data: {data}\n\n"
                    sent_results.add(task_id)
            
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
    <title>DSPy Human-in-the-Loop Demo</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
            background-color: #f5f5f5; 
        }
        .container { 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
        }
        .request { 
            background: #e3f2fd; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 5px; 
            border-left: 4px solid #2196f3; 
        }
        .request.answered { 
            background: #f3e5f5; 
            border-left: 4px solid #9c27b0; 
        }
        .response-display {
            margin-top: 10px;
            padding: 8px;
            background: #fff3e0;
            border-radius: 4px;
            font-style: italic;
        }
        .question { 
            font-weight: bold; 
            margin-bottom: 10px; 
            color: #1976d2; 
        }
        input[type="text"] { 
            width: 70%; 
            padding: 8px; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            font-size: 14px; 
        }
        button { 
            padding: 8px 15px; 
            margin-left: 10px; 
            background: #2196f3; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
        }
        button:hover { background: #1976d2; }
        #log { 
            background: #f8f9fa; 
            padding: 15px; 
            height: 200px; 
            overflow-y: auto; 
            border: 1px solid #e9ecef; 
            border-radius: 4px; 
            font-family: monospace; 
            font-size: 12px; 
        }
        h1 { color: #333; }
        h2, h3 { color: #555; }
        .start-section { margin-bottom: 30px; }
        #question { width: 60%; }
        .final-answer { 
            background: #e8f5e8; 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 8px; 
            border-left: 4px solid #4caf50; 
            font-size: 16px;
        }
        .final-answer h3 { 
            color: #2e7d32; 
            margin-top: 0; 
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍕 DSPy Human-in-the-Loop Pizza Agent</h1>
        
        <div class="start-section">
            <h2>Ask the Pizza Agent</h2>
            <p>The agent will help you order pizza by asking for your preferences!</p>
            <input type="text" id="question" placeholder="I want to order a pizza..." />
            <button onclick="startAgent()">Start Agent</button>
        </div>
        
        <div id="requests"></div>
        
        <div>
            <h3>Activity Log</h3>
            <div id="log"></div>
        </div>
    </div>
    
    <script>
        let eventSource = null;
        
        function log(message) {
            const logDiv = document.getElementById('log');
            const timestamp = new Date().toLocaleTimeString();
            logDiv.innerHTML += `[${timestamp}] ${message}<br>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function startAgent() {
            const questionInput = document.getElementById('question');
            const question = questionInput.value;
            if (!question.trim()) {
                log('Please enter a question first!');
                return;
            }
            
            // Clear previous results and requests
            document.querySelectorAll('.final-answer').forEach(el => el.remove());
            document.querySelectorAll('.request').forEach(el => el.remove());
            
            // Disable the input and switch to "New Order" workflow immediately
            const startButton = document.querySelector('.start-section button');
            questionInput.disabled = true;
            questionInput.readOnly = true;
            startButton.textContent = 'New Order';
            startButton.onclick = newOrder;
            startButton.disabled = false;
            
            fetch('/agent/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question: question})
            })
            .then(r => r.json())
            .then(data => {
                log(`🤖 Agent started: ${data.message}`);
                // Don't clear the question - keep it visible
            })
            .catch(error => {
                log(`❌ Error starting agent: ${error}`);
                // Reset to initial state on error
                const startButton = document.querySelector('.start-section button');
                questionInput.disabled = false;
                questionInput.readOnly = false;
                startButton.textContent = 'Start Agent';
                startButton.onclick = startAgent;
                startButton.disabled = false;
            });
            
            // Start listening for events if not already
            if (!eventSource) {
                startSSE();
            }
        }
        
        function newOrder() {
            // Reset everything to initial state
            const questionInput = document.getElementById('question');
            const startButton = document.querySelector('.start-section button');
            
            // Clear all previous content
            document.querySelectorAll('.final-answer').forEach(el => el.remove());
            document.querySelectorAll('.request').forEach(el => el.remove());
            
            // Reset input and button
            questionInput.value = '';
            questionInput.disabled = false;
            questionInput.readOnly = false;
            startButton.textContent = 'Start Agent';
            startButton.onclick = startAgent;
            startButton.disabled = false;
            
            // Focus on input for new question
            questionInput.focus();
            
            log('🔄 Ready for new order!');
        }
        
        function startSSE() {
            eventSource = new EventSource('/events');
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'human_input') {
                    log(`🤔 Agent needs input: "${data.question}"`);
                    showRequest(data);
                } else if (data.type === 'task_result') {
                    if (data.status === 'complete') {
                        log(`🎉 Agent completed! Final answer: "${data.answer}"`);
                        showFinalAnswer(data.answer);
                        // New Order workflow already set up when agent started
                    } else if (data.status === 'error') {
                        log(`❌ Agent error: ${data.error}`);
                        // Reset to initial state on error
                        const questionInput = document.getElementById('question');
                        const startButton = document.querySelector('.start-section button');
                        questionInput.disabled = false;
                        questionInput.readOnly = false;
                        startButton.textContent = 'Start Agent';
                        startButton.onclick = startAgent;
                        startButton.disabled = false;
                    }
                }
            };
            
            eventSource.onerror = function(error) {
                log('🔄 SSE connection error - will reconnect...');
            };
            
            log('🔗 Connected to agent events');
        }
        
        function showRequest(data) {
            const div = document.createElement('div');
            div.className = 'request';
            div.innerHTML = `
                <div class="question">❓ ${data.question}</div>
                <input type="text" id="response-${data.id}" placeholder="Your response..." />
                <button onclick="respond('${data.id}')">Send Response</button>
            `;
            document.getElementById('requests').appendChild(div);
            
            // Focus on the input field
            document.getElementById(`response-${data.id}`).focus();
        }
        
        function respond(requestId) {
            const responseInput = document.getElementById(`response-${requestId}`);
            const response = responseInput.value.trim();
            
            if (!response) {
                log('❌ Please enter a response');
                return;
            }
            
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
                log(`✅ Response sent: "${response}"`);
                
                // Instead of removing, show the response and disable input
                const requestDiv = responseInput.parentElement;
                requestDiv.classList.add('answered');
                
                // Create response display
                const responseDisplay = document.createElement('div');
                responseDisplay.className = 'response-display';
                responseDisplay.innerHTML = `<strong>Your response:</strong> ${response}`;
                
                // Remove input and button
                const inputElement = requestDiv.querySelector('input');
                const buttonElement = requestDiv.querySelector('button');
                if (inputElement) inputElement.remove();
                if (buttonElement) buttonElement.remove();
                
                // Add response display
                requestDiv.appendChild(responseDisplay);
            })
            .catch(error => log(`❌ Error sending response: ${error}`));
        }
        
        function showFinalAnswer(answer) {
            const div = document.createElement('div');
            div.className = 'final-answer';
            div.innerHTML = `
                <h3>🎉 Final Answer</h3>
                <p>${answer}</p>
            `;
            
            // Insert at the end, after all requests
            const requestsDiv = document.getElementById('requests');
            requestsDiv.appendChild(div);
            
            // Scroll to the final answer
            div.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Allow Enter key to submit responses
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                const target = event.target;
                if (target.id.startsWith('response-')) {
                    const requestId = target.id.replace('response-', '');
                    respond(requestId);
                } else if (target.id === 'question') {
                    startAgent();
                }
            }
        });
        
        // Start SSE on page load
        window.onload = function() {
            startSSE();
            log('🚀 Pizza Agent web interface ready!');
        };
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)