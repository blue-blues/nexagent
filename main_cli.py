import asyncio
import os
import sys
from app.cli import main as cli_main

if __name__ == "__main__":
    try:
        # Run the CLI main function
        asyncio.run(cli_main())
    except KeyboardInterrupt:
        print("\nExiting NexAgent CLI...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
