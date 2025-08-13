"""
Console demo for human-in-the-loop DSPy agents.
"""
import asyncio
from input_provider import ConsoleInputProvider
from agent import create_pizza_agent


async def main():
    """Run the console demo"""
    print("🍕 DSPy Human-in-the-Loop Pizza Agent (Console Version)")
    print("=" * 50)
    
    # Create provider and agent
    provider = ConsoleInputProvider()
    agent = create_pizza_agent(provider)
    
    while True:
        print("\nWhat would you like to ask the pizza agent?")
        print("(Type 'quit' to exit)")
        question = input("> ")
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not question.strip():
            continue
        
        try:
            print(f"\n🤖 Agent is thinking about: '{question}'")
            print("The agent may ask you questions during its reasoning process...\n")
            
            result = await agent.aforward(what_would_you_like=question)
            
            # Display the structured order
            if hasattr(result, 'order') and result.order:
                print(f"\n✅ Your order:")
                for i, pizza in enumerate(result.order, 1):
                    print(f"  {i}. {pizza['size']} pizza with {', '.join(pizza['toppings'])}")
                    if pizza.get('special_instructions'):
                        print(f"     Special instructions: {pizza['special_instructions']}")
            else:
                print(f"\n✅ Order: {result.order if hasattr(result, 'order') else 'Could not process order'}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print("\n" + "-" * 50)


if __name__ == "__main__":
    # Set up a simple LLM (you'll need to configure this with your preferred model)
    # For now, we'll use a placeholder
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Setup Error: {e}")
        print("\nNote: You may need to configure DSPy with an LLM model.")
        print("See DSPy documentation for setup instructions.")