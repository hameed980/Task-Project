"""
Module for interacting with Gemini API for data extraction.
Handles client configuration, retry logic with tenacity, and prompt optimization.
"""

import os
import json
import re
from typing import Tuple, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv
from src.utils import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# Configurable defaults
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

class GeminiAPIError(Exception):
    """Custom exception wrapper for Gemini API failures to trigger retries."""
    pass

def get_gemini_client() -> Tuple[Any, str]:
    """
    Initializes and returns the Gemini client and model name.
    Supports both modern google-genai and legacy google-generativeai packages as fallbacks.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY environment variable is not set. API calls may fail.")
        
    model_name = DEFAULT_MODEL
    
    #  importing Google GenAI SDK
    try:
        from google import genai
        logger.info(f"Using google-genai SDK with model {model_name}")
        client = genai.Client(api_key=api_key)
        return client, model_name
    except ImportError:
        logger.info("google-genai SDK not found, attempting google-generativeai fallback")
        
    #  standard google-generativeai fallback
    try:
        import google.generativeai as genai
        logger.info(f"Using google-generativeai SDK with model {model_name}")
        genai.configure(api_key=api_key)
        return genai, model_name
    except ImportError:
        raise ImportError(
            "Neither 'google-genai' nor 'google-generativeai' packages are installed. "
            "Please install requirements.txt first."
        )

# Retry decorator with exponential backoff for tenacity
# Retries up to 4 times for GeminiAPIError/RateLimit/Server errors
@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(GeminiAPIError),
    reraise=True
)
def call_gemini_with_retry(client: Any, model_name: str, prompt: str) -> str:
    """Executes a Gemini API request with tenacity retries and error handling."""
    try:
        # Check if the client is google-genai (has client.models property)
        if hasattr(client, "models"):
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            text = response.text
        else:
            # Fallback client (google-generativeai)
            model = client.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text
            
        if not text:
            raise GeminiAPIError("Empty response returned from Gemini API.")
        return text
    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}. Retrying...")
        raise GeminiAPIError(f"API execution error: {str(e)}") from e

def extract_university_data(combined_text: str, source_urls: list[str]) -> dict:
    """
    Constructs the prompt, calls Gemini, and returns extracted JSON data.
    Ensures validation rules (no hallucinating, JSON output format).
    """
    logger.info("Preparing data extraction prompt for Gemini LLM")
    
    # Prompt is designed to guide output into structured JSON matching Pydantic structure
    # while asking LLM to produce confidence scores and source URL mappings.
    prompt = f"""
You are an expert data extraction assistant. Extract structured university data from the provided scraped text.

CRITICAL CONSTRAINTS:
1. ONLY extract information supported by the provided text.
2. NEVER hallucinate or guess any missing values.
3. If a piece of information is missing, return null for it.
4. Output must be a SINGLE valid JSON object matching the schema. No markdown formatting around JSON (do not include ```json tags).

Here is the JSON schema you must fill:
{{
  "overview": {{
    "university_name": "Official university name",
    "location": {{
      "city": "City name",
      "state": "State name or abbreviation",
      "country": "Country name",
      "postal_code": "Postal/ZIP code"
    }},
    "contact": {{
      "phone": "Official phone number",
      "email": "Official contact email (valid email syntax)"
    }}
  }},
  "tuition_breakdown": [
    {{
      "fee_type": "Brief description (e.g. Undergraduate Tuition, Room & Board, Fees)",
      "cost": 12345, // numeric whole number in USD only
      "currency": "USD"
    }}
  ],
  "admission_deadlines": [
    {{
      "deadline_type": "Early Decision" OR "Regular Decision" OR "Transfer Admission",
      "deadline_date": "YYYY-MM-DD", // Parse dates strictly to YYYY-MM-DD
      "notes": "Any extra notes"
    }}
  ],
  "page_metadata": [
    {{
      "url": "Source URL where this data was extracted",
      "page_title": "Title of the page",
      "scraped_at": "YYYY-MM-DD HH:MM:SS",
      "status_code": "200"
    }}
  ],
  "confidence_scores": {{
    "university_name": 0.95, // Float between 0.0 and 1.0 representing extraction confidence
    "location": 0.90,
    "contact": 0.85,
    "tuition_breakdown": 0.90,
    "admission_deadlines": 0.90
  }},
  "source_attributions": {{
    "university_name": "URL matching source",
    "location": "URL matching source",
    "contact": "URL matching source",
    "tuition_breakdown": "URL matching source",
    "admission_deadlines": "URL matching source"
  }}
}}

List of valid page URLs that you can attribute as source URLs:
{json.dumps(source_urls, indent=2)}

---
SCRAPED TEXT:
{combined_text}
---

Output only the raw JSON object.
"""
    
    client, model_name = get_gemini_client()
    
    try:
        raw_response = call_gemini_with_retry(client, model_name, prompt)
    except GeminiAPIError as primary_err:
        fallback_model = "gemini-2.5-flash"
        logger.warning(f"Primary model {model_name} failed with service/rate issues. Attempting fallback to stability model '{fallback_model}'...")
        try:
            raw_response = call_gemini_with_retry(client, fallback_model, prompt)
        except Exception as fallback_err:
            logger.error(f"Fallback model '{fallback_model}' also failed: {fallback_err}")
            # Raise the original error if fallback also fails
            raise primary_err
    
    # Strip potential markdown fences if returned
    cleaned_json = raw_response.strip()
    if cleaned_json.startswith("```json"):
        cleaned_json = cleaned_json[7:]
    if cleaned_json.endswith("```"):
        cleaned_json = cleaned_json[:-3]
    cleaned_json = cleaned_json.strip()
    
    try:
        data = json.loads(cleaned_json)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from LLM: {e}")
        logger.debug(f"Raw Response: {raw_response}")
        # Return partial fallback structure
        return {}
