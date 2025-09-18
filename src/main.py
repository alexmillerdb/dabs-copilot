"""Main entry point for DAB agent system"""
import asyncio
import logging
from agents.orchestrator import OrchestratorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run interactive DAB agent"""
    logger.info("Starting Databricks Asset Bundle Agent System")
    
    agent = OrchestratorAgent()
    
    print("🤖 Databricks Asset Bundle Agent")
    print("Type 'help' for available commands or 'quit' to exit")
    print()
    
    while True:
        try:
            user_input = input("DAB Agent> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if not user_input:
                continue
            
            # Handle request
            response = await agent.handle_request(user_input)
            print(f"\n{response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())