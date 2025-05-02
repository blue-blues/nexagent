import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult
from app.tools.enhanced_browser_tool import EnhancedBrowserTool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FinancialDataExtractor')

# Telemetry data structure
class ExtractionTelemetry(BaseModel):
    """Tracks the success/failure rates of different extraction methods."""
    method_name: str
    success_count: int = 0
    failure_count: int = 0
    average_execution_time: float = 0.0
    last_execution_time: float = 0.0
    last_status: str = "not_executed"
    last_error: Optional[str] = None
    
    def update(self, success: bool, execution_time: float, error: Optional[str] = None):
        """Update telemetry after an extraction attempt."""
        if success:
            self.success_count += 1
            self.last_status = "success"
        else:
            self.failure_count += 1
            self.last_status = "failure"
            self.last_error = error
            
        self.last_execution_time = execution_time
        total_executions = self.success_count + self.failure_count
        self.average_execution_time = (
            (self.average_execution_time * (total_executions - 1) + execution_time) / total_executions
        )

# Financial metrics model
class FinancialMetrics(BaseModel):
    """Model for storing financial metrics of a stock."""
    symbol: str
    company_name: Optional[str] = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None
    market_cap: Optional[str] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None
    rsi: Optional[float] = None
    moving_avg_50d: Optional[float] = None
    moving_avg_200d: Optional[float] = None
    trading_volume: Optional[int] = None
    beta: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    analyst_rating: Optional[str] = None
    price_target: Optional[float] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    data_source: Optional[str] = None
    extraction_method: Optional[str] = None
    
    def calculate_score(self, weights: Dict[str, float] = None) -> float:
        """Calculate a weighted score based on financial metrics.
        
        Args:
            weights: Dictionary mapping metric names to their weights in the score calculation.
                     If None, default weights will be used.
        
        Returns:
            float: The calculated score.
        """
        if weights is None:
            # Default weights prioritizing growth, value, and profitability
            weights = {
                "revenue_growth": 0.15,
                "eps": 0.15,
                "pe_ratio": -0.10,  # Lower is better
                "profit_margin": 0.15,
                "roe": 0.15,
                "debt_to_equity": -0.10,  # Lower is better
                "dividend_yield": 0.05,
                "rsi": 0.05,  # Moderate RSI is better
                "beta": -0.05,  # Lower volatility is better
                "analyst_rating": 0.05
            }
        
        score = 0.0
        metrics_used = 0
        
        for metric, weight in weights.items():
            value = getattr(self, metric, None)
            if value is not None:
                # Handle special cases
                if metric == "pe_ratio" and value <= 0:
                    continue  # Skip negative P/E ratios
                    
                if metric == "rsi":
                    # Adjust RSI to prefer values in the middle range (40-60)
                    if 40 <= value <= 60:
                        adjusted_value = 1.0
                    elif value < 40:
                        adjusted_value = value / 40  # Lower values get lower scores
                    else:  # value > 60
                        adjusted_value = (100 - value) / 40  # Higher values get lower scores
                    score += adjusted_value * weight
                elif metric == "analyst_rating":
                    # Convert string ratings to numeric values
                    rating_map = {
                        "strong buy": 1.0,
                        "buy": 0.75,
                        "hold": 0.5,
                        "sell": 0.25,
                        "strong sell": 0.0
                    }
                    rating_value = rating_map.get(value.lower(), 0.5)
                    score += rating_value * weight
                else:
                    # For regular numeric metrics
                    score += value * weight
                    
                metrics_used += 1
        
        # Normalize score based on metrics used
        if metrics_used > 0:
            return score / sum(abs(w) for w in weights.values() if w != 0)
        return 0.0


