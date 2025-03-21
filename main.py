import asyncio

from app.agent.nexagent import Nexagent
from app.logger import logger
from app.session import session_manager


async def main():
    agent = Nexagent()
    session = session_manager.create_session()
    
    try:
        while True:
            # Get user input
            if session.is_waiting():
                prompt = input("\nWhat would you like to do next? ")
            else:
                prompt = input("\nEnter your prompt: ")
                
            if not prompt.strip():
                logger.warning("Empty prompt provided. Please enter a valid prompt.")
                continue
            
            # Mark session as active
            session.mark_active()
            
            # Process the request
            logger.warning("Processing your request...")
            result = await agent.run(prompt)
            
            # Record task in session history
            success = agent.state == "FINISHED"
            session.add_task(prompt, result, success)
            
            # If agent is in FINISHED state, mark session as waiting
            if agent.state == "FINISHED":
                session.mark_waiting()
                
            logger.info("Request processing completed.")
            
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
        session.mark_terminated()


if __name__ == "__main__":
    asyncio.run(main())
