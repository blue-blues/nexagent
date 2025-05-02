"""
Structured Data Extractor for Nexagent.

This module provides tools for extracting structured data from web pages,
including JSON-LD, Microdata, and RDFa formats.
"""

from typing import Dict, List, Any, Optional
import json
import re
from bs4 import BeautifulSoup

from app.logger import logger
from app.tools.base import BaseTool, ToolResult

class StructuredDataExtractor(BaseTool):
    """
    Tool for extracting structured data from web pages.
    
    This tool can extract various types of structured data including:
    - JSON-LD
    - Microdata
    - RDFa
    - Custom extraction patterns
    """
    
    name: str = "structured_data_extractor"
    description: str = """
    Extract structured data from web pages in various formats including JSON-LD, Microdata, and RDFa.
    Can also extract data using custom patterns for specific websites.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "html": {
                "type": "string",
                "description": "The HTML content to extract data from",
            },
            "url": {
                "type": "string",
                "description": "The URL of the page (used for custom extraction patterns)",
            },
            "extraction_type": {
                "type": "string",
                "description": "The type of extraction to perform (jsonld, microdata, rdfa, custom, all)",
                "enum": ["jsonld", "microdata", "rdfa", "custom", "all"],
                "default": "all",
            },
            "custom_patterns": {
                "type": "object",
                "description": "Custom extraction patterns to use (only for custom extraction)",
            },
        },
        "required": ["html"],
    }
    
    async def execute(
        self,
        html: str,
        url: Optional[str] = None,
        extraction_type: str = "all",
        custom_patterns: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Extract structured data from HTML content.
        
        Args:
            html: The HTML content to extract data from
            url: The URL of the page (used for custom extraction patterns)
            extraction_type: The type of extraction to perform
            custom_patterns: Custom extraction patterns to use
            
        Returns:
            ToolResult containing the extracted structured data
        """
        try:
            results = {}
            
            # Create BeautifulSoup object
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract data based on extraction type
            if extraction_type in ["jsonld", "all"]:
                jsonld_data = self._extract_jsonld(soup)
                if jsonld_data:
                    results["jsonld"] = jsonld_data
            
            if extraction_type in ["microdata", "all"]:
                microdata = self._extract_microdata(soup)
                if microdata:
                    results["microdata"] = microdata
            
            if extraction_type in ["rdfa", "all"]:
                rdfa_data = self._extract_rdfa(soup)
                if rdfa_data:
                    results["rdfa"] = rdfa_data
            
            if extraction_type in ["custom", "all"] and url and custom_patterns:
                custom_data = self._extract_custom(soup, url, custom_patterns)
                if custom_data:
                    results["custom"] = custom_data
            
            if not results:
                return ToolResult(output="No structured data found in the provided HTML")
            
            return ToolResult(output=json.dumps(results, indent=2))
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            return ToolResult(error=f"Error extracting structured data: {str(e)}")
    
    def _extract_jsonld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract JSON-LD data from HTML.
        
        Args:
            soup: BeautifulSoup object of the HTML
            
        Returns:
            List of JSON-LD objects
        """
        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        result = []
        
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                result.append(data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error parsing JSON-LD: {str(e)}")
        
        return result
    
    def _extract_microdata(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract Microdata from HTML.
        
        Args:
            soup: BeautifulSoup object of the HTML
            
        Returns:
            List of Microdata objects
        """
        items = soup.find_all(itemscope=True)
        result = []
        
        for item in items:
            item_data = self._extract_item(item)
            if item_data:
                result.append(item_data)
        
        return result
    
    def _extract_item(self, item) -> Dict[str, Any]:
        """
        Extract a single Microdata item.
        
        Args:
            item: BeautifulSoup tag with itemscope
            
        Returns:
            Dictionary of item properties
        """
        result = {}
        
        # Get item type
        if item.has_attr('itemtype'):
            result['@type'] = item['itemtype']
        
        # Get item id
        if item.has_attr('itemid'):
            result['@id'] = item['itemid']
        
        # Get item properties
        props = item.find_all(itemprop=True)
        for prop in props:
            prop_name = prop['itemprop']
            prop_value = self._get_prop_value(prop)
            
            if prop_name in result:
                if isinstance(result[prop_name], list):
                    result[prop_name].append(prop_value)
                else:
                    result[prop_name] = [result[prop_name], prop_value]
            else:
                result[prop_name] = prop_value
        
        return result
    
    def _get_prop_value(self, prop):
        """
        Get the value of a Microdata property.
        
        Args:
            prop: BeautifulSoup tag with itemprop
            
        Returns:
            Property value
        """
        # Check for nested items
        if prop.has_attr('itemscope'):
            return self._extract_item(prop)
        
        # Get value based on tag type
        tag_name = prop.name.lower()
        
        if tag_name == 'meta':
            return prop.get('content', '')
        elif tag_name == 'img':
            return prop.get('src', '')
        elif tag_name == 'a':
            return prop.get('href', '')
        elif tag_name == 'time':
            return prop.get('datetime', prop.text.strip())
        elif tag_name in ['link', 'area']:
            return prop.get('href', '')
        elif tag_name in ['audio', 'embed', 'iframe', 'img', 'source', 'track', 'video']:
            return prop.get('src', '')
        elif tag_name == 'data':
            return prop.get('value', prop.text.strip())
        else:
            return prop.text.strip()
    
    def _extract_rdfa(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract RDFa data from HTML.
        
        Args:
            soup: BeautifulSoup object of the HTML
            
        Returns:
            List of RDFa objects
        """
        # Find all elements with RDFa attributes
        rdfa_elements = soup.find_all(lambda tag: any(attr in tag.attrs for attr in 
                                                    ['typeof', 'property', 'resource', 'about']))
        
        result = []
        current_item = None
        
        for element in rdfa_elements:
            if 'typeof' in element.attrs:
                # Start a new item
                current_item = {
                    '@type': element['typeof']
                }
                
                if 'about' in element.attrs:
                    current_item['@id'] = element['about']
                elif 'resource' in element.attrs:
                    current_item['@id'] = element['resource']
                
                result.append(current_item)
            
            if 'property' in element.attrs and current_item is not None:
                prop_name = element['property']
                prop_value = element.text.strip()
                
                if 'content' in element.attrs:
                    prop_value = element['content']
                
                if prop_name in current_item:
                    if isinstance(current_item[prop_name], list):
                        current_item[prop_name].append(prop_value)
                    else:
                        current_item[prop_name] = [current_item[prop_name], prop_value]
                else:
                    current_item[prop_name] = prop_value
        
        return result
    
    def _extract_custom(self, soup: BeautifulSoup, url: str, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data using custom patterns for specific websites.
        
        Args:
            soup: BeautifulSoup object of the HTML
            url: URL of the page
            patterns: Custom extraction patterns
            
        Returns:
            Dictionary of extracted data
        """
        result = {}
        
        # Find matching pattern for the URL
        for pattern_name, pattern_data in patterns.items():
            if 'url_pattern' in pattern_data and re.search(pattern_data['url_pattern'], url):
                # Apply the pattern
                for field_name, selector in pattern_data.get('selectors', {}).items():
                    elements = soup.select(selector)
                    if elements:
                        if pattern_data.get('multiple', False):
                            result[field_name] = [elem.text.strip() for elem in elements]
                        else:
                            result[field_name] = elements[0].text.strip()
        
        return result
