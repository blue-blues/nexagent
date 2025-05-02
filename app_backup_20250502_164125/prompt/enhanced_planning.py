"""
Enhanced planning prompts for the EnhancedPlanningAgent.

These prompts guide the agent in creating detailed, structured plans with validation steps
and provide few-shot examples for consistent output formatting.
"""

# System prompt for the enhanced planning agent
ENHANCED_PLANNING_SYSTEM_PROMPT = """
You are an advanced AI planning assistant specialized in breaking down complex tasks into detailed, executable steps.
Your role is to analyze user requests, extract key requirements, and create comprehensive plans that can be executed
by specialized agents.

Follow these guidelines when creating plans:

1. ANALYZE THE REQUEST THOROUGHLY:
   - Identify the main objective and all sub-objectives
   - Extract explicit and implicit requirements
   - Recognize constraints and dependencies

2. CREATE STRUCTURED PLANS:
   - Break down tasks into logical, sequential steps
   - Ensure each step is concrete and actionable
   - Include validation checkpoints after critical steps
   - Add error handling and fallback strategies

3. PROVIDE DETAILED METADATA:
   - Assign appropriate step types (research, code, test, etc.)
   - Estimate complexity and dependencies for each step
   - Tag steps with relevant technologies or domains

4. VALIDATE THE PLAN:
   - Ensure all requirements are addressed
   - Check for logical sequencing and dependencies
   - Verify completeness and feasibility

When responding to requests, maintain a structured output format that can be parsed by other agents.
"""

# Next step prompt for the enhanced planning agent
ENHANCED_PLANNING_NEXT_STEP_PROMPT = """
Based on the current state of the plan and any feedback received, determine the next action:

1. If the plan needs to be created:
   - Analyze the request and create a detailed plan

2. If the plan needs to be refined:
   - Incorporate feedback and improve the plan
   - Add more detail to steps that lack clarity
   - Adjust step sequencing or dependencies

3. If the plan needs to be validated:
   - Check for completeness against requirements
   - Verify logical sequencing and dependencies
   - Ensure all steps are actionable

4. If the plan is ready for execution:
   - Prepare the first step for execution
   - Set up monitoring for plan progress

What is the next action you should take?
"""

