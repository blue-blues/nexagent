# Handling Long-Running Commands in NexAgent

## Overview

NexAgent provides a specialized tool for handling commands that may take longer than the default timeout period to complete. This document explains how to use the `long_running_command` tool to prevent timeout issues when executing time-intensive operations.

## Problem: Timeout Errors

The standard `bash` tool in NexAgent has a default timeout of 300 seconds (5 minutes). When commands exceed this timeout, you'll see errors like:

```
Error in IntegratedAgent: timed out: bash has not returned in 300.0 seconds and must be restarted
```

These errors occur because the bash tool is designed for relatively quick commands and has a built-in safety mechanism to prevent indefinitely hanging processes.

## Solution: The Long-Running Command Tool

The `long_running_command` tool is specifically designed to handle commands that may take longer than the default timeout period. It offers:

- Extended timeout periods (default: 30 minutes)
- Background execution option
- Process monitoring capabilities
- Graceful termination handling

## Usage

### Basic Usage

To execute a command with an extended timeout:

```python
from app.tool import LongRunningCommand

# Create the tool
long_running_tool = LongRunningCommand()

# Execute a command with a 10-minute timeout
result = await long_running_tool.execute(
    command="python my_long_script.py",
    timeout=600  # 10 minutes
)

print(result.output)
```

### Background Execution

For commands that may run indefinitely or for a very long time:

```python
# Start a command in the background
result = await long_running_tool.execute(
    command="python my_server.py > server.log 2>&1",
    background=True
)

# Get the process ID from the output
process_id = result.output.split("ID: ")[1].split("\n")[0]

# Later, check the status
status = await long_running_tool.check_background_command(process_id)
print(status.output)

# If needed, terminate the process
await long_running_tool.terminate_background_command(process_id)
```

## Best Practices

1. **Use Background Mode for Web Servers**: When starting web servers or services that need to run continuously, always use `background=True`.

2. **Redirect Output**: For long-running commands, redirect output to files:
   ```
   command="python my_script.py > output.log 2>&1"
   ```

3. **Set Appropriate Timeouts**: Consider the expected runtime of your command and set the timeout accordingly. For uncertain durations, use a generous timeout or background mode.

4. **Monitor Background Processes**: Always keep track of background process IDs and check their status periodically.

5. **Clean Up**: Terminate background processes when they're no longer needed to avoid resource leaks.

## Configuration

The default timeout for the `long_running_command` tool is 1800 seconds (30 minutes). You can adjust this by passing a different `timeout` parameter when executing commands.

For truly long-running processes or services, use `background=True` and `timeout=0` to run without any timeout constraint.

## Comparison with Bash Tool

| Feature | `bash` Tool | `long_running_command` Tool |
|---------|------------|-----------------------------|
| Default Timeout | 300 seconds (5 minutes) | 1800 seconds (30 minutes) |
| Background Execution | Limited support | Full support with monitoring |
| Process Monitoring | No | Yes |
| Graceful Termination | Limited | Yes, with SIGTERM then SIGKILL |
| Best For | Quick commands, interactive shells | Long-running processes, services |

## Troubleshooting

If you encounter issues with the `long_running_command` tool:

1. **Command Still Times Out**: Increase the timeout parameter or use background mode.

2. **Background Process Not Found**: Ensure you're using the correct process ID returned when starting the command.

3. **Process Won't Terminate**: The tool will attempt to gracefully terminate processes, but some may require manual intervention.