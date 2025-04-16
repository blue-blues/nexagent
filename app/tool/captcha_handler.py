import asyncio
import base64
import logging
import re
import time
from typing import Optional, Dict, Any, Tuple, List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CaptchaSolution(BaseModel):
    """Model for a solved captcha"""
    solution: str
    timestamp: float = Field(default_factory=time.time)
    captcha_type: str
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaptchaHandler:
    """Handles detection and solving of various types of CAPTCHAs"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.service_url: Optional[str] = None
        self.service_type: str = "none"  # none, 2captcha, anticaptcha, custom
        self.timeout: int = 120  # seconds
        self.max_retries: int = 3
        self.last_solutions: List[CaptchaSolution] = []
        self._lock = asyncio.Lock()
    
    def configure(self, service_type: str, api_key: Optional[str] = None, service_url: Optional[str] = None):
        """Configure the captcha handler with service details"""
        self.service_type = service_type
        self.api_key = api_key
        self.service_url = service_url
        logger.info(f"Captcha handler configured to use {service_type} service")
    
    async def detect_captcha(self, browser_context) -> Tuple[bool, str, Dict[str, Any]]:
        """Detect if a captcha is present on the current page"""
        try:
            # Check for common captcha indicators
            captcha_indicators = await browser_context.execute_javascript("""
            (function() {
                const indicators = {
                    recaptcha: false,
                    hcaptcha: false,
                    cloudflare: false,
                    textCaptcha: false,
                    imageCaptcha: false,
                    details: {}
                };
                
                // Check for reCAPTCHA
                if (document.querySelector('.g-recaptcha') || 
                    document.querySelector('iframe[src*="recaptcha"]') ||
                    document.querySelector('iframe[src*="google.com/recaptcha"]')) {
                    indicators.recaptcha = true;
                    indicators.details.recaptcha = {
                        visible: document.querySelector('.g-recaptcha') !== null,
                        sitekey: document.querySelector('.g-recaptcha')?.getAttribute('data-sitekey') || ''
                    };
                }
                
                // Check for hCaptcha
                if (document.querySelector('.h-captcha') || 
                    document.querySelector('iframe[src*="hcaptcha"]')) {
                    indicators.hcaptcha = true;
                    indicators.details.hcaptcha = {
                        visible: document.querySelector('.h-captcha') !== null,
                        sitekey: document.querySelector('.h-captcha')?.getAttribute('data-sitekey') || ''
                    };
                }
                
                // Check for Cloudflare captcha
                if (document.querySelector('#cf-please-wait') || 
                    document.querySelector('.cf-browser-verification') ||
                    document.querySelector('#cf-spinner')) {
                    indicators.cloudflare = true;
                }
                
                // Check for text-based captcha (simple pattern match)
                const bodyText = document.body.innerText.toLowerCase();
                if (bodyText.includes('captcha') && 
                    (document.querySelector('input[type="text"]') || document.querySelector('input:not([type])')) &&
                    (bodyText.includes('enter the code') || bodyText.includes('enter the characters') || 
                     bodyText.includes('security check') || bodyText.includes('prove you\'re human'))) {
                    indicators.textCaptcha = true;
                    
                    // Try to find the captcha image
                    const nearbyImg = Array.from(document.querySelectorAll('img'))
                        .find(img => {
                            const rect = img.getBoundingClientRect();
                            return rect.width > 50 && rect.height > 20 && rect.width < 300 && rect.height < 100;
                        });
                    
                    if (nearbyImg) {
                        indicators.imageCaptcha = true;
                        indicators.details.imageCaptcha = {
                            src: nearbyImg.src,
                            alt: nearbyImg.alt || '',
                            dimensions: `${nearbyImg.width}x${nearbyImg.height}`
                        };
                    }
                }
                
                return indicators;
            })();
            """)
            
            captcha_detected = any([
                captcha_indicators.get('recaptcha', False),
                captcha_indicators.get('hcaptcha', False),
                captcha_indicators.get('cloudflare', False),
                captcha_indicators.get('textCaptcha', False),
                captcha_indicators.get('imageCaptcha', False)
            ])
            
            captcha_type = 'none'
            if captcha_indicators.get('recaptcha', False):
                captcha_type = 'recaptcha'
            elif captcha_indicators.get('hcaptcha', False):
                captcha_type = 'hcaptcha'
            elif captcha_indicators.get('cloudflare', False):
                captcha_type = 'cloudflare'
            elif captcha_indicators.get('imageCaptcha', False):
                captcha_type = 'image'
            elif captcha_indicators.get('textCaptcha', False):
                captcha_type = 'text'
            
            details = captcha_indicators.get('details', {})
            
            if captcha_detected:
                logger.info(f"Detected {captcha_type} captcha on page")
            
            return captcha_detected, captcha_type, details
        
        except Exception as e:
            logger.error(f"Error detecting captcha: {e}")
            return False, 'error', {'error': str(e)}
    
    async def solve_captcha(self, browser_context, captcha_type: str, details: Dict[str, Any]) -> Optional[CaptchaSolution]:
        """Solve the detected captcha"""
        if self.service_type == "none":
            logger.warning("No captcha solving service configured")
            return None
        
        try:
            if captcha_type == 'recaptcha':
                return await self._solve_recaptcha(browser_context, details)
            elif captcha_type == 'hcaptcha':
                return await self._solve_hcaptcha(browser_context, details)
            elif captcha_type == 'cloudflare':
                return await self._handle_cloudflare(browser_context)
            elif captcha_type == 'image':
                return await self._solve_image_captcha(browser_context, details)
            elif captcha_type == 'text':
                return await self._solve_text_captcha(browser_context, details)
            else:
                logger.warning(f"Unsupported captcha type: {captcha_type}")
                return None
        except Exception as e:
            logger.error(f"Error solving captcha: {e}")
            return None
    
    async def _solve_recaptcha(self, browser_context, details: Dict[str, Any]) -> Optional[CaptchaSolution]:
        """Solve a reCAPTCHA challenge"""
        if self.service_type == "2captcha" and self.api_key:
            try:
                # Get the site key and page URL
                site_key = details.get('recaptcha', {}).get('sitekey')
                if not site_key:
                    site_key = await browser_context.execute_javascript("""
                    document.querySelector('.g-recaptcha')?.getAttribute('data-sitekey') || ''
                    """)
                
                if not site_key:
                    logger.error("Could not find reCAPTCHA site key")
                    return None
                
                page_url = await browser_context.execute_javascript("window.location.href")
                
                # This is a simplified example. In a real implementation, you would:
                # 1. Send the site key and page URL to 2captcha API
                # 2. Poll for the solution
                # 3. Apply the solution to the page
                
                logger.info(f"Solving reCAPTCHA with site key {site_key} on {page_url}")
                
                # Simulate solving process (in real implementation, call 2captcha API)
                await asyncio.sleep(2)  # Simulating API call delay
                
                # In a real implementation, you would get the g-recaptcha-response from 2captcha
                # and inject it into the page
                solution = "simulated_recaptcha_solution_token"
                
                # Apply the solution to the page
                success = await browser_context.execute_javascript(f"""
                (function() {{
                    // In a real implementation, you would set the g-recaptcha-response
                    // and submit the form
                    console.log('Applying reCAPTCHA solution: {solution}');
                    return true; // Simulating success
                }})();
                """)
                
                if success:
                    return CaptchaSolution(
                        solution=solution,
                        captcha_type="recaptcha",
                        success=True,
                        metadata={"site_key": site_key, "page_url": page_url}
                    )
                
            except Exception as e:
                logger.error(f"Error solving reCAPTCHA: {e}")
        
        return None
    
    async def _solve_hcaptcha(self, browser_context, details: Dict[str, Any]) -> Optional[CaptchaSolution]:
        """Solve an hCaptcha challenge"""
        # Similar implementation to _solve_recaptcha but for hCaptcha
        # This is a placeholder for the actual implementation
        logger.info("hCaptcha solving not fully implemented yet")
        return None
    
    async def _handle_cloudflare(self, browser_context) -> Optional[CaptchaSolution]:
        """Handle Cloudflare protection"""
        try:
            # For Cloudflare, often waiting is the best strategy
            logger.info("Waiting for Cloudflare challenge to complete")
            
            # Wait for Cloudflare spinner to disappear
            for _ in range(30):  # Wait up to 30 seconds
                cloudflare_elements = await browser_context.execute_javascript("""
                (function() {
                    return {
                        spinner: document.querySelector('#cf-spinner') !== null,
                        verification: document.querySelector('.cf-browser-verification') !== null,
                        wait: document.querySelector('#cf-please-wait') !== null
                    };
                })();
                """)
                
                if not any(cloudflare_elements.values()):
                    logger.info("Cloudflare challenge appears to be completed")
                    return CaptchaSolution(
                        solution="waited_for_cloudflare",
                        captcha_type="cloudflare",
                        success=True
                    )
                
                await asyncio.sleep(1)
            
            logger.warning("Cloudflare challenge did not complete in time")
            return None
            
        except Exception as e:
            logger.error(f"Error handling Cloudflare: {e}")
            return None
    
    async def _solve_image_captcha(self, browser_context, details: Dict[str, Any]) -> Optional[CaptchaSolution]:
        """Solve an image-based captcha"""
        try:
            # Get the captcha image
            image_src = details.get('imageCaptcha', {}).get('src')
            if not image_src:
                logger.error("Could not find captcha image source")
                return None
            
            # Get the image as base64
            image_base64 = await browser_context.execute_javascript(f"""
            (async function() {{
                try {{
                    const img = document.querySelector('img[src="{image_src}"]');
                    if (!img) return null;
                    
                    // Create a canvas and draw the image on it
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    
                    // Get the image as base64
                    return canvas.toDataURL('image/png').split(',')[1];
                }} catch (e) {{
                    console.error('Error getting captcha image:', e);
                    return null;
                }}
            }})();
            """)
            
            if not image_base64:
                logger.error("Could not get captcha image as base64")
                return None
            
            # In a real implementation, you would send the image to a captcha solving service
            # and get the solution
            
            # Simulate solving process
            logger.info("Solving image captcha")
            await asyncio.sleep(2)  # Simulating API call delay
            
            # Simulated solution
            solution = "ABCD123"  # This would come from the captcha solving service
            
            # Find the input field and submit button
            input_and_button = await browser_context.execute_javascript("""
            (function() {
                // Find an input field near the captcha image
                const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'));
                const captchaInput = inputs.find(input => {
                    const rect = input.getBoundingClientRect();
                    return rect.width > 30 && rect.height > 15;
                });
                
                // Find a submit button
                const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
                const submitButton = buttons.find(button => {
                    const text = button.innerText || button.value || '';
                    return text.toLowerCase().includes('submit') || 
                           text.toLowerCase().includes('verify') || 
                           text.toLowerCase().includes('continue');
                });
                
                return {
                    hasInput: captchaInput !== undefined,
                    hasButton: submitButton !== undefined
                };
            })();
            """)
            
            if input_and_button.get('hasInput'):
                # Enter the solution
                await browser_context.execute_javascript(f"""
                (function() {{
                    const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'));
                    const captchaInput = inputs.find(input => {{
                        const rect = input.getBoundingClientRect();
                        return rect.width > 30 && rect.height > 15;
                    }});
                    
                    if (captchaInput) {{
                        captchaInput.value = '{solution}';
                        return true;
                    }}
                    return false;
                }})();
                """)
                
                # Submit the form if there's a button
                if input_and_button.get('hasButton'):
                    await browser_context.execute_javascript("""
                    (function() {
                        const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
                        const submitButton = buttons.find(button => {
                            const text = button.innerText || button.value || '';
                            return text.toLowerCase().includes('submit') || 
                                   text.toLowerCase().includes('verify') || 
                                   text.toLowerCase().includes('continue');
                        });
                        
                        if (submitButton) {
                            submitButton.click();
                            return true;
                        }
                        return false;
                    })();
                    """)
                
                return CaptchaSolution(
                    solution=solution,
                    captcha_type="image",
                    success=True,
                    metadata={"image_dimensions": details.get('imageCaptcha', {}).get('dimensions')}
                )
            
            logger.warning("Could not find input field for captcha solution")
            return None
            
        except Exception as e:
            logger.error(f"Error solving image captcha: {e}")
            return None
    
    async def _solve_text_captcha(self, browser_context, details: Dict[str, Any]) -> Optional[CaptchaSolution]:
        """Solve a text-based captcha"""
        # Similar to image captcha but for text-based challenges
        # This is a placeholder for the actual implementation
        logger.info("Text captcha solving not fully implemented yet")
        return None
    
    async def apply_solution(self, browser_context, solution: CaptchaSolution) -> bool:
        """Apply a captcha solution to the page"""
        try:
            if solution.captcha_type == "recaptcha":
                # Apply reCAPTCHA solution
                success = await browser_context.execute_javascript(f"""
                (function() {{
                    try {{
                        // Set the g-recaptcha-response
                        document.querySelector('[name="g-recaptcha-response"]').innerHTML = '{solution.solution}';
                        
                        // Find and submit the form
                        const form = document.querySelector('.g-recaptcha').closest('form');
                        if (form) {{
                            form.submit();
                            return true;
                        }}
                        return false;
                    }} catch (e) {{
                        console.error('Error applying reCAPTCHA solution:', e);
                        return false;
                    }}
                }})();
                """)
                return success
            
            elif solution.captcha_type == "hcaptcha":
                # Apply hCaptcha solution
                # Similar to reCAPTCHA
                return False  # Not implemented yet
            
            elif solution.captcha_type == "cloudflare":
                # For Cloudflare, we've already waited for it to complete
                return True
            
            elif solution.captcha_type in ["image", "text"]:
                # For image and text captchas, we've already applied the solution
                # during the solving process
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error applying captcha solution: {e}")
            return False
    
    def store_solution(self, solution: CaptchaSolution):
        """Store a successful captcha solution for future reference"""
        self.last_solutions.append(solution)
        # Keep only the last 10 solutions
        if len(self.last_solutions) > 10:
            self.last_solutions.pop(0)


# Singleton instance
captcha_handler = CaptchaHandler()