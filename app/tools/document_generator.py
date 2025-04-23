"""Document generator tool for creating formatted documents.

This tool generates formatted documents from structured data, such as
travel itineraries, research reports, and data analysis results.
"""

from typing import Dict, Any, Optional, List
import os
import json
import uuid
import datetime

from pydantic import BaseModel, Field

from app.core.tools.base_tool import BaseTool
from app.logger import logger


class DocumentGenerator(BaseTool):
    """Tool for generating formatted documents from structured data."""
    
    name: str = "document_generator"
    description: str = "Generate formatted documents from structured data"
    
    async def _run(self, document_type: str, data: Dict[str, Any], output_format: str = "html") -> str:
        """
        Generate a document from structured data.
        
        Args:
            document_type: Type of document to generate (e.g., "travel_itinerary")
            data: Structured data for the document
            output_format: Output format (html, markdown, pdf)
            
        Returns:
            str: Path to the generated document
        """
        if document_type == "travel_itinerary":
            return await self._generate_travel_itinerary(data, output_format)
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
    
    async def _generate_travel_itinerary(self, data: Dict[str, Any], output_format: str) -> str:
        """Generate a travel itinerary document."""
        # Create a unique filename
        filename = f"travel_itinerary_{uuid.uuid4().hex[:8]}.{output_format}"
        
        # Get the conversation directory
        conversation_id = data.get("conversation_id")
        if conversation_id:
            output_dir = self._get_conversation_dir(conversation_id)
        else:
            output_dir = os.path.join(os.getcwd(), "output")
            
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        
        # Generate the document based on format
        if output_format == "html":
            await self._generate_html_itinerary(data, output_path)
        elif output_format == "markdown":
            await self._generate_markdown_itinerary(data, output_path)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
            
        return output_path
    
    def _get_conversation_dir(self, conversation_id: str) -> str:
        """Get the directory for a conversation."""
        base_dir = os.path.join(os.getcwd(), "data", "conversations")
        conversation_dir = os.path.join(base_dir, conversation_id)
        os.makedirs(conversation_dir, exist_ok=True)
        return conversation_dir
    
    async def _generate_html_itinerary(self, data: Dict[str, Any], output_path: str) -> None:
        """Generate an HTML travel itinerary document."""
        try:
            # Basic HTML template
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{data.get('title', 'Travel Itinerary')}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    h1, h2, h3 {{
                        color: #0d47a1;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        padding-bottom: 20px;
                        border-bottom: 1px solid #ddd;
                    }}
                    .day {{
                        margin-bottom: 30px;
                        padding: 20px;
                        background-color: #f9f9f9;
                        border-radius: 5px;
                    }}
                    .activity {{
                        margin-bottom: 15px;
                        padding-left: 20px;
                        border-left: 3px solid #1976d2;
                    }}
                    .activity-title {{
                        font-weight: bold;
                        color: #1976d2;
                    }}
                    .activity-time {{
                        color: #666;
                        font-style: italic;
                    }}
                    .activity-location {{
                        color: #666;
                        font-size: 0.9em;
                    }}
                    .proposal-locations {{
                        display: flex;
                        flex-wrap: wrap;
                        gap: 20px;
                        margin-top: 30px;
                    }}
                    .proposal-location {{
                        flex: 1;
                        min-width: 300px;
                        padding: 15px;
                        background-color: #f0f7ff;
                        border-radius: 5px;
                        border: 1px solid #d0e5ff;
                    }}
                    .additional-info {{
                        margin-top: 30px;
                        padding: 20px;
                        background-color: #f5f5f5;
                        border-radius: 5px;
                    }}
                    .footer {{
                        margin-top: 50px;
                        text-align: center;
                        font-size: 0.8em;
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{data.get('title', 'Travel Itinerary')}</h1>
                    <p><strong>Destination:</strong> {data.get('destination', 'Unknown')}</p>
                    <p><strong>Dates:</strong> {data.get('start_date', 'Unknown')} to {data.get('end_date', 'Unknown')}</p>
                </div>
                
                <h2>Overview</h2>
                <p>{data.get('overview', 'No overview provided.')}</p>
                
                <h2>Daily Itinerary</h2>
            """
            
            # Add days
            for day in data.get('days', []):
                html += f"""
                <div class="day">
                    <h3>Day {day.get('day_number', '?')} - {day.get('date', 'Unknown')}: {day.get('title', 'Unknown')}</h3>
                    {f"<p>{day.get('description', '')}</p>" if day.get('description') else ''}
                """
                
                # Add activities
                for activity in day.get('activities', []):
                    html += f"""
                    <div class="activity">
                        <div class="activity-title">
                            {f"<span class='activity-time'>{activity.get('time', '')}: </span>" if activity.get('time') else ''}
                            {activity.get('title', 'Unknown activity')}
                        </div>
                        {f"<p>{activity.get('description', '')}</p>" if activity.get('description') else ''}
                        {f"<div class='activity-location'>Location: {activity.get('location', '')}</div>" if activity.get('location') else ''}
                    </div>
                    """
                
                html += "</div>"
            
            # Add proposal locations
            if data.get('proposal_locations'):
                html += """
                <h2>Romantic Proposal Locations</h2>
                <div class="proposal-locations">
                """
                
                for location in data.get('proposal_locations', []):
                    html += f"""
                    <div class="proposal-location">
                        <h3>{location.get('name', 'Unknown location')}</h3>
                        <p>{location.get('description', 'No description provided.')}</p>
                        {f"<p><strong>Best time:</strong> {location.get('best_time', '')}</p>" if location.get('best_time') else ''}
                        {f"<img src='{location.get('image_url', '')}' alt='{location.get('name', 'Proposal location')}' style='max-width: 100%; border-radius: 5px;'>" if location.get('image_url') else ''}
                    </div>
                    """
                
                html += "</div>"
            
            # Add additional info
            if data.get('additional_info'):
                html += """
                <div class="additional-info">
                    <h2>Additional Information</h2>
                """
                
                additional_info = data.get('additional_info', {})
                
                # Essential phrases
                if additional_info.get('essential_phrases'):
                    html += "<h3>Essential Phrases</h3><ul>"
                    for phrase, translation in additional_info.get('essential_phrases', {}).items():
                        html += f"<li><strong>{phrase}:</strong> {translation}</li>"
                    html += "</ul>"
                
                # Emergency contacts
                if additional_info.get('emergency_contacts'):
                    html += "<h3>Emergency Contacts</h3><ul>"
                    for service, contact in additional_info.get('emergency_contacts', {}).items():
                        html += f"<li><strong>{service}:</strong> {contact}</li>"
                    html += "</ul>"
                
                # Transportation info
                if additional_info.get('transportation_info'):
                    html += f"<h3>Transportation Information</h3><p>{additional_info.get('transportation_info', '')}</p>"
                
                # Weather info
                if additional_info.get('weather_info'):
                    html += f"<h3>Weather Information</h3><p>{additional_info.get('weather_info', '')}</p>"
                
                html += "</div>"
            
            # Add footer
            html += f"""
                <div class="footer">
                    <p>Generated by Nexagent on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """
            
            # Write the HTML to the output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
            logger.info(f"Generated HTML travel itinerary at {output_path}")
        except Exception as e:
            logger.error(f"Error generating HTML travel itinerary: {str(e)}")
            raise
    
    async def _generate_markdown_itinerary(self, data: Dict[str, Any], output_path: str) -> None:
        """Generate a Markdown travel itinerary document."""
        try:
            # Basic Markdown template
            markdown = f"""# {data.get('title', 'Travel Itinerary')}

**Destination:** {data.get('destination', 'Unknown')}  
**Dates:** {data.get('start_date', 'Unknown')} to {data.get('end_date', 'Unknown')}

## Overview

{data.get('overview', 'No overview provided.')}

## Daily Itinerary

"""
            
            # Add days
            for day in data.get('days', []):
                markdown += f"""### Day {day.get('day_number', '?')} - {day.get('date', 'Unknown')}: {day.get('title', 'Unknown')}

{day.get('description', '')}

"""
                
                # Add activities
                for activity in day.get('activities', []):
                    markdown += f"""- **{activity.get('time', '') + ': ' if activity.get('time') else ''}{activity.get('title', 'Unknown activity')}**  
  {activity.get('description', '')}  
  {f"Location: {activity.get('location', '')}" if activity.get('location') else ''}

"""
            
            # Add proposal locations
            if data.get('proposal_locations'):
                markdown += """## Romantic Proposal Locations

"""
                
                for location in data.get('proposal_locations', []):
                    markdown += f"""### {location.get('name', 'Unknown location')}

{location.get('description', 'No description provided.')}

{f"**Best time:** {location.get('best_time', '')}" if location.get('best_time') else ''}

"""
            
            # Add additional info
            if data.get('additional_info'):
                markdown += """## Additional Information

"""
                
                additional_info = data.get('additional_info', {})
                
                # Essential phrases
                if additional_info.get('essential_phrases'):
                    markdown += "### Essential Phrases\n\n"
                    for phrase, translation in additional_info.get('essential_phrases', {}).items():
                        markdown += f"- **{phrase}:** {translation}\n"
                    markdown += "\n"
                
                # Emergency contacts
                if additional_info.get('emergency_contacts'):
                    markdown += "### Emergency Contacts\n\n"
                    for service, contact in additional_info.get('emergency_contacts', {}).items():
                        markdown += f"- **{service}:** {contact}\n"
                    markdown += "\n"
                
                # Transportation info
                if additional_info.get('transportation_info'):
                    markdown += f"### Transportation Information\n\n{additional_info.get('transportation_info', '')}\n\n"
                
                # Weather info
                if additional_info.get('weather_info'):
                    markdown += f"### Weather Information\n\n{additional_info.get('weather_info', '')}\n\n"
            
            # Add footer
            markdown += f"""---

*Generated by Nexagent on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            # Write the Markdown to the output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
                
            logger.info(f"Generated Markdown travel itinerary at {output_path}")
        except Exception as e:
            logger.error(f"Error generating Markdown travel itinerary: {str(e)}")
            raise