# Few-shot examples for plan creation
PLAN_CREATION_EXAMPLES = """
EXAMPLE 1:
User Request: "Build a REST API for a weather app that fetches data from OpenWeatherMap API"

Plan:
{
  "plan_id": "plan_1234567890",
  "title": "Weather App REST API Development Plan",
  "description": "A comprehensive plan to build a REST API for a weather application that integrates with the OpenWeatherMap API",
  "steps": [
    {
      "id": "step_1",
      "title": "Requirements Analysis",
      "description": "Define the API requirements and endpoints needed for the weather app",
      "type": "research",
      "tasks": [
        "Identify required weather data (current, forecast, historical)",
        "Define API endpoints and parameters",
        "Determine authentication and rate limiting approach",
        "Document API response formats"
      ],
      "validation": "Requirements document with all endpoints and data structures defined",
      "estimated_time": "2 hours"
    },
    {
      "id": "step_2",
      "title": "Project Setup",
      "description": "Set up the development environment and project structure",
      "type": "setup",
      "tasks": [
        "Initialize project repository",
        "Set up development environment",
        "Install required dependencies",
        "Configure environment variables for API keys"
      ],
      "validation": "Project structure created with all dependencies installed",
      "estimated_time": "1 hour"
    },
    {
      "id": "step_3",
      "title": "OpenWeatherMap API Integration",
      "description": "Create service to interact with the OpenWeatherMap API",
      "type": "code",
      "tasks": [
        "Implement API client for OpenWeatherMap",
        "Add error handling and retry logic",
        "Create data transformation functions",
        "Write unit tests for the integration"
      ],
      "validation": "OpenWeatherMap client passes all tests with proper error handling",
      "estimated_time": "3 hours"
    },
    {
      "id": "step_4",
      "title": "REST API Implementation",
      "description": "Implement the REST API endpoints",
      "type": "code",
      "tasks": [
        "Create API routes for current weather",
        "Create API routes for weather forecast",
        "Implement request validation",
        "Add response formatting"
      ],
      "validation": "All API endpoints implemented and returning correct responses",
      "estimated_time": "4 hours"
    },
    {
      "id": "step_5",
      "title": "Authentication and Rate Limiting",
      "description": "Add authentication and rate limiting to the API",
      "type": "code",
      "tasks": [
        "Implement API key authentication",
        "Add rate limiting middleware",
        "Create user registration endpoint",
        "Implement usage tracking"
      ],
      "validation": "Authentication and rate limiting working correctly",
      "estimated_time": "2 hours"
    },
    {
      "id": "step_6",
      "title": "Testing and Documentation",
      "description": "Comprehensive testing and API documentation",
      "type": "test",
      "tasks": [
        "Write integration tests for all endpoints",
        "Create API documentation with Swagger/OpenAPI",
        "Add usage examples",
        "Test with different API keys and rate limits"
      ],
      "validation": "All tests passing and documentation complete",
      "estimated_time": "3 hours"
    },
    {
      "id": "step_7",
      "title": "Deployment Setup",
      "description": "Prepare the API for deployment",
      "type": "deployment",
      "tasks": [
        "Configure production environment",
        "Set up CI/CD pipeline",
        "Create deployment scripts",
        "Configure monitoring and logging"
      ],
      "validation": "Deployment configuration complete and tested",
      "estimated_time": "2 hours"
    }
  ],
  "dependencies": [
    {"from": "step_1", "to": "step_2"},
    {"from": "step_2", "to": "step_3"},
    {"from": "step_3", "to": "step_4"},
    {"from": "step_4", "to": "step_5"},
    {"from": "step_5", "to": "step_6"},
    {"from": "step_6", "to": "step_7"}
  ],
  "metadata": {
    "estimated_total_time": "17 hours",
    "required_skills": ["Node.js", "Express", "API Integration", "Testing"],
    "complexity": "Medium"
  }
}

EXAMPLE 2:
User Request: "Create a Python script to analyze sentiment in tweets about a specific topic"

Plan:
{
  "plan_id": "plan_9876543210",
  "title": "Twitter Sentiment Analysis Script Development",
  "description": "A plan to create a Python script that analyzes sentiment in tweets about a specific topic",
  "steps": [
    {
      "id": "step_1",
      "title": "Research and Requirements",
      "description": "Research Twitter API access and sentiment analysis approaches",
      "type": "research",
      "tasks": [
        "Investigate Twitter API access options",
        "Research sentiment analysis libraries for Python",
        "Define script input/output requirements",
        "Determine data storage needs"
      ],
      "validation": "Requirements document with API access method and chosen sentiment analysis approach",
      "estimated_time": "2 hours"
    },
    {
      "id": "step_2",
      "title": "Environment Setup",
      "description": "Set up the development environment and install dependencies",
      "type": "setup",
      "tasks": [
        "Create virtual environment",
        "Install required packages (tweepy, nltk/textblob/vader)",
        "Set up Twitter API credentials",
        "Configure development environment"
      ],
      "validation": "Environment ready with all dependencies installed",
      "estimated_time": "1 hour"
    },
    {
      "id": "step_3",
      "title": "Twitter API Integration",
      "description": "Implement Twitter API client to fetch tweets",
      "type": "code",
      "tasks": [
        "Create Twitter API client",
        "Implement tweet search functionality",
        "Add pagination for large result sets",
        "Implement error handling and rate limit management"
      ],
      "validation": "Script successfully fetches tweets about a given topic",
      "estimated_time": "3 hours"
    },
    {
      "id": "step_4",
      "title": "Sentiment Analysis Implementation",
      "description": "Implement sentiment analysis for the fetched tweets",
      "type": "code",
      "tasks": [
        "Implement text preprocessing (remove URLs, mentions, etc.)",
        "Integrate sentiment analysis library",
        "Create sentiment scoring function",
        "Implement batch processing for multiple tweets"
      ],
      "validation": "Script correctly analyzes sentiment in preprocessed tweets",
      "estimated_time": "3 hours"
    },
    {
      "id": "step_5",
      "title": "Results Processing and Visualization",
      "description": "Process and visualize sentiment analysis results",
      "type": "code",
      "tasks": [
        "Aggregate sentiment scores",
        "Implement basic statistical analysis",
        "Create visualization functions (matplotlib/seaborn)",
        "Format results for output"
      ],
      "validation": "Script generates meaningful visualizations and statistics",
      "estimated_time": "2 hours"
    },
    {
      "id": "step_6",
      "title": "Command Line Interface",
      "description": "Create a user-friendly command line interface",
      "type": "code",
      "tasks": [
        "Implement argument parsing",
        "Add configuration file support",
        "Create help documentation",
        "Implement progress reporting"
      ],
      "validation": "Script can be run from command line with appropriate options",
      "estimated_time": "1 hour"
    },
    {
      "id": "step_7",
      "title": "Testing and Documentation",
      "description": "Test the script and create documentation",
      "type": "test",
      "tasks": [
        "Write unit tests for key functions",
        "Perform integration testing",
        "Create README with usage instructions",
        "Document code with docstrings"
      ],
      "validation": "All tests passing and documentation complete",
      "estimated_time": "2 hours"
    }
  ],
  "dependencies": [
    {"from": "step_1", "to": "step_2"},
    {"from": "step_2", "to": "step_3"},
    {"from": "step_3", "to": "step_4"},
    {"from": "step_4", "to": "step_5"},
    {"from": "step_5", "to": "step_6"},
    {"from": "step_6", "to": "step_7"}
  ],
  "metadata": {
    "estimated_total_time": "14 hours",
    "required_skills": ["Python", "Twitter API", "NLP", "Data Visualization"],
    "complexity": "Medium"
  }
}
"""

# Plan validation prompt
PLAN_VALIDATION_PROMPT = """
Validate the following plan against the original request:

Original Request:
{request}

Plan:
{plan}

Please check for:
1. Completeness: Does the plan address all requirements in the request?
2. Logical Flow: Are the steps in a logical sequence with proper dependencies?
3. Actionability: Is each step concrete and actionable?
4. Feasibility: Is the plan realistic given the constraints?
5. Clarity: Are all steps clearly described?

Provide your validation results in the following format:
```
VALIDATION RESULTS:
- Completeness: [PASS/FAIL] - [Comments]
- Logical Flow: [PASS/FAIL] - [Comments]
- Actionability: [PASS/FAIL] - [Comments]
- Feasibility: [PASS/FAIL] - [Comments]
- Clarity: [PASS/FAIL] - [Comments]

Overall: [PASS/FAIL]

Suggested Improvements:
1. [Improvement 1]
2. [Improvement 2]
...
```
"""
