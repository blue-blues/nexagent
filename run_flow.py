import asyncio
import time

from app.agent.nexagent import Nexagent
from app.config import config
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger
from app.session import session_manager


async def run_flow():
    # Verify configuration is loaded correctly
    try:
        # Log configuration details for verification
        logger.info("Configuration loaded successfully")
        logger.info(f"LLM Models configured: {list(config.llm.keys())}")
        if config.browser_config:
            logger.info(f"Browser configuration: headless={config.browser_config.headless}")
        if config.search_config:
            logger.info(f"Search engine: {config.search_config.engine}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise
        
    agents = {
        "nexagent": Nexagent(),
    }
    
    # Create a new session
    session = session_manager.create_session()
    flow = None

    try:
        while True:
            # Get user input based on session state
            if session.is_waiting():
                prompt = input("\nWhat would you like to do next? ")
            else:
                prompt = input("\nEnter your prompt: ")

            if prompt.strip().isspace() or not prompt:
                logger.warning("Empty prompt provided. Please enter a valid prompt.")
                continue

            # Mark session as active
            session.mark_active()
            
            # Create flow if it doesn't exist or create a new one for each request
            # (depending on whether we want to maintain flow state between requests)
            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agents,
            )
            logger.warning("Processing your request...")

            try:
                start_time = time.time()
                result = await asyncio.wait_for(
                    flow.execute(prompt),
                    timeout=3600,  # 60 minute timeout for the entire execution
                )
                elapsed_time = time.time() - start_time
                logger.info(f"Request processed in {elapsed_time:.2f} seconds")
                logger.info(result)
                
                # Record task in session history
                primary_agent = flow.primary_agent
                success = hasattr(primary_agent, 'state') and primary_agent.state == "FINISHED"
                session.add_task(prompt, result, success)
                
                # Mark session as waiting for next input
                session.mark_waiting()
                
            except asyncio.TimeoutError:
                logger.error("Request processing timed out after 1 hour")
                logger.info(
                    "Operation terminated due to timeout. Please try a simpler request."
                )
                session.add_task(prompt, "Request timed out", False)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
        session.mark_terminated()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if session:
            session.mark_terminated()


if __name__ == "__main__":
    asyncio.run(run_flow())
