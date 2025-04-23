import threading
import tomllib
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.logger import logger


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMSettings(BaseModel):
    model: str = Field(..., description="LLM model name")
    api_type: str = Field("google", description="API type (openai, azure, google, ollama)")
    api_key: str = Field(..., description="API key for the LLM service")
    api_version: Optional[str] = Field(None, description="API version (required for Azure)")
    base_url: str = Field(..., description="Base URL for the API")
    max_tokens: int = Field(1024, description="Maximum tokens in the response")
    temperature: float = Field(0.7, description="Temperature for sampling")
    allowed_domains: Optional[List[str]] = Field(None, description="Allowed domains for ethical scraping")
    allowed_content_types: Optional[List[str]] = Field(None, description="Permitted content types")
    max_input_tokens: Optional[int] = Field(
        None, description="Maximum input tokens to use across all requests"
    )
    api_call_delay: float = Field(1.0, description="Delay between API calls in seconds")
    python_execute_timeout: int = Field(30, description="Timeout for Python code execution in seconds")
    bash_timeout: float = Field(120.0, description="Timeout for bash commands in seconds")


class ProxySettings(BaseModel):
    server: str = Field(None, description="Proxy server address")
    username: Optional[str] = Field(None, description="Proxy username")
    password: Optional[str] = Field(None, description="Proxy password")


class SearchSettings(BaseModel):
    engine: str = Field(default="Google", description="Search engine the llm to use")
    brave_api_key: Optional[str] = Field(None, description="API key for Brave Search")


class FileAttachmentSettings(BaseModel):
    max_file_size: int = Field(10485760, description="Maximum file size in bytes (10MB)")
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".txt", ".pdf", ".docx", ".xlsx", ".csv", ".json", ".xml", ".html", ".md", ".py", ".js", ".ts", ".jpg", ".jpeg", ".png", ".gif"],
        description="List of allowed file extensions"
    )
    scan_for_malware: bool = Field(True, description="Whether to scan uploaded files for malware")
    process_content: bool = Field(True, description="Whether to process the content of the file")


class BrowserSettings(BaseModel):
    headless: bool = Field(False, description="Whether to run browser in headless mode")
    disable_security: bool = Field(
        True, description="Disable browser security features"
    )
    rate_limit: int = Field(5, description="Maximum requests per second")
    respect_robots_txt: bool = Field(True, description="Enable robots.txt compliance")
    extra_chromium_args: List[str] = Field(
        default_factory=list, description="Extra arguments to pass to the browser"
    )
    chrome_instance_path: Optional[str] = Field(
        None, description="Path to a Chrome instance to use"
    )
    wss_url: Optional[str] = Field(
        None, description="Connect to a browser instance via WebSocket"
    )
    cdp_url: Optional[str] = Field(
        None, description="Connect to a browser instance via CDP"
    )
    proxy: Optional[ProxySettings] = Field(
        None, description="Proxy settings for the browser"
    )
    # Fallback browser settings
    enable_fallback: bool = Field(
        True, description="Whether to enable automatic fallback to browser-use/web-ui when scraping fails"
    )
    max_fallback_attempts: int = Field(
        3, description="Maximum number of fallback attempts before giving up"
    )
    web_ui_url: str = Field(
        "http://localhost:3000", description="URL for the browser-use/web-ui service"
    )
    # Enhanced web browser settings
    stealth_mode: bool = Field(
        True, description="Enable stealth mode to avoid detection"
    )
    random_delay: bool = Field(
        True, description="Enable random delays to appear more human-like"
    )
    min_delay: int = Field(
        800, description="Minimum delay in milliseconds for random delays"
    )
    max_delay: int = Field(
        2500, description="Maximum delay in milliseconds for random delays"
    )
    user_agent_rotation: bool = Field(
        True, description="Enable user agent rotation"
    )
    base_delay: float = Field(
        1.0, description="Base delay for exponential backoff retry mechanism"
    )
    validation_level: str = Field(
        "thorough", description="Default validation level for multi-source validation"
    )