class FinancialDataExtractor(BaseTool):
    """Tool for extracting financial data from websites with robust error handling and fallback strategies."""
    
    name: str = "financial_data_extractor"
    description: str = """
    Extract financial data from websites with robust error handling and fallback strategies.
    Features include:
    - Dynamic selectors for different financial websites
    - Multi-level fallback strategies
    - Anti-scraping mitigation techniques
    - Financial metrics analysis and stock ranking
    - Data persistence for future reference
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "extract_stock_data",
                    "analyze_stocks",
                    "rank_stocks",
                    "save_stock_data",
                    "get_extraction_stats"
                ],
                "description": "The action to perform"
            },
            "url": {
                "type": "string",
                "description": "URL of the financial website to extract data from"
            },
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of stock symbols to extract or analyze"
            },
            "max_retries": {
                "type": "integer",
                "description": "Maximum number of retry attempts for extraction"
            },
            "extraction_method": {
                "type": "string",
                "enum": ["auto", "table", "text", "structured", "api"],
                "description": "Method to use for data extraction"
            },
            "output_file": {
                "type": "string",
                "description": "File path to save extracted data"
            },
            "weights": {
                "type": "object",
                "description": "Custom weights for ranking stocks"
            }
        },
        "required": ["action"]
    }
    
    # Browser tool for web interactions
    browser: EnhancedBrowserTool = Field(default_factory=EnhancedBrowserTool)
    
    # Storage for extracted financial data
    stock_data: Dict[str, FinancialMetrics] = Field(default_factory=dict)
    
    # Telemetry tracking for extraction methods
    telemetry: Dict[str, ExtractionTelemetry] = Field(default_factory=dict)
    
    # Selector strategies for different financial websites
    selector_strategies: Dict[str, Dict[str, List[str]]] = Field(default_factory=lambda: {
        "yahoo_finance": {
            "price": [
                "[data-test='qsp-price']", 
                ".Fw(b).Fz(36px)",
                "fin-streamer[data-field='regularMarketPrice']"
            ],
            "company_name": [
                "h1[data-test='qsp-header']",
                ".D(ib).Mt(-5px).Fw(b).Fz(18px)"
            ],
            "table": [
                "div[data-test='left-summary-table'] table",
                "div[data-test='right-summary-table'] table",
                ".W(100%)"
            ],
            "key_stats": [
                "div#quote-summary",
                "[data-test='qsp-statistics']"
            ]
        },
        "finviz": {
            "table": [
                ".snapshot-table2",
                "table.snapshot-table"
            ],
            "price": [
                ".snapshot-td2-cp",
                "#ticker-last-price"
            ]
        },
        "marketwatch": {
            "price": [
                ".intraday__price h2",
                ".value"
            ],
            "company_name": [
                "h1.company__name"
            ],
            "table": [
                ".table--primary",
                ".element--table"
            ]
        },
        "seeking_alpha": {
            "price": [
                "div[data-test-id='symbol-price']",
                ".sa-symbol-price"
            ],
            "company_name": [
                "h1[data-test-id='symbol-title']"
            ],
            "table": [
                ".sa-table",
                "table.financial-data-table"
            ]
        },
        "generic": {
            "table": [
                "table",
                ".table",
                "[role='table']"
            ],
            "price": [
                "[data-field='price']",
                ".price",
                ".stock-price",
                ".quote-price"
            ],
            "financial_data": [
                ".financial-data",
                ".stock-data",
                ".metrics",
                ".statistics"
            ]
        }
    })
    
    # Regex patterns for extracting financial data from text
    extraction_patterns: Dict[str, str] = Field(default_factory=lambda: {
        "price": r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)",
        "market_cap": r"Market\s*Cap\s*[:\-]?\s*([\d\.]+\s*[KMBT]?)",
        "pe_ratio": r"P\/E(?:\s*Ratio)?\s*[:\-]?\s*([\d\.]+)",
        "eps": r"EPS\s*(?:\(ttm\))?\s*[:\-]?\s*([\-\d\.]+)",
        "dividend_yield": r"Dividend(?:\s*Yield)?\s*[:\-]?\s*([\d\.]+)%?",
        "volume": r"Volume\s*[:\-]?\s*([\d\.,]+[KMB]?)",
        "beta": r"Beta\s*[:\-]?\s*([\d\.]+)"
    })
    
    # Website detection patterns to identify financial websites
    website_patterns: Dict[str, List[str]] = Field(default_factory=lambda: {
        "yahoo_finance": ["finance.yahoo.com", "yahoo.com/finance"],
        "finviz": ["finviz.com"],
        "marketwatch": ["marketwatch.com"],
        "seeking_alpha": ["seekingalpha.com"],
        "investing": ["investing.com"],
        "tradingview": ["tradingview.com"],
        "morningstar": ["morningstar.com"],
        "bloomberg": ["bloomberg.com"],
        "cnbc": ["cnbc.com"]
    })
    
    # Initialize telemetry for extraction methods
    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_telemetry()
    
    def _initialize_telemetry(self):
        """Initialize telemetry tracking for all extraction methods."""
        extraction_methods = [
            "extract_from_table",
            "extract_from_text",
            "extract_structured",
            "extract_from_api",
            "extract_with_js"
        ]
        
        for method in extraction_methods:
            self.telemetry[method] = ExtractionTelemetry(method_name=method)
    
    async def _extract_stock_data(
        self,
        url: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        max_retries: int = 3,
        extraction_method: str = "auto"
    ) -> Dict[str, Any]:
        """Extract financial data for the specified stock symbols.
        
        Args:
            url: URL of the financial website to extract data from
            symbols: List of stock symbols to extract data for
            max_retries: Maximum number of retry attempts for extraction
            extraction_method: Method to use for data extraction
            
        Returns:
            Dict containing the extracted financial data
        """
        results = {}
        
        # If symbols are provided but no URL, generate URLs for each symbol
        if symbols and not url:
            for symbol in symbols:
                # Try to extract data from multiple financial websites
                symbol_data = None
                websites_tried = 0
                
                # List of financial websites to try
                websites = [
                    f"https://finance.yahoo.com/quote/{symbol}",
                    f"https://finviz.com/quote.ashx?t={symbol}",
                    f"https://www.marketwatch.com/investing/stock/{symbol}"
                ]
                
                for website_url in websites:
                    try:
                        logger.info(f"Attempting to extract data for {symbol} from {website_url}")
                        
                        # Determine website type from URL
                        website_type = self._detect_website_type(website_url)
                        
                        # Extract data with retry logic
                        symbol_data = await self._extract_with_retry(
                            url=website_url,
                            symbol=symbol,
                            website_type=website_type,
                            max_retries=max_retries,
                            extraction_method=extraction_method
                        )
                        
                        if symbol_data:
                            # Store the successful data
                            self.stock_data[symbol] = FinancialMetrics(**symbol_data)
                            results[symbol] = symbol_data
                            break
                            
                    except Exception as e:
                        logger.error(f"Error extracting data for {symbol} from {website_url}: {str(e)}")
                        websites_tried += 1
                        
                        # If we've tried all websites and still failed, log the failure
                        if websites_tried == len(websites):
                            logger.error(f"Failed to extract data for {symbol} from all websites")
                            results[symbol] = {"symbol": symbol, "error": "Failed to extract data from all sources"}
        
        # If URL is provided, extract data from that specific URL
        elif url:
            try:
                # Determine website type from URL
                website_type = self._detect_website_type(url)
                
                # If no symbol is provided, try to extract it from the URL
                symbol = None
                if symbols and len(symbols) > 0:
                    symbol = symbols[0]
                else:
                    # Try to extract symbol from URL
                    symbol_match = re.search(r"[?&/](?:t|symbol|ticker|q)=([A-Z]+)", url, re.IGNORECASE)
                    if symbol_match:
                        symbol = symbol_match.group(1).upper()
                    else:
                        # Use a generic symbol if we can't extract one
                        symbol = "UNKNOWN"
                
                # Extract data with retry logic
                data = await self._extract_with_retry(
                    url=url,
                    symbol=symbol,
                    website_type=website_type,
                    max_retries=max_retries,
                    extraction_method=extraction_method
                )
                
                if data:
                    # Store the successful data
                    self.stock_data[symbol] = FinancialMetrics(**data)
                    results[symbol] = data
                
            except Exception as e:
                logger.error(f"Error extracting data from {url}: {str(e)}")
                results["error"] = f"Failed to extract data: {str(e)}"
        
        return results
    
    def _detect_website_type(self, url: str) -> str:
        """Detect the type of financial website from the URL."""
        for website_type, patterns in self.website_patterns.items():
            if any(pattern in url.lower() for pattern in patterns):
                return website_type
        return "generic"
    
    async def _extract_with_retry(
        self,
        url: str,
        symbol: str,
        website_type: str,
        max_retries: int = 3,
        extraction_method: str = "auto"
    ) -> Dict[str, Any]:
        """Extract data with retry logic and fallback strategies.
        
        Args:
            url: URL to extract data from
            symbol: Stock symbol
            website_type: Type of financial website
            max_retries: Maximum number of retry attempts
            extraction_method: Method to use for extraction
            
        Returns:
            Dict containing the extracted financial data
        """
        # Enable stealth mode and random delays to avoid detection
        await self.browser.execute(action="stealth_mode", enable=True)
        await self.browser.execute(action="random_delay", min_delay=800, max_delay=2500)
        await self.browser.execute(action="rotate_user_agent")
        
        # Navigate to the URL
        nav_result = await self.browser.execute(action="navigate", url=url)
        if nav_result.error:
            logger.error(f"Navigation error: {nav_result.error}")
            return None
        
        # Wait for page to load
        await asyncio.sleep(3)
        
        # Determine extraction methods to try based on the specified method
        methods_to_try = []
        
        if extraction_method == "auto":
            # Try methods in order of reliability for the specific website type
            if website_type in ["yahoo_finance", "finviz", "marketwatch"]:
                methods_to_try = ["extract_structured", "extract_from_table", "extract_from_text", "extract_with_js"]
            else:
                methods_to_try = ["extract_from_table", "extract_structured", "extract_from_text", "extract_with_js"]
        else:
            # Map the specified method to the actual method name
            method_mapping = {
                "table": "extract_from_table",
                "text": "extract_from_text",
                "structured": "extract_structured",
                "api": "extract_from_api"
            }
            methods_to_try = [method_mapping.get(extraction_method, "extract_from_table")]
        
        # Try each method with retries
        for method_name in methods_to_try:
            for attempt in range(max_retries):
                try:
                    start_time = time.time()
                    
                    # Call the appropriate extraction method
                    if method_name == "extract_from_table":
                        data = await self._extract_from_table(symbol, website_type)
                    elif method_name == "extract_from_text":
                        data = await self._extract_from_text(symbol, website_type)
                    elif method_name == "extract_structured":
                        data = await self._extract_structured(symbol, website_type)
                    elif method_name == "extract_from_api":
                        data = await self._extract_from_api(symbol, website_type)
                    elif method_name == "extract_with_js":
                        data = await self._extract_with_js(symbol, website_type)
                    else:
                        continue
                    
                    execution_time = time.time() - start_time
                    
                    # Update telemetry
                    if data:
                        self.telemetry[method_name].update(True, execution_time)
                        
                        # Add metadata about extraction
                        data["data_source"] = website_type
                        data["extraction_method"] = method_name
                        data["last_updated"] = datetime.now().isoformat()
                        
                        return data
                    else:
                        self.telemetry[method_name].update(False, execution_time, "No data extracted")
                        
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.telemetry[method_name].update(False, execution_time, str(e))
                    logger.error(f"Error in {method_name} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    
                    # Add a delay before retrying
                    await asyncio.sleep(1 + attempt)
        
        # If all methods failed, return a basic structure with the symbol
        logger.error(f"All extraction methods failed for {symbol}")
        return {"symbol": symbol, "error": "All extraction methods failed"}
    
    async def _extract_from_table(self, symbol: str, website_type: str) -> Dict[str, Any]:
        """Extract financial data from tables on the page."""
        # Get selectors for this website type
        selectors = self.selector_strategies.get(website_type, self.selector_strategies["generic"])
        
        # Extract tables using the appropriate selectors
        table_selectors = selectors.get("table", ["table"])
        
        data = {"symbol": symbol}
        
        for selector in table_selectors:
            try:
                # Extract tables using the enhanced browser tool
                result = await self.browser.execute(
                    action="extract_structured",
                    selector=selector,
                    extraction_type="table"
                )
                
                if result.error:
                    logger.warning(f"Error extracting tables with selector '{selector}': {result.error}")
                    continue
                
                # Parse the JSON result
                tables = json.loads(result.output)
                
                if not tables or len(tables) == 0:
                    continue
                
                # Process each table to extract financial metrics
                for table in tables:
                    # Extract data from table rows
                    for row_idx, row in enumerate(table.get("rows", [])):
                        if len(row) < 2:
                            continue
                        
                        # First column is usually the metric name, second is the value
                        metric_name = row[0].lower()
                        metric_value = row[1]
                        
                        # Map common metric names to our standardized fields
                        self._map_metric_to_data(data, metric_name, metric_value)
                
                # If we found some data, break the loop
                if len(data) > 1:  # More than just the symbol
                    break
                    
            except Exception as e:
                logger.error(f"Error processing table with selector '{selector}': {str(e)}")
        
        # Try to get the company name and price if not already extracted
        if "company_name" not in data or "current_price" not in data:
            await self._extract_name_and_price(data, symbol, website_type)
        
        return data if len(data) > 1 else None
    
    async def _extract_from_text(self, symbol: str, website_type: str) -> Dict[str, Any]:
        """Extract financial data from text content on the page."""
        # Get the text content of the page
        result = await self.browser.execute(action="get_text")
        
        if result.error:
            logger.error(f"Error getting text content: {result.error}")
            return None
        
        text_content = result.output
        data = {"symbol": symbol}
        
        # Use regex patterns to extract financial metrics from text
        for metric, pattern in self.extraction_patterns.items():
            match = re.search(pattern, text_content)
            if match:
                value = match.group(1)
                
                # Convert value to appropriate type
                if metric == "price":
                    try:
                        data["current_price"] = float(value.replace(',', ''))
                    except ValueError:
                        pass
                elif metric == "market_cap":
                    data["market_cap"] = value
                elif metric == "pe_ratio":
                    try:
                        data["pe_ratio"] = float(value)
                    except ValueError:
                        pass
                elif metric == "eps":
                    try:
                        data["eps"] = float(value)
                    except ValueError:
                        pass
                elif metric == "dividend_yield":
                    try:
                        data["dividend_yield"] = float(value)
                    except ValueError:
                        pass
                elif metric == "volume":
                    # Convert K, M, B suffixes to actual numbers
                    try:
                        data["trading_volume"] = self._parse_volume(value)
                    except ValueError:
                        pass
                elif metric == "beta":
                    try:
                        data["beta"] = float(value)
                    except ValueError:
                        pass
        
        # Try to extract company name
        company_name_match = re.search(r"([A-Z][a-zA-Z0-9\s.,]+)\s+\([A-Z]+\)", text_content)
        if company_name_match:
            data["company_name"] = company_name_match.group(1).strip()
        
        # If we couldn't extract much data, try to get name and price directly
        if len(data) < 3:  # Symbol plus at least 2 metrics
            await self._extract_name_and_price(data, symbol, website_type)
        
        return data if len(data) > 1 else None
    
    async def _extract_structured(self, symbol: str, website_type: str) -> Dict[str, Any]:
        """Extract financial data using structured extraction approach."""
        # Use the navigate_and_extract action for comprehensive extraction
        result = await self.browser.execute(
            action="navigate_and_extract",
            url=None,  # Use current page
            extract_type="comprehensive"
        )
        
        if result.error:
            logger.error(f"Error in structured extraction: {result.error}")
            return None
        
        try:
            # Parse the JSON result
            data_str = result.output.split('\n\n', 1)[1] if '\n\n' in result.output else result.output
            comprehensive_data = json.loads(data_str)
            
            # Initialize data with symbol
            data = {"symbol": symbol}
            
            # Extract company name from metadata if available
            if "metadata" in comprehensive_data:
                metadata = comprehensive_data["metadata"]
                if "title" in metadata:
                    # Extract company name from title (usually in format "Company Name (SYMBOL)")
                    title = metadata["title"]
                    company_match = re.search(r"([^(]+)\s*\([^)]+\)", title)
                    if company_match:
                        data["company_name"] = company_match.group(1).strip()
            
            # Extract price from text content
            if "text" in comprehensive_data:
                text_content = comprehensive_data["text"]
                
                # Try to extract price using regex
                price_match = re.search(self.extraction_patterns["price"], text_content)
                if price_match:
                    try:
                        data["current_price"] = float(price_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
                
                # Extract other metrics using regex patterns
                for metric, pattern in self.extraction_patterns.items():
                    if metric == "price":
                        continue  # Already handled
                        
                    match = re.search(pattern, text_content)
                    if match:
                        value = match.group(1)
                        self._map_metric_to_data(data, metric, value)
            
            # Extract data from tables if available
            if "tables" in comprehensive_data:
                tables = comprehensive_data["tables"]
                for table in tables:
                    # Process table rows
                    for row in table.get("rows", []):
                        if len(row) < 2:
                            continue
                            
                        # First column is usually the metric name, second is the value
                        metric_name = row[0].lower()
                        metric_value = row[1]
                        
                        # Map common metric names to our standardized fields
                        self._map_metric_to_data(data, metric_name, metric_value)
            
            return data if len(data) > 1 else None
            
        except Exception as e:
            logger.error(f"Error processing structured extraction result: {str(e)}")
            return None
    
    async def _extract_from_api(self, symbol: str, website_type: str) -> Dict[str, Any]:
        """Extract financial data from API endpoints if available."""
        # This is a placeholder for API-based extraction
        # In a real implementation, this would make API calls to financial data providers
        # For now, we'll return None to indicate this method is not implemented
        logger.warning("API-based extraction not implemented yet")
        return None
    
    async def _extract_with_js(self, symbol: str, website_type: str) -> Dict[str, Any]:
        """Extract financial data using custom JavaScript injection."""
        # Prepare a JavaScript extraction script based on the website type
        extraction_script = """
        function extractFinancialData() {
            const data = {
                metrics: {}
            };
            
            // Try to extract price
            const priceElements = [
                document.querySelector('[data-test="qsp-price"]'),
                document.querySelector('.Fw\\(b\\).Fz\\(36px\\)'),
                document.querySelector('fin-streamer[data-field="regularMarketPrice"]'),
                document.querySelector('.price'),
                document.querySelector('.stock-price'),
                document.querySelector('.quote-price'),
                document.querySelector('.intraday__price h2'),
                document.querySelector('.value')
            ].filter(el => el !== null);
            
            if (priceElements.length > 0) {
                const priceText = priceElements[0].innerText.trim();
                const priceMatch = priceText.match(/[\\d,.]+/);
                if (priceMatch) {
                    data.metrics.price = priceMatch[0].replace(/,/g, '');
                }
            }
            
            // Try to extract company name
            const nameElements = [
                document.querySelector('h1[data-test="qsp-header"]'),
                document.querySelector('.D\\(ib\\).Mt\\(-5px\\).Fw\\(b\\).Fz\\(18px\\)'),
                document.querySelector('h1.company__name'),
                document.querySelector('h1[data-test-id="symbol-title"]')
            ].filter(el => el !== null);
            
            if (nameElements.length > 0) {
                data.companyName = nameElements[0].innerText.trim();
            }
            
            // Extract metrics from tables
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                for (const row of rows) {
                    const cells = row.querySelectorAll('td, th');
                    if (cells.length >= 2) {
                        const label = cells[0].innerText.trim().toLowerCase();
                        const value = cells[1].innerText.trim();
                        
                        // Store all metrics
                        data.metrics[label] = value;
                    }
                }
            }
            
            return data;
        }
        
        return extractFinancialData();
        """
        
        try:
            # Execute the JavaScript extraction script
            result = await self.browser.execute(action="execute_js", script=extraction_script)
            
            if result.error:
                logger.error(f"Error executing JavaScript extraction: {result.error}")
                return None
            
            # Parse the result
            js_data = json.loads(result.output)
            
            # Convert to our standard format
            data = {"symbol": symbol}
            
            # Add company name if available
            if "companyName" in js_data:
                data["company_name"] = js_data["companyName"]
            
            # Process metrics
            if "metrics" in js_data:
                metrics = js_data["metrics"]
                
                # Extract price
                if "price" in metrics:
                    try:
                        data["current_price"] = float(metrics["price"])
                    except ValueError:
                        pass
                
                # Map other metrics
                for metric_name, metric_value in metrics.items():
                    self._map_metric_to_data(data, metric_name, metric_value)
            
            return data if len(data) > 1 else None
            
        except Exception as e:
            logger.error(f"Error in JavaScript extraction: {str(e)}")
            return None
    
    async def _extract_name_and_price(self, data: Dict[str, Any], symbol: str, website_type: str):
        """Extract basic company name and price information."""
        # Get selectors for this website type
        selectors = self.selector_strategies.get(website_type, self.selector_strategies["generic"])
        
        # Try to extract company name
        if "company_name" not in data:
            for selector in selectors.get("company_name", []):
                try:
                    result = await self.browser.execute(
                        action="extract_structured",
                        selector=selector,
                        extraction_type="text"
                    )
                    
                    if not result.error and result.output:
                        elements = json.loads(result.output)
                        if elements and len(elements) > 0:
                            data["company_name"] = elements[0]["text"]
                            break
                except Exception as e:
                    logger.error(f"Error extracting company name: {str(e)}")
        
        # Try to extract price
        if "current_price" not in data:
            for selector in selectors.get("price", []):
                try:
                    result = await self.browser.execute(
                        action="extract_structured",
                        selector=selector,
                        extraction_type="text"
                    )
                    
                    if not result.error and result.output:
                        elements = json.loads(result.output)
                        if elements and len(elements) > 0:
                            price_text = elements[0]["text"]
                            price_match = re.search(r"[\d,.]+", price_text)
                            if price_match:
                                try:
                                    data["current_price"] = float(price_match.group(0).replace(',', ''))
                                    break
                                except ValueError:
                                    pass
                except Exception as e:
                    logger.error(f"Error extracting price: {str(e)}")
    
    def _map_metric_to_data(self, data: Dict[str, Any], metric_name: str, metric_value: str):
        """Map common metric names to standardized fields in our data structure."""
        # Convert metric name to lowercase and remove special characters for better matching
        clean_name = re.sub(r'[^a-z0-9\s]', '', metric_name.lower())
        
        # Map for common metric names
        metric_mapping = {
            # Price and basic info
            "price": "current_price",
            "last price": "current_price",
            "current price": "current_price",
            "change": "price_change",
            "chg": "price_change",
            "change percent": "price_change_percent",
            "chg percent": "price_change_percent",
            
            # Market data
            "market cap": "market_cap",
            "marketcap": "market_cap",
            "volume": "trading_volume",
            "avg volume": "trading_volume",
            "average volume": "trading_volume",
            
            # Valuation metrics
            "pe": "pe_ratio",
            "pe ratio": "pe_ratio",
            "priceearnings": "pe_ratio",
            "eps": "eps",
            "earnings per share": "eps",
            "dividend": "dividend_yield",
            "dividend yield": "dividend_yield",
            "yield": "dividend_yield",
            
            # Growth metrics
            "revenue growth": "revenue_growth",
            "sales growth": "revenue_growth",
            "profit margin": "profit_margin",
            "operating margin": "profit_margin",
            
            # Financial health
            "debt to equity": "debt_to_equity",
            "debtequity": "debt_to_equity",
            "roe": "roe",
            "return on equity": "roe",
            
            # Technical indicators
            "rsi": "rsi",
            "relative strength index": "rsi",
            "50day ma": "moving_avg_50d",
            "50 day": "moving_avg_50d",
            "200day ma": "moving_avg_200d",
            "200 day": "moving_avg_200d",
            "beta": "beta",
            
            # Classification
            "sector": "sector",
            "industry": "industry",
            
            # Analyst opinions
            "analyst rating": "analyst_rating",
            "recommendation": "analyst_rating",
            "target price": "price_target",
            "price target": "price_target"
        }
        
        # Try to find a match in our mapping
        target_field = None
        for key, field in metric_mapping.items():
            if key in clean_name or clean_name in key:
                target_field = field
                break
        
        # If we found a matching field, try to convert and store the value
        if target_field:
            try:
                # Handle different value types
                if target_field in ["current_price", "price_change", "eps", "pe_ratio", 
                                  "dividend_yield", "revenue_growth", "profit_margin", 
                                  "debt_to_equity", "roe", "rsi", "moving_avg_50d", 
                                  "moving_avg_200d", "beta", "price_target"]:
                    # Extract numeric value
                    numeric_match = re.search(r"-?[\d.,]+", str(metric_value))
                    if numeric_match:
                        # Convert to float, handling commas in numbers
                        value = float(numeric_match.group(0).replace(',', ''))
                        
                        # Handle percentages
                        if target_field in ["price_change_percent", "dividend_yield", "revenue_growth", "profit_margin", "roe"] and "%" in str(metric_value):
                            value /= 100.0
                            
                        data[target_field] = value
                        
                elif target_field == "trading_volume":
                    # Handle volume with K, M, B suffixes
                    data[target_field] = self._parse_volume(metric_value)
                    
                elif target_field in ["market_cap"]:
                    # Store as string with original formatting
                    data[target_field] = str(metric_value).strip()
                    
                elif target_field in ["sector", "industry", "analyst_rating", "company_name"]:
                    # Store as string
                    data[target_field] = str(metric_value).strip()
                    
            except Exception as e:
                logger.error(f"Error mapping {metric_name} to {target_field}: {str(e)}")
    
    def _parse_volume(self, volume_str: str) -> int:
        """Parse volume string with K, M, B suffixes into integer."""
        try:
            volume_str = str(volume_str).strip().upper()
            if not volume_str:
                return 0
                
            # Extract numeric part
            numeric_match = re.search(r"([\d.,]+)", volume_str)
            if not numeric_match:
                return 0
                
            # Convert to float, handling commas
            value = float(numeric_match.group(1).replace(',', ''))
            
            # Apply multiplier based on suffix
            if 'K' in volume_str:
                value *= 1_000
            elif 'M' in volume_str:
                value *= 1_000_000
            elif 'B' in volume_str:
                value *= 1_000_000_000
                
            return int(value)
        except Exception as e:
            logger.error(f"Error parsing volume {volume_str}: {str(e)}")
            return 0
    
    async def _analyze_stocks(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze financial data for the specified stock symbols.
        
        Args:
            symbols: List of stock symbols to analyze. If None, analyze all stocks in stock_data.
            
        Returns:
            Dict containing the analysis results
        """
        results = {}
        
        # Determine which symbols to analyze
        symbols_to_analyze = symbols if symbols else list(self.stock_data.keys())
        
        for symbol in symbols_to_analyze:
            if symbol not in self.stock_data:
                results[symbol] = {"error": "No data available for analysis"}
                continue
                
            stock = self.stock_data[symbol]
            analysis = {}
            
            # Basic information
            analysis["symbol"] = symbol
            analysis["company_name"] = stock.company_name
            analysis["current_price"] = stock.current_price
            
            # Valuation analysis
            if stock.pe_ratio is not None:
                if stock.pe_ratio < 0:
                    analysis["pe_ratio_analysis"] = "Negative P/E ratio indicates the company is not profitable."
                elif stock.pe_ratio < 15:
                    analysis["pe_ratio_analysis"] = "P/E ratio below 15 suggests the stock may be undervalued."
                elif stock.pe_ratio < 25:
                    analysis["pe_ratio_analysis"] = "P/E ratio between 15-25 is in the moderate valuation range."
                else:
                    analysis["pe_ratio_analysis"] = "P/E ratio above 25 suggests the stock may be overvalued."
            
            # Dividend analysis
            if stock.dividend_yield is not None:
                if stock.dividend_yield == 0:
                    analysis["dividend_analysis"] = "The stock does not pay dividends."
                elif stock.dividend_yield < 0.02:
                    analysis["dividend_analysis"] = "Low dividend yield below 2%."
                elif stock.dividend_yield < 0.04:
                    analysis["dividend_analysis"] = "Moderate dividend yield between 2-4%."
                else:
                    analysis["dividend_analysis"] = "High dividend yield above 4%."
            
            # Growth analysis
            if stock.revenue_growth is not None:
                if stock.revenue_growth < 0:
                    analysis["growth_analysis"] = "Negative revenue growth indicates declining sales."
                elif stock.revenue_growth < 0.05:
                    analysis["growth_analysis"] = "Slow revenue growth below 5%."
                elif stock.revenue_growth < 0.15:
                    analysis["growth_analysis"] = "Moderate revenue growth between 5-15%."
                else:
                    analysis["growth_analysis"] = "Strong revenue growth above 15%."
            
            # Financial health analysis
            if stock.debt_to_equity is not None:
                if stock.debt_to_equity < 0.3:
                    analysis["financial_health"] = "Low debt-to-equity ratio indicates strong financial health."
                elif stock.debt_to_equity < 1.0:
                    analysis["financial_health"] = "Moderate debt-to-equity ratio."
                else:
                    analysis["financial_health"] = "High debt-to-equity ratio indicates potential financial risk."
            
            # Technical analysis
            if stock.rsi is not None:
                if stock.rsi < 30:
                    analysis["technical_analysis"] = "RSI below 30 suggests the stock may be oversold."
                elif stock.rsi > 70:
                    analysis["technical_analysis"] = "RSI above 70 suggests the stock may be overbought."
                else:
                    analysis["technical_analysis"] = "RSI between 30-70 indicates neutral momentum."
            
            # Moving average analysis
            if stock.moving_avg_50d is not None and stock.moving_avg_200d is not None and stock.current_price is not None:
                if stock.current_price > stock.moving_avg_50d and stock.moving_avg_50d > stock.moving_avg_200d:
                    analysis["moving_average_analysis"] = "Price above both 50-day and 200-day moving averages indicates a strong uptrend."
                elif stock.current_price < stock.moving_avg_50d and stock.moving_avg_50d < stock.moving_avg_200d:
                    analysis["moving_average_analysis"] = "Price below both 50-day and 200-day moving averages indicates a strong downtrend."
                elif stock.moving_avg_50d > stock.moving_avg_200d:
                    analysis["moving_average_analysis"] = "50-day moving average above 200-day moving average indicates a bullish trend (golden cross)."
                elif stock.moving_avg_50d < stock.moving_avg_200d:
                    analysis["moving_average_analysis"] = "50-day moving average below 200-day moving average indicates a bearish trend (death cross)."
            
            # Overall recommendation
            analysis["recommendation"] = self._generate_recommendation(stock)
            
            # Calculate a score for the stock
            analysis["score"] = stock.calculate_score()
            
            results[symbol] = analysis
        
        return results
    
    def _generate_recommendation(self, stock: FinancialMetrics) -> str:
        """Generate a recommendation based on the stock's metrics."""
        # Count positive and negative factors
        positive_factors = 0
        negative_factors = 0
        neutral_factors = 0
        
        # Valuation factors
        if stock.pe_ratio is not None:
            if stock.pe_ratio > 0 and stock.pe_ratio < 15:
                positive_factors += 1
            elif stock.pe_ratio > 30:
                negative_factors += 1
            else:
                neutral_factors += 1
        
        # Growth factors
        if stock.revenue_growth is not None:
            if stock.revenue_growth > 0.1:  # 10% growth
                positive_factors += 1
            elif stock.revenue_growth < 0:
                negative_factors += 1
            else:
                neutral_factors += 1
        
        # Profitability factors
        if stock.profit_margin is not None:
            if stock.profit_margin > 0.15:  # 15% margin
                positive_factors += 1
            elif stock.profit_margin < 0:
                negative_factors += 1
            else:
                neutral_factors += 1
        
        # Financial health factors
        if stock.debt_to_equity is not None:
            if stock.debt_to_equity < 0.5:
                positive_factors += 1
            elif stock.debt_to_equity > 1.5:
                negative_factors += 1
            else:
                neutral_factors += 1
        
        # Technical factors
        if stock.rsi is not None:
            if stock.rsi < 30:
                positive_factors += 1  # Oversold, potential buy
            elif stock.rsi > 70:
                negative_factors += 1  # Overbought, potential sell
            else:
                neutral_factors += 1
        
        # Moving average factors
        if stock.moving_avg_50d is not None and stock.moving_avg_200d is not None and stock.current_price is not None:
            if stock.current_price > stock.moving_avg_50d and stock.moving_avg_50d > stock.moving_avg_200d:
                positive_factors += 1
            elif stock.current_price < stock.moving_avg_50d and stock.moving_avg_50d < stock.moving_avg_200d:
                negative_factors += 1
            else:
                neutral_factors += 1
        
        # Generate recommendation based on factors
        if positive_factors >= 3 and positive_factors > negative_factors + 1:
            return "Strong Buy"
        elif positive_factors > negative_factors:
            return "Buy"
        elif negative_factors > positive_factors + 1:
            return "Sell"
        elif negative_factors > positive_factors:
            return "Reduce"
        else:
            return "Hold"
    
    async def _rank_stocks(self, symbols: Optional[List[str]] = None, weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Rank stocks based on their financial metrics and custom weights.
        
        Args:
            symbols: List of stock symbols to rank. If None, rank all stocks in stock_data.
            weights: Custom weights for ranking. If None, use default weights.
            
        Returns:
            Dict containing the ranked stocks and their scores
        """
        # Determine which symbols to rank
        symbols_to_rank = symbols if symbols else list(self.stock_data.keys())
        
        # Filter out symbols that don't have data
        valid_symbols = [symbol for symbol in symbols_to_rank if symbol in self.stock_data]
        
        if not valid_symbols:
            return {"error": "No valid stock data available for ranking"}
        
        # Calculate scores for each stock
        scores = []
        for symbol in valid_symbols:
            stock = self.stock_data[symbol]
            score = stock.calculate_score(weights)
            
            scores.append({
                "symbol": symbol,
                "company_name": stock.company_name,
                "score": score,
                "current_price": stock.current_price,
                "recommendation": self._generate_recommendation(stock),
                "key_metrics": {
                    "pe_ratio": stock.pe_ratio,
                    "eps": stock.eps,
                    "revenue_growth": stock.revenue_growth,
                    "profit_margin": stock.profit_margin,
                    "debt_to_equity": stock.debt_to_equity,
                    "dividend_yield": stock.dividend_yield
                }
            })
        
        # Sort stocks by score in descending order
        ranked_stocks = sorted(scores, key=lambda x: x["score"], reverse=True)
        
        # Add rank to each stock
        for i, stock in enumerate(ranked_stocks):
            stock["rank"] = i + 1
        
        # Generate summary of ranking criteria
        summary = {
            "ranking_criteria": "Stocks ranked based on a weighted combination of financial metrics",
            "weights_used": weights if weights else "default weights",
            "number_of_stocks_ranked": len(ranked_stocks),
            "top_performer": ranked_stocks[0]["symbol"] if ranked_stocks else None,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "ranked_stocks": ranked_stocks,
            "summary": summary
        }
    
    async def _load_stock_data(self, input_file: str) -> Dict[str, Any]:
        """Load stock data from a file.
        
        Args:
            input_file: File path to load the data from
            
        Returns:
            Dict containing the loaded stock data
        """
        try:
            with open(input_file, "r") as f:
                data = json.load(f)
            
            if "stocks" not in data:
                return {"error": "Invalid stock data file format"}
            
            # Convert loaded data to FinancialMetrics objects
            for symbol, stock_dict in data["stocks"].items():
                self.stock_data[symbol] = FinancialMetrics(**stock_dict)
            
            return {
                "success": True,
                "message": f"Successfully loaded data for {len(data['stocks'])} stocks from {input_file}",
                "symbols_loaded": list(data["stocks"].keys())
            }
            
        except Exception as e:
            logger.error(f"Error loading stock data: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to load stock data: {str(e)}"
            }
    
    async def _save_stock_data(self, output_file: str, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Save extracted stock data to a file.
        
        Args:
            output_file: File path to save the data
            symbols: List of stock symbols to save. If None, save all stocks in stock_data.
            
        Returns:
            Dict containing the result of the save operation
        """
        try:
            # Determine which symbols to save
            symbols_to_save = symbols if symbols else list(self.stock_data.keys())
            
            # Filter out symbols that don't have data
            valid_symbols = [symbol for symbol in symbols_to_save if symbol in self.stock_data]
            
            if not valid_symbols:
                return {"error": "No valid stock data available to save"}
            
            # Prepare data for saving
            data_to_save = {}
            for symbol in valid_symbols:
                # Convert FinancialMetrics to dict
                stock_dict = self.stock_data[symbol].dict()
                # Convert datetime to string for JSON serialization
                if "last_updated" in stock_dict and isinstance(stock_dict["last_updated"], datetime):
                    stock_dict["last_updated"] = stock_dict["last_updated"].isoformat()
                data_to_save[symbol] = stock_dict
            
            # Add metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "total_stocks": len(valid_symbols),
                "symbols": valid_symbols
            }
            
            # Create the final data structure
            final_data = {
                "metadata": metadata,
                "stocks": data_to_save
            }
            
            # Save to file
            with open(output_file, "w") as f:
                json.dump(final_data, f, indent=2)
            
            return {
                "success": True,
                "message": f"Successfully saved data for {len(valid_symbols)} stocks to {output_file}",
                "file_path": output_file,
                "symbols_saved": valid_symbols
            }
            
        except Exception as e:
            logger.error(f"Error saving stock data: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save stock data: {str(e)}"
            }
    
    def _get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about extraction methods performance.
        
        Returns:
            Dict containing extraction statistics
        """
        stats = {
            "methods": {},
            "overall": {
                "total_success": 0,
                "total_failure": 0,
                "success_rate": 0.0,
                "average_execution_time": 0.0
            }
        }
        
        # Calculate overall statistics
        total_success = 0
        total_failure = 0
        total_execution_time = 0.0
        method_count = 0
        
        # Process each method's telemetry
        for method_name, telemetry in self.telemetry.items():
            method_stats = {
                "success_count": telemetry.success_count,
                "failure_count": telemetry.failure_count,
                "total_executions": telemetry.success_count + telemetry.failure_count,
                "success_rate": 0.0,
                "average_execution_time": telemetry.average_execution_time,
                "last_status": telemetry.last_status,
                "last_error": telemetry.last_error
            }
            
            # Calculate success rate if there were any executions
            if method_stats["total_executions"] > 0:
                method_stats["success_rate"] = (telemetry.success_count / method_stats["total_executions"]) * 100.0
            
            # Add to overall counts
            total_success += telemetry.success_count
            total_failure += telemetry.failure_count
            total_execution_time += telemetry.average_execution_time
            method_count += 1
            
            # Add to stats dictionary
            stats["methods"][method_name] = method_stats
        
        # Calculate overall statistics
        total_executions = total_success + total_failure
        if total_executions > 0:
            stats["overall"]["success_rate"] = (total_success / total_executions) * 100.0
        
        if method_count > 0:
            stats["overall"]["average_execution_time"] = total_execution_time / method_count
        
        stats["overall"]["total_success"] = total_success
        stats["overall"]["total_failure"] = total_failure
        stats["overall"]["total_executions"] = total_executions
        stats["overall"]["timestamp"] = datetime.now().isoformat()
        
        # Add recommendations based on statistics
        stats["recommendations"] = self._generate_extraction_recommendations(stats)
        
        return stats
    
    def _generate_extraction_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving extraction based on statistics.
        
        Args:
            stats: Dictionary containing extraction statistics
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check overall success rate
        overall_success_rate = stats["overall"]["success_rate"]
        if overall_success_rate < 50.0:
            recommendations.append("Overall extraction success rate is below 50%. Consider reviewing and improving extraction strategies.")
        
        # Find the best and worst performing methods
        method_stats = stats["methods"]
        if method_stats:
            # Sort methods by success rate
            sorted_methods = sorted(
                [(name, data) for name, data in method_stats.items() if data["total_executions"] > 0],
                key=lambda x: x[1]["success_rate"],
                reverse=True
            )
            
            if sorted_methods:
                best_method = sorted_methods[0]
                worst_method = sorted_methods[-1]
                
                # Add recommendations based on best and worst methods
                if best_method[1]["success_rate"] > 70.0:
                    recommendations.append(f"The '{best_method[0]}' method has a high success rate ({best_method[1]['success_rate']:.1f}%). Consider prioritizing this method.")
                
                if worst_method[1]["success_rate"] < 30.0 and worst_method[1]["total_executions"] > 5:
                    recommendations.append(f"The '{worst_method[0]}' method has a low success rate ({worst_method[1]['success_rate']:.1f}%). Consider improving or deprioritizing this method.")
        
        # Check for methods with high execution times
        slow_methods = [name for name, data in method_stats.items() 
                       if data["average_execution_time"] > 5.0 and data["total_executions"] > 5]
        
        if slow_methods:
            recommendations.append(f"The following methods have high average execution times: {', '.join(slow_methods)}. Consider optimizing these methods.")
        
        # Add general recommendations if no specific issues found
        if not recommendations:
            recommendations.append("All extraction methods are performing well. Continue monitoring for any changes in performance.")
        
        return recommendations
    
    async def _load_stock_data(self, input_file: str) -> Dict[str, Any]:
        """Load stock data from a file.
        
        Args:
            input_file: File path to load the data from
            
        Returns:
            Dict containing the loaded stock data
        """
        try:
            with open(input_file, "r") as f:
                data = json.load(f)
            
            if "stocks" not in data:
                return {"error": "Invalid stock data file format"}
            
            # Convert loaded data to FinancialMetrics objects
            for symbol, stock_dict in data["stocks"].items():
                self.stock_data[symbol] = FinancialMetrics(**stock_dict)
            
            return {
                "success": True,
                "message": f"Successfully loaded data for {len(data['stocks'])} stocks from {input_file}",
                "symbols_loaded": list(data["stocks"].keys())
            }
            
        except Exception as e:
            logger.error(f"Error loading stock data: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to load stock data: {str(e)}"
            }
    
    async def _save_stock_data(self, output_file: str, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Save extracted stock data to a file.
        
        Args:
            output_file: File path to save the data
            symbols: List of stock symbols to save. If None, save all stocks in stock_data.
            
        Returns:
            Dict containing the result of the save operation
        """
        try:
            # Determine which symbols to save
            symbols_to_save = symbols if symbols else list(self.stock_data.keys())
            
            # Filter out symbols that don't have data
            valid_symbols = [symbol for symbol in symbols_to_save if symbol in self.stock_data]
            
            if not valid_symbols:
                return {"error": "No valid stock data available to save"}
            
            # Prepare data for saving
            data_to_save = {}
            for symbol in valid_symbols:
                # Convert FinancialMetrics to dict
                stock_dict = self.stock_data[symbol].dict()
                # Convert datetime to string for JSON serialization
                if "last_updated" in stock_dict and isinstance(stock_dict["last_updated"], datetime):
                    stock_dict["last_updated"] = stock_dict["last_updated"].isoformat()
                data_to_save[symbol] = stock_dict
            
            # Add metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "total_stocks": len(valid_symbols),
                "symbols": valid_symbols
            }
            
            # Create the final data structure
            final_data = {
                "metadata": metadata,
                "stocks": data_to_save
            }
            
            # Save to file
            with open(output_file, "w") as f:
                json.dump(final_data, f, indent=2)
            
            return {
                "success": True,
                "message": f"Successfully saved data for {len(valid_symbols)} stocks to {output_file}",
                "file_path": output_file,
                "symbols_saved": valid_symbols
            }
            
        except Exception as e:
            logger.error(f"Error saving stock data: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save stock data: {str(e)}"
            }
    
    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        max_retries: int = 3,
        extraction_method: str = "auto",
        output_file: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> ToolResult:
        """Execute the financial data extractor tool.
        
        Args:
            action: The action to perform
            url: URL of the financial website to extract data from
            symbols: List of stock symbols to extract or analyze
            max_retries: Maximum number of retry attempts for extraction
            extraction_method: Method to use for data extraction
            output_file: File path to save extracted data
            weights: Custom weights for ranking stocks
            **kwargs: Additional arguments
            
        Returns:
            ToolResult with the action's output or error
        """
        try:
            if action == "extract_stock_data":
                if not url and not symbols:
                    return ToolResult(error="Either URL or symbols must be provided for extraction")
                
                result = await self._extract_stock_data(
                    url=url,
                    symbols=symbols,
                    max_retries=max_retries,
                    extraction_method=extraction_method
                )
                return ToolResult(output=result)
                
            elif action == "analyze_stocks":
                if not symbols and not self.stock_data:
                    return ToolResult(error="No stock data available for analysis")
                
                result = await self._analyze_stocks(symbols=symbols)
                return ToolResult(output=result)
                
            elif action == "rank_stocks":
                if not symbols and not self.stock_data:
                    return ToolResult(error="No stock data available for ranking")
                
                result = await self._rank_stocks(symbols=symbols, weights=weights)
                return ToolResult(output=result)
                
            elif action == "save_stock_data":
                if not output_file:
                    return ToolResult(error="Output file path must be provided for saving data")
                
                result = await self._save_stock_data(output_file=output_file, symbols=symbols)
                return ToolResult(output=result)
                
            elif action == "get_extraction_stats":
                result = self._get_extraction_stats()
                return ToolResult(output=result)
                
            else:
                return ToolResult(error=f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Error executing {action}: {str(e)}")
            return ToolResult(error=f"Error executing {action}: {str(e)}")