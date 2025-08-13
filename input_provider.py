"""
Input provider implementations for human-in-the-loop DSPy agents.
"""
from typing import Protocol, Dict
import asyncio
import uuid


class InputProvider(Protocol):
    """Protocol for different human input mechanisms"""
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        """Request input from a human"""
        ...
    
    def provide_response(self, request_id: str, response: str) -> None:
        """Callback for async providers to receive human response"""
        ...


class ConsoleInputProvider:
    """Simple console-based input provider"""
    
    async def get_input(self, question: str, metadata: dict = None) -> str:
        # For async compatibility, but actually synchronous
        return input(f"\n🤔 {question}\n> ")
    
    def provide_response(self, request_id: str, response: str) -> None:
        # Not needed for console - input() blocks until response
        pass


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