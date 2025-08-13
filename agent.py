"""
DSPy ReAct agent with human-in-the-loop capabilities.
"""
from typing_extensions import TypedDict

import dspy
from input_provider import InputProvider


lm = dspy.LM('openrouter/google/gemini-2.5-flash')
dspy.configure(lm=lm)


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



class PizzaOrder(TypedDict):
    """TypedDict for pizza order details"""
    size: str
    toppings: list[str]
    special_instructions: str | None


class PizzaOrderAgent(dspy.Signature):
    """An agent that helps order pizza by asking the human for preferences"""
    what_would_you_like = dspy.InputField()
    order: list[PizzaOrder] = dspy.OutputField()

def create_pizza_agent(provider: InputProvider):
    """Create a pizza ordering agent that needs human input"""
    
    human_tool = create_human_input_tool(provider)
    
    # Use the PizzaOrderAgent signature with ReAct
    agent = dspy.ReAct(signature=PizzaOrderAgent, tools=[human_tool], max_iters=6)
    
    return agent