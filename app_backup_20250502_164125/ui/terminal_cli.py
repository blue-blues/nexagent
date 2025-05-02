"""
CLI interface for the Terminal UI Component.
"""

import os
import sys
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from app.ui.terminal_ui_component import terminal_ui
from app.logger import logger


class TerminalCLI:
    """CLI interface for the Terminal UI Component."""
    
    def __init__(self):
        """Initialize the CLI interface."""
        self.session = PromptSession(
            history=InMemoryHistory(),
            style=Style.from_dict({
                'prompt': 'ansigreen bold',
                'command': 'ansiwhite',
            }),
            completer=WordCompleter([
                'cd', 'dir', 'ls', 'copy', 'move', 'del', 'mkdir', 'rmdir',
                'echo', 'type', 'more', 'find', 'where', 'help', 'python',
                'git', 'npm', 'pip', 'grep', 'cat', 'touch', 'code',
                'tab', 'new-tab', 'close-tab', 'list-tabs', 'switch-tab',
                'history', 'clear', 'exit', 'quit'
            ])
        )
        self.running = False
    
    async def execute_command(self, command: str) -> str:
        """
        Execute a command in the terminal.
        
        Args:
            command: The command to execute
            
        Returns:
            Command output
        """
        # Handle special commands
        if command.startswith("tab "):
            parts = command.split(" ", 1)
            if len(parts) > 1:
                tab_name = parts[1]
                tab_id = terminal_ui.create_tab(tab_name)
                terminal_ui.switch_tab(tab_id)
                return f"Created and switched to tab: {tab_name}"
            return "Usage: tab <tab_name>"
        
        elif command == "new-tab":
            tab_id = terminal_ui.create_tab(f"Tab {len(terminal_ui.tabs) + 1}")
            terminal_ui.switch_tab(tab_id)
            return f"Created and switched to tab: Tab {len(terminal_ui.tabs)}"
        
        elif command == "list-tabs":
            tabs = []
            for tab_id, tab in terminal_ui.tabs.items():
                if tab_id == terminal_ui.active_tab_id:
                    tabs.append(f"* {tab.name} (active)")
                else:
                    tabs.append(f"  {tab.name}")
            return "Tabs:\n" + "\n".join(tabs)
        
        elif command.startswith("switch-tab "):
            parts = command.split(" ", 1)
            if len(parts) > 1:
                tab_name = parts[1]
                for tab_id, tab in terminal_ui.tabs.items():
                    if tab.name == tab_name:
                        terminal_ui.switch_tab(tab_id)
                        return f"Switched to tab: {tab_name}"
                return f"Tab not found: {tab_name}"
            return "Usage: switch-tab <tab_name>"
        
        elif command.startswith("close-tab"):
            parts = command.split(" ", 1)
            if len(parts) > 1:
                tab_name = parts[1]
                for tab_id, tab in terminal_ui.tabs.items():
                    if tab.name == tab_name:
                        terminal_ui.close_tab(tab_id)
                        return f"Closed tab: {tab_name}"
                return f"Tab not found: {tab_name}"
            else:
                # Close active tab
                active_tab = terminal_ui.get_active_tab()
                if active_tab:
                    tab_name = active_tab.name
                    terminal_ui.close_tab(terminal_ui.active_tab_id)
                    return f"Closed tab: {tab_name}"
                return "No active tab to close"
        
        elif command == "history":
            history = terminal_ui.get_command_history()
            if not history:
                return "No command history"
            return "Command history:\n" + "\n".join([f"{i+1}. {cmd}" for i, cmd in enumerate(history)])
        
        elif command == "clear":
            os.system('cls' if os.name == 'nt' else 'clear')
            return ""
        
        elif command in ["exit", "quit"]:
            self.running = False
            return "Exiting..."
        
        # For regular commands, add to history and execute
        terminal_ui.add_command_to_history(command)
        
        # Simulate command execution (in a real implementation, this would use subprocess)
        if command.startswith("cd "):
            parts = command.split(" ", 1)
            if len(parts) > 1:
                path = parts[1]
                try:
                    os.chdir(path)
                    active_tab = terminal_ui.get_active_tab()
                    if active_tab:
                        active_tab.working_directory = os.getcwd()
                    output = f"Changed directory to: {os.getcwd()}"
                except Exception as e:
                    output = f"Error: {str(e)}"
            else:
                output = f"Current directory: {os.getcwd()}"
        elif command == "ls" or command == "dir":
            try:
                files = os.listdir()
                output = "\n".join(files)
            except Exception as e:
                output = f"Error: {str(e)}"
        elif command.startswith("echo "):
            parts = command.split(" ", 1)
            if len(parts) > 1:
                output = parts[1]
            else:
                output = ""
        elif command == "pwd":
            output = os.getcwd()
        else:
            # For demo purposes, just echo the command
            output = f"Simulated execution of: {command}"
        
        # Add output to history
        terminal_ui.add_output_to_history(command, output)
        
        return output
    
    async def run(self):
        """Run the CLI interface."""
        self.running = True
        
        # Print welcome message
        print("Terminal UI Component Demo")
        print("Type 'exit' or 'quit' to exit")
        print("Type 'help' for a list of commands")
        print()
        
        while self.running:
            try:
                # Get active tab
                active_tab = terminal_ui.get_active_tab()
                if not active_tab:
                    prompt_text = "$ "
                else:
                    prompt_text = f"{active_tab.name} $ "
                
                # Get user input
                command = await self.session.prompt_async(HTML(f"<ansigreen><b>{prompt_text}</b></ansigreen>"))
                
                # Execute command
                if command.strip():
                    output = await self.execute_command(command.strip())
                    if output:
                        print(output)
                
            except KeyboardInterrupt:
                print("^C")
            except EOFError:
                print("^D")
                self.running = False
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                print(f"Error: {str(e)}")


async def main():
    """Main entry point."""
    cli = TerminalCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
