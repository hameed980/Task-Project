"""
Module for cleaning HTML content.
Removes navigational, boilerplate, and UI noise to minimize tokens and improve LLM parsing.
"""

import re
from bs4 import BeautifulSoup
from src.utils import setup_logger

logger = setup_logger(__name__)

# List of HTML elements that typically contain noise/boilerplate
NOISE_TAGS = [
    "script", "style", "nav", "header", "footer", "form", "iframe",
    "noscript", "svg", "button", "aside", "menu"
]

def clean_html(html_content: str) -> str:
    """
    Parses and cleans HTML by:
    1. Stripping navigation, styles, scripts, buttons, and footers.
    2. Extracting structured page text.
    3. Collapsing whitespace and duplicate empty lines.
    """
    if not html_content:
        return ""
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Strip structural tags and media noise
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()
        
    # Remove common class name/ID boilerplate elements (e.g., skip-link, social-media, menu)
    for class_or_id_match in soup.find_all(
        class_=re.compile(r"nav|menu|social|footer|header|sidebar|share|popup|cookie|modal", re.I)
    ):
        class_or_id_match.decompose()
        
    for id_match in soup.find_all(
        id=re.compile(r"nav|menu|social|footer|header|sidebar|share|popup|cookie|modal", re.I)
    ):
        id_match.decompose()
        
    # 2. Extract text structures (preserving basic block separators)
    # Using spaces or newlines for visual structure elements
    for block in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"]):
        block.append(" \n ")
        
    text = soup.get_text()
    
    # 3. Collapse whitespace and duplicate lines
    cleaned_lines = []
    seen_lines = set()
    
    for line in text.split("\n"):
        cleaned_line = re.sub(r"\s+", " ", line).strip()
        
        # Filter out empty or extremely short junk lines
        if not cleaned_line or len(cleaned_line) < 3:
            continue
            
        # Optional: Deduplicate exact duplicate lines within the page to save tokens
        # (e.g., repeating buttons, quick links, repeated side panel texts)
        if cleaned_line in seen_lines:
            continue
            
        seen_lines.add(cleaned_line)
        cleaned_lines.append(cleaned_line)
        
    return "\n".join(cleaned_lines)
