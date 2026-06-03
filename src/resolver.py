"""
Module for resolving university names to official website domains.
Uses DuckDuckGo search API first, falling back to Gemini LLM resolution.
"""

import os
import re
from urllib.parse import urlparse
from typing import Optional
from duckduckgo_search import DDGS
from src.utils import setup_logger
from src.extractor import get_gemini_client, call_gemini_with_retry

logger = setup_logger(__name__)

def clean_domain(url: str) -> Optional[str]:
    """Helper to extract domain from a full URL."""
    try:
        parsed = urlparse(url)
        # Handle cases where protocol might be missing
        if not parsed.scheme:
            parsed = urlparse("https://" + url)
        
        # Ensure we have netloc
        if parsed.netloc:
            # We want to return the base official website URL format: e.g. https://www.bucknell.edu
            scheme = parsed.scheme if parsed.scheme in ["http", "https"] else "https"
            netloc = parsed.netloc
            # Keep www if present, but clean standard trailing paths
            return f"{scheme}://{netloc}"
    except Exception as e:
        logger.warning(f"Error cleaning URL {url}: {e}")
    return None

def resolve_name_via_search(name: str) -> Optional[str]:
    """Resolves university name using DuckDuckGo Search."""
    logger.info(f"Attempting to resolve name via DuckDuckGo Search: '{name}'")
    try:
        with DDGS() as ddgs:
            # Search query optimized for official website
            query = f"{name} official university website homepage"
            results = ddgs.text(query, max_results=8)
            
            domains = []
            for r in results:
                href = r.get("href", "")
                domain = clean_domain(href)
                if domain:
                    domains.append(domain)
            
            # Prioritize domains:
            # 1. Official education domains (.edu, .ac.uk, .edu.au, etc.)
            # 2. Domains containing a key word from the university name
            
            ignored_keywords = [
                "wikipedia.org", "facebook.com", "linkedin.com", "twitter.com", 
                "instagram.com", "youtube.com", "usnews.com", "forbes.com",
                "microsoft.com", "google.com", "github.com", "reddit.com", "apple.com"
            ]
            
            # Clean candidate list
            filtered_domains = []
            for d in domains:
                d_lower = d.lower()
                if any(kw in d_lower for kw in ignored_keywords):
                    continue
                filtered_domains.append(d)
                
            name_words = [w.lower() for w in re.findall(r'\w+', name) if len(w) > 3]
            
            # Phase 1: Look for education domains (.edu) that also overlap with the name
            for d in filtered_domains:
                d_lower = d.lower()
                if ".edu" in d_lower or ".ac." in d_lower:
                    if any(word in d_lower for word in name_words):
                        logger.info(f"Resolved '{name}' to prioritized edu domain: {d}")
                        return d
                        
            # Phase 2: Look for any education domains (.edu)
            for d in filtered_domains:
                d_lower = d.lower()
                if ".edu" in d_lower or ".ac." in d_lower:
                    logger.info(f"Resolved '{name}' to edu domain: {d}")
                    return d
                    
            # Phase 3: Look for any domain with keyword overlap
            for d in filtered_domains:
                d_lower = d.lower()
                if any(word in d_lower for word in name_words):
                    logger.info(f"Resolved '{name}' to overlapping name domain: {d}")
                    return d
                    
            # Phase 4: Fallback to the first filtered domain
            if filtered_domains:
                fallback_domain = filtered_domains[0]
                logger.info(f"Resolved '{name}' to fallback domain: {fallback_domain}")
                return fallback_domain
                
    except Exception as e:
        logger.error(f"Search API domain resolution failed: {e}")
    return None

def resolve_name_via_llm(name: str) -> Optional[str]:
    """LLM Fallback to resolve university name to official website domain."""
    logger.info(f"Attempting fallback to Gemini LLM for domain resolution: '{name}'")
    try:
        prompt = (
            f"You are a university domain resolution assistant. "
            f"Given the university name: '{name}', identify their official homepage URL. "
            f"Respond with ONLY the valid homepage URL (e.g., https://www.bucknell.edu). "
            f"Do not include any explanation or extra text. If unknown, respond with nothing."
        )
        
        client, model_name = get_gemini_client()
        try:
            response_text = call_gemini_with_retry(client, model_name, prompt)
        except Exception as primary_err:
            fallback_model = "gemini-2.5-flash"
            logger.warning(f"Primary model {model_name} failed during domain resolution. Attempting fallback model '{fallback_model}'...")
            response_text = call_gemini_with_retry(client, fallback_model, prompt)
        
        # Extract URL from response
        urls = re.findall(r'https?://[^\s\)]+', response_text)
        if urls:
            cleaned = clean_domain(urls[0])
            if cleaned:
                logger.info(f"Gemini resolved '{name}' to: {cleaned}")
                return cleaned
    except Exception as e:
        logger.error(f"Gemini domain resolution failed: {e}")
    return None

def resolve_university_input(user_input: str) -> str:
    """
    Validates input. If it is already a domain, returns it.
    If it is a name, attempts search-based and then LLM-based resolution.
    """
    user_input = user_input.strip()
    
    # Simple regex to check if it's already a URL or domain-like
    if re.match(r'^(https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$', user_input):
        # Clean/normalize the provided domain
        cleaned = clean_domain(user_input)
        if cleaned:
            logger.info(f"Input is already a domain: {cleaned}")
            return cleaned
        return user_input
    
    # Resolve university name
    resolved = resolve_name_via_search(user_input)
    if resolved:
        return resolved
        
    resolved_llm = resolve_name_via_llm(user_input)
    if resolved_llm:
        return resolved_llm
        
    raise ValueError(f"Could not resolve university name '{user_input}' to an official domain.")
