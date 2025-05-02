"""
Configuration Module

This module provides a unified interface for accessing application configuration.
It loads configuration from various sources and provides a consistent interface
for accessing configuration values.
"""

import os
import tomli
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.core.schema.schema import LLMSettings
from app.core.schema.exceptions import ConfigurationError
from app.utils.logging.logger import logger


class ToolSettings(BaseModel):
    """Settings for tools"""
    
    enabled: bool = Field(True, description="Whether tools are enabled")
    allowed_tools: Optional[List[str]] = Field(None, description="List of allowed tools")
    blocked_tools: List[str] = Field(default_factory=list, description="List of blocked tools")
    timeout: int = Field(60, description="Default timeout for tool execution in seconds")


class BrowserSettings(BaseModel):
    """Settings for browser tools"""
    
    headless: bool = Field(True, description="Whether to run browser in headless mode")
    user_agent: Optional[str] = Field(None, description="User agent to use")
    timeout: int = Field(30, description="Default timeout for browser operations in seconds")
    allowed_domains: Optional[List[str]] = Field(None, description="List of allowed domains")
    blocked_domains: List[str] = Field(default_factory=list, description="List of blocked domains")


class SearchSettings(BaseModel):
    """Settings for search tools"""
    
    engine: str = Field("google", description="Default search engine")
    api_key: Optional[str] = Field(None, description="API key for search engine")
    max_results: int = Field(5, description="Maximum number of search results")


class AgentSettings(BaseModel):
    """Settings for agents"""
    
    default_agent: str = Field("nexagent", description="Default agent type")
    max_steps: int = Field(10, description="Maximum steps for agent execution")
    timeout: int = Field(300, description="Default timeout for agent execution in seconds")


class AppConfig(BaseModel):
    """Main application configuration"""
    
    # General settings
    app_name: str = Field("Nexagent", description="Application name")
    debug: bool = Field(False, description="Whether debug mode is enabled")
    
    # Component settings
    llm: LLMSettings
    tools: ToolSettings = Field(default_factory=ToolSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    
    # Additional settings
    custom_settings: Dict[str, Any] = Field(default_factory=dict)


class ConfigLoader:
    """
    Configuration loader for the application.
    
    This class provides methods for loading configuration from various sources
    and accessing configuration values.
    """
    
    _instance: Optional["ConfigLoader"] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Path to the configuration file
        """
        if self._config is not None:
            return
        
        if config_path is None:
            # Try to find config in standard locations
            possible_paths = [
                Path("config.toml"),
                Path("config/config.toml"),
                Path(os.getcwd()) / "config.toml",
                Path(os.getcwd()) / "config" / "config.toml",
            ]
            
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
        
        if config_path is None or not Path(config_path).exists():
            logger.warning("No configuration file found, using default values")
            # Create minimal config with required values
            self._config = AppConfig(
                llm=LLMSettings(
                    model="gpt-3.5-turbo",
                    api_type="openai",
                    api_key=os.environ.get("OPENAI_API_KEY", ""),
                    base_url="https://api.openai.com/v1",
                )
            )
            return
        
        try:
            # Load configuration from file
            with open(config_path, "rb") as f:
                config_data = tomli.load(f)
            
            # Create config object
            self._config = AppConfig(**config_data)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise ConfigurationError(f"Error loading configuration: {str(e)}")
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration"""
        if self._config is None:
            raise ConfigurationError("Configuration not initialized")
        return self._config
    
    def reload(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """
        Reload the configuration.
        
        Args:
            config_path: Path to the configuration file
        """
        self._config = None
        self.__init__(config_path)


# Create a singleton instance
config_loader = ConfigLoader()
config = config_loader.config
