"""
DSPy ReAct agent with human-in-the-loop capabilities.
"""
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


def create_simple_math_tool():
    """Create a simple math calculator tool"""
    
    def calculate(expression: str) -> str:
        """Calculate a mathematical expression.
        
        Args:
            expression: A mathematical expression to evaluate (e.g., "2 + 3 * 4")
            
        Returns:
            The result of the calculation as a string
        """
        try:
            # Basic safety check - only allow safe characters
            allowed_chars = set('0123456789+-*/()%. ')
            if not all(c in allowed_chars for c in expression):
                return "Error: Invalid characters in expression"
            
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    
    return dspy.Tool(calculate)


def create_agent(provider: InputProvider):
    """Create a ReAct agent with human input capabilities"""
    
    # Create tools
    human_tool = create_human_input_tool(provider)
    math_tool = create_simple_math_tool()
    
    # Set up agent with a signature that requires reasoning
    agent = dspy.ReAct(signature="question -> answer", tools=[human_tool, math_tool])
    
    return agent




class PizzaOrderAgent(dspy.Signature):
    """An agent that helps order pizza by asking the human for preferences"""
    question = dspy.InputField(desc="A question about what pizza to order")
    answer = dspy.OutputField(desc="A complete pizza order recommendation based on human input")


def create_pizza_agent(provider: InputProvider):
    """Create a pizza ordering agent that needs human input"""
    
    human_tool = create_human_input_tool(provider)
    
    # Use the PizzaOrderAgent signature with ReAct
    agent = dspy.ReAct(signature=PizzaOrderAgent, tools=[human_tool], max_iters=6)
    
    return agent