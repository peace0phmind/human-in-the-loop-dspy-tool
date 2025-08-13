"""
DSPy signature and types for pizza ordering agents.
"""
from typing_extensions import TypedDict

import dspy


class Pizza(TypedDict):
    """TypedDict for pizza order details"""
    size: str
    toppings: list[str]
    special_instructions: str | None


class OrderPizza(dspy.Signature):
    """
    An agent that can ask clarifying questions about a pizza order.
    It can handle multiple pizzas and special instructions.
    """
    customer_request = dspy.InputField()
    pizzas: list[Pizza] = dspy.OutputField()