# Manus Agent for Nexagent

The Manus Agent is a versatile AI assistant that can handle complex tasks with visible thinking processes. It's designed to provide a seamless interface where users can submit complex tasks, receive intelligent, actionable outputs, and benefit from an AI that "thinks" through tasks before delivering results.

## Features

### Task Interpretation

The Manus Agent can parse user queries, identify core requirements, and determine the appropriate steps to generate an output. For example, if a user requests to "find the largest real estate brokerages," the agent will break down the task into data retrieval, analysis, and presentation.

### Thought Process Visibility

The agent incorporates a feature where it can display its "thinking process" (e.g., major decision points or analysis steps) that builds trust and transparency in the output. Users can toggle the visibility of this process.

### Action Execution

The agent can integrate with various APIs and internal databases to fetch real-time data, perform calculations, or generate content based on the user's request.

### Multi-Task Handling

The agent is capable of queuing and managing multiple tasks simultaneously, prioritizing based on complexity or user-defined preferences.

## Use Cases

### Data Analysis

The Manus Agent can analyze data from various sources, perform calculations, and present results in a structured format. For example, it can analyze real estate data to identify the largest brokerages based on number of agents, total revenue, or other metrics.

### Travel Planning

Users can submit travel planning requests, and the agent will gather information about destinations, accommodations, transportation, and activities to create a comprehensive travel plan.

### Research

The agent can conduct research on various topics, gathering information from multiple sources, synthesizing the data, and presenting findings in a structured format.

### Content Generation

Users can request the agent to generate content such as blog posts, reports, or summaries based on specific topics or requirements.

## Getting Started

### Installation

1. Ensure you have the Nexagent framework installed.
2. The Manus Agent is included in the Nexagent framework and doesn't require additional installation.

### Running the Manus Agent

You can run the Manus Agent as a standalone application using the provided script:

```bash
python run_manus_agent.py
```

This will start the agent and API server, allowing you to interact with it through the REST API or web interface.

### Using the Web Interface

The Manus Agent includes a web interface that allows you to submit tasks, view results, and toggle the visibility of the thinking process. To access the web interface, open your browser and navigate to:

```
http://localhost:8000
```

### Using the API

You can also interact with the Manus Agent programmatically through its REST API. Here are some example API calls:

#### Submit a Task

```python
import requests

response = requests.post(
    "http://localhost:8000/api/manus/tasks",
    json={
        "task_description": "Find the largest real estate brokerages in the US",
        "category": "research",
        "show_thinking": True,
        "priority": 1
    }
)

task_id = response.json()["task_id"]
print(f"Task submitted with ID: {task_id}")
```

#### Get Task Result

```python
import requests

response = requests.get(f"http://localhost:8000/api/manus/tasks/{task_id}")
task_result = response.json()

print(f"Task status: {task_result['status']}")
print(f"Task result: {task_result['details']}")
```

#### Toggle Thinking Visibility

```python
import requests

response = requests.post(
    f"http://localhost:8000/api/manus/tasks/{task_id}/thinking",
    json={"show": False}
)

print(response.json()["message"])
```

## Configuration

The Manus Agent can be configured through the Nexagent configuration system. Here are some configuration options:

### Agent Configuration

- `max_steps`: Maximum number of steps the agent will take before terminating (default: 30)
- `max_observe`: Maximum number of characters to observe from tool outputs (default: 2000)
- `show_thinking`: Whether to show the thinking process by default (default: True)

### API Configuration

- `host`: The host to bind the API server to (default: "0.0.0.0")
- `port`: The port to bind the API server to (default: 8000)

## Examples

### Data Analysis Example

```
Analyze the sales data in the attached CSV file and identify the top 5 performing products by revenue. Create a chart showing the revenue trend over time for these products.
```

### Travel Planning Example

```
Plan a 7-day trip to Japan in April for a family of 4 with children aged 10 and 12. Include recommendations for accommodations, transportation, activities, and a daily itinerary. The budget is $5,000 excluding flights.
```

### Research Example

```
Research the impact of artificial intelligence on the job market over the next decade. Include statistics, expert opinions, and potential mitigation strategies for job displacement.
```

## Troubleshooting

### Common Issues

- **Task Timeout**: If a task takes too long to complete, it may time out. Try breaking the task into smaller, more manageable pieces.
- **API Rate Limits**: If you're making too many API calls, you may hit rate limits. Consider adding delays between requests or implementing a backoff strategy.
- **Memory Issues**: If the agent is processing large amounts of data, it may run into memory issues. Try reducing the size of the data or breaking the task into smaller chunks.

### Getting Help

If you encounter any issues or have questions about the Manus Agent, please refer to the Nexagent documentation or open an issue on the GitHub repository.

## Contributing

Contributions to the Manus Agent are welcome! Please refer to the Nexagent contribution guidelines for more information.

## License

The Manus Agent is part of the Nexagent framework and is licensed under the same terms.