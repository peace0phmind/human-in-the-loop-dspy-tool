"""
Console demo for human-in-the-loop DSPy agents.
"""
import asyncio
import dspy
from pizza_agent import OrderPizza
from human_in_the_loop import human_in_the_loop, console_requester


async def main():
    """Run the console demo"""
    print("DSPy Human-in-the-Loop Pizza Agent (Console Version)")
    print("=" * 50)
    
    lm = dspy.LM('openai/GS-Qwen3-30B', api_key="py123", base_url="https://ai.b.0fpy.com/v1")
    dspy.configure(lm=lm)

    # Create agent for console usage
    agent = dspy.ReAct(
        signature=OrderPizza,
        tools=[human_in_the_loop(console_requester)],
        max_iters=6
    )
    
    while True:
        print("\nWhat is your order?")
        print("(Type 'quit' to exit)")
        customer_request = input("> ")
        
        if customer_request.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not customer_request.strip():
            continue
        
        try:
            print(f"\nAgent is thinking about: '{customer_request}'")
            print("The agent may ask you questions during its reasoning process...\n")
            
            result = await agent.aforward(customer_request=customer_request)
            
            # Display the structured order
            if hasattr(result, 'order') and result.order:
                print(f"\nYour order:")
                for i, pizza in enumerate(result.order, 1):
                    print(f"  {i}. {pizza['size']} pizza with {', '.join(pizza['toppings'])}")
                    if pizza.get('special_instructions'):
                        print(f"     Special instructions: {pizza['special_instructions']}")
            else:
                print(f"\nOrder: {result.pizzas if hasattr(result, 'pizzas') else 'Could not process order'}")

        except Exception as e:
            print(f"\nError: {e}")
        
        print("\n" + "-" * 50)


if __name__ == "__main__":
    # Set up a simple LLM (you'll need to configure this with your preferred model)
    # For now, we'll use a placeholder
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nSetup Error: {e}")
        print("\nNote: You may need to configure DSPy with an LLM model.")
        print("See DSPy documentation for setup instructions.")