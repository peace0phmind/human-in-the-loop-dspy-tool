"""
Human-in-the-loop implementation for DSPy agents.

This module provides the core infrastructure for inserting human feedback and decision-making
into automated DSPy agent workflows using a unified requester pattern.

The human-in-the-loop pattern allows agents to:
- Request clarification when uncertain
- Ask for approval before taking actions  
- Gather additional context from domain experts
- Involve humans in complex decision-making processes

"""
from dataclasses import dataclass
from typing import Callable, Awaitable
import asyncio
import uuid

import dspy


class HumanInputRequest:
    """A request for human input containing the question and response mechanism"""
    
    def __init__(self, question: str):
        self.question = question
        self._response_future = asyncio.Future()
    
    async def response(self) -> str:
        """Wait for the response to be provided"""
        return await self._response_future
    
    def set_response(self, response: str):
        """Provide the response and notify waiters"""
        self._response_future.set_result(response)


Requester = Callable[[HumanInputRequest], Awaitable[None]]


def human_in_the_loop(requester: Requester) -> dspy.Tool:
    """Create a human-in-the-loop tool for DSPy agents
    
    Args:
        requester: Async function that handles outbound requests to humans
        
    Returns:
        A DSPy tool that can ask humans for input
    """
    async def ask_human(question: str) -> str:
        """Ask a human for clarification, additional information, or approval."""
        request = HumanInputRequest(question)
        
        # Let requester handle the outbound request
        await requester(request)
        
        # Wait for response (resolved by requester or external system)
        response = await request.response()
        return response
    
    return dspy.Tool(ask_human)


# Console requester: ask via stdin and resolve immediately
async def console_requester(request: HumanInputRequest):
    """Console requester that gets input via stdin and resolves immediately"""
    response = input(f"\n🤔 {request.question}\n> ")
    request.set_response(response)


# Queue requester: push to queue for async delivery
def create_queue_requester(request_queue: asyncio.Queue, pending_requests: dict):
    """Create a queue requester that pushes requests to an asyncio.Queue for async delivery"""
    
    async def queue_requester(request: HumanInputRequest):
        """Queue requester that pushes request to queue for async delivery"""
        request_id = str(uuid.uuid4())
        
        # Store in pending requests for response resolution
        pending_requests[request_id] = {
            'request': request,
            'question': request.question,
            'sent': False
        }
        
        await request_queue.put({
            'type': 'human_input',
            'id': request_id,
            'question': request.question
        })
        # Mark as sent to avoid duplicate sends
        pending_requests[request_id]['sent'] = True
    
    return queue_requester