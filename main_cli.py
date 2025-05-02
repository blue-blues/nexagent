import sys
from app.ui.cli.cli import main as cli_main

if __name__ == "__main__":
    try:
        # Run the CLI main function
        exit_code = cli_main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nExiting NexAgent CLI...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
