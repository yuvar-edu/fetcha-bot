import json
import logging
import asyncio
from typing import Dict, Any, Optional
from openai import OpenAI

class AnalysisAPI:
    def __init__(self, api_key: str, base_url: str = "https://api.x.ai/v1"):
        """
        Initialize the Analysis API client.
        
        Args:
            api_key: API key for the AI service
            base_url: Base URL for the AI service
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.logger = logging.getLogger(__name__)
    
    async def analyze_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze text using the AI service.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with analysis results, or None if analysis failed
        """
        try:
            # Add a 1-second delay before making the API call
            await asyncio.sleep(1)
            
            response = self.client.chat.completions.create(
                model="grok-2-latest",
                messages=[
                    {"role": "system", "content": (
                        "You are a financial market analysis assistant. "
                        "Analyze the user's input and return a JSON object with the following keys: "
                        "'sentiment' (positive, negative, or neutral), "
                        "'score' (integer from 0 to 10), "
                        "'impact' (high, medium, or low), "
                        "'direction' (bullish, bearish or neautral), "
                        "'assets' (a list of asset names), "
                        "'relevant' (boolean indicating if the analysis is relevant). "
                        "Only return a valid JSON object. Do not include any explanations or extra text."
                    )},
                    {"role": "user", "content": text}
                ]
            )

            content = response.choices[0].message.content
            self.logger.debug(f"AI analysis raw output:\n{content}")
            
            # Check if content is empty or whitespace
            if not content or content.isspace():
                self.logger.warning("AI returned empty or whitespace content")
                return None
                
            # Try to clean the content before parsing
            # Sometimes APIs return text with JSON embedded
            content = content.strip()
            if content.startswith("```json"):
                # Extract JSON from code blocks if present
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif content.startswith("```"):
                # Handle generic code blocks
                content = content.split("```", 1)[1].split("```", 1)[0].strip()
                
            # Try to find JSON in the response if it's mixed with text
            if not (content.startswith('{') and content.endswith('}')):
                import re
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)

            # Safely parse the JSON response
            analysis = json.loads(content)
            
            # Add success logging
            self.logger.info(f"AI analysis successful. Result: {json.dumps(analysis, indent=2)}")

            # Fill in missing fields with defaults
            return {
                'sentiment': analysis.get('sentiment', 'neutral'),
                'score': int(analysis.get('score', 5)),
                'impact': analysis.get('impact', 'medium'),
                'direction': analysis.get('direction', 'neutral'),
                'assets': analysis.get('assets', []) or [],
                'relevant': analysis.get('relevant', False)
            }

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}. Raw content: {content[:100]}...")
            return None
        except Exception as e:
            self.logger.error(f"AI analysis error: {str(e)}", exc_info=True)
            return None