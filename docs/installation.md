# Nexagent Installation Guide

## Prerequisites

- Python 3.9 or higher
- Git (for cloning the repository)
- Node.js and npm (for the web interface)

## Basic Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/blue-blues/nexagent.git
cd nexagent
```

### Step 2: Create a Virtual Environment (Recommended)

#### On Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux

```bash
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

For conversation organization features, install additional dependencies:

```bash
pip install -r requirements_conversation_org.txt
```

### Step 4: Configure the Application

1. Create a configuration file:

```bash
cp config/config.example.toml config/config.toml
```

2. Edit `config/config.toml` to add your API keys and customize settings:

```toml
# LLM model configuration
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "your-api-key-here"  # Replace with your actual API key
max_tokens = 4096
temperature = 0.0

# Browser configuration
[browser]
headless = false  # Set to true for production use
timeout = 30000   # Default timeout in milliseconds
```

## Web Interface Installation

If you want to use the web interface, you'll need to set up the frontend components:

### Step 1: Navigate to the Web Directory

```bash
cd web
```

### Step 2: Install Node.js Dependencies

```bash
npm install
```

### Step 3: Build the Web Interface

```bash
npm run build
```

## Running Nexagent

### CLI Mode

To run Nexagent in CLI mode:

```bash
python main_cli.py
```

### Web Interface Mode

To run Nexagent with the web interface:

```bash
python main.py
```

### API Server Mode

To run Nexagent as an API server:

```bash
python run_api_server.py
```

For conversation organization features:

```bash
python run_api_server_with_organization.py
```

## Troubleshooting

### Common Issues

#### Missing Dependencies

If you encounter errors about missing packages, try installing them manually:

```bash
pip install package-name
```

#### Browser Automation Issues

If you encounter issues with browser automation:

1. Make sure you have a compatible browser installed
2. Try setting `headless = false` in the configuration to see what's happening
3. Increase the timeout value if operations are timing out

#### API Key Issues

If you encounter authentication errors:

1. Verify that your API key is correct
2. Check that you have sufficient credits or quota for the API service
3. Ensure your API key has the necessary permissions

## Advanced Configuration

### Custom LLM Providers

Nexagent supports multiple LLM providers. To use a different provider, modify the `config.toml` file:

```toml
[llm]
model = "your-model-name"
base_url = "https://your-provider-api-url"
api_key = "your-api-key"
```

### Browser Configuration

For advanced browser configuration:

```toml
[browser]
headless = true
timeout = 60000  # 60 seconds
user_agent = "Custom User Agent String"
proxy = "http://your-proxy-server:port"
```

## Updating Nexagent

To update to the latest version:

```bash
git pull
pip install -r requirements.txt
```

If the web interface has been updated:

```bash
cd web
npm install
npm run build
```