class AppConfig(BaseModel):
    llm: Dict[str, LLMSettings]
    browser_config: Optional[BrowserSettings] = Field(
        None, description="Browser configuration"
    )
    search_config: Optional[SearchSettings] = Field(
        None, description="Search configuration"
    )
    file_attachment_config: Optional[FileAttachmentSettings] = Field(
        None, description="File attachment configuration"
    )

    class Config:
        arbitrary_types_allowed = True


class Config:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_config_path() -> Path:
        root = PROJECT_ROOT
        config_path = root / "config" / "config.toml"
        # Use the current working directory path instead of hardcoded absolute path
        if config_path.exists():
            logger.info(f"Loading configuration from path: {config_path}")
            return config_path
        example_path = root / "config" / "config.example.toml"
        if example_path.exists():
            logger.warning(f"Configuration file not found, using example config: {example_path}")
            return example_path
        raise FileNotFoundError("No configuration file found in config directory")

    def _load_config(self) -> dict:
        try:
            config_path = self._get_config_path()
            with config_path.open("rb") as f:
                config = tomllib.load(f)
                logger.info("Configuration loaded successfully")
                return config
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            raise
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Error parsing TOML configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            raise

    def _load_initial_config(self):
        raw_config = self._load_config()
        base_llm = raw_config.get("llm", {})
        llm_overrides = {
            k: v for k, v in raw_config.get("llm", {}).items() if isinstance(v, dict)
        }

        default_settings = {
            "model": base_llm.get("model"),
            "base_url": base_llm.get("base_url"),
            "api_key": base_llm.get("api_key"),
            "max_tokens": base_llm.get("max_tokens", 4096),
            "max_input_tokens": base_llm.get("max_input_tokens"),
            "temperature": base_llm.get("temperature", 1.0),
            "api_type": base_llm.get("api_type", "openai"),
            "api_version": base_llm.get("api_version", ""),
            "api_call_delay": base_llm.get("api_call_delay", 1.0),
            "bash_timeout": base_llm.get("bash_timeout", 300.0),
        }

        # handle browser config.
        browser_config = raw_config.get("browser", {})
        browser_settings = None

        if browser_config:
            # handle proxy settings.
            proxy_config = browser_config.get("proxy", {})
            proxy_settings = None

            if proxy_config and proxy_config.get("server"):
                proxy_settings = ProxySettings(
                    **{
                        k: v
                        for k, v in proxy_config.items()
                        if k in ["server", "username", "password"] and v
                    }
                )

            # filter valid browser config parameters.
            valid_browser_params = {
                k: v
                for k, v in browser_config.items()
                if k in BrowserSettings.__annotations__ and v is not None
            }

            # if there is proxy settings, add it to the parameters.
            if proxy_settings:
                valid_browser_params["proxy"] = proxy_settings

            # only create BrowserSettings when there are valid parameters.
            if valid_browser_params:
                browser_settings = BrowserSettings(**valid_browser_params)

        search_config = raw_config.get("search", {})
        search_settings = None
        if search_config:
            search_settings = SearchSettings(**search_config)

        # Load file attachment settings
        file_attachment_config = raw_config.get("file_attachment", {})
        file_attachment_settings = None
        if file_attachment_config:
            file_attachment_settings = FileAttachmentSettings(**file_attachment_config)

        config_dict = {
            "llm": {
                "default": default_settings,
                **{
                    name: {**default_settings, **override_config}
                    for name, override_config in llm_overrides.items()
                },
            },
            "browser_config": browser_settings,
            "search_config": search_settings,
            "file_attachment_config": file_attachment_settings,
        }

        self._config = AppConfig(**config_dict)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        return self._config.llm

    @property
    def browser_config(self) -> Optional[BrowserSettings]:
        return self._config.browser_config

    @property
    def search_config(self) -> Optional[SearchSettings]:
        return self._config.search_config

    @property
    def file_attachment_config(self) -> Optional[FileAttachmentSettings]:
        return self._config.file_attachment_config


config = Config()
