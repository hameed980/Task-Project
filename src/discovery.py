"""
Module for scoring and ranking scraped pages to identify relevant sources.
Categorizes pages into Admissions and Tuition/Cost targets based on scoring heuristics.
"""

import re
from urllib.parse import urlparse
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
from src.utils import setup_logger

logger = setup_logger(__name__)

# Scoring keyword signal matrices
ADMISSION_SIGNALS = {
    "admission": 10,
    "admissions": 10,
    "apply": 8,
    "deadline": 6,
    "deadlines": 6,
    "undergraduate": 5,
    "freshman": 4,
    "transfer": 4,
    "application": 4,
    "enrollment": 3,
    "requirements": 3
}

TUITION_SIGNALS = {
    "tuition": 10,
    "cost": 8,
    "costs": 8,
    "fees": 8,
    "financial-aid": 10,
    "financialaid": 10,
    "scholarship": 6,
    "scholarships": 6,
    "affordability": 6,
    "calculator": 4,
    "expenses": 4,
    "billing": 3
}

def calculate_score(url: str, title: str, html: str, signals: Dict[str, int]) -> float:
    """
    Computes a composite relevance score for a page based on signal keyword matches.
    Analyzes the URL, Page Title, and primary Headings.
    """
    score = 0.0
    url_path = urlparse(url).path.lower()
    title_lower = title.lower()
    
    # Clean and parse text elements of headings
    soup = BeautifulSoup(html, "html.parser")
    headings = " ".join([h.get_text().lower() for h in soup.find_all(["h1", "h2", "h3"])])
    
    for kw, weight in signals.items():
        # Match URL segments (high importance)
        if re.search(rf"\b{kw}\b|[-_]{kw}[-_]|^{kw}", url_path):
            score += weight * 2.0
            
        # Match Page Title (high importance)
        if re.search(rf"\b{kw}\b", title_lower):
            score += weight * 1.5
            
        # Match Headings (moderate importance)
        if re.search(rf"\b{kw}\b", headings):
            score += weight * 0.5
            
    return score

def discover_relevant_pages(
    pages: Dict[str, dict], 
    top_n: int = 3
) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Ranks crawled pages and selects the top N matching:
    1. Admissions pages
    2. Tuition & Cost pages
    Also includes the Home Page (depth 0) to extract Overview & Contact metadata.
    """
    logger.info("Ranking crawled pages for Admissions and Tuition relevance")
    
    scored_admissions: List[Tuple[float, dict]] = []
    scored_tuition: List[Tuple[float, dict]] = []
    home_pages: List[dict] = []
    
    for url, page_data in pages.items():
        # Home page is depth 0. Keep it separately to ensure generic overview details are captured.
        if page_data.get("depth") == 0:
            home_pages.append(page_data)
            continue
            
        adm_score = calculate_score(url, page_data["title"], page_data["html"], ADMISSION_SIGNALS)
        tui_score = calculate_score(url, page_data["title"], page_data["html"], TUITION_SIGNALS)
        
        if adm_score > 0:
            scored_admissions.append((adm_score, page_data))
        if tui_score > 0:
            scored_tuition.append((tui_score, page_data))
            
    # Sort by score descending
    scored_admissions.sort(key=lambda x: x[0], reverse=True)
    scored_tuition.sort(key=lambda x: x[0], reverse=True)
    
    # Extract raw page dictionaries
    top_admissions = [item[1] for item in scored_admissions[:top_n]]
    top_tuition = [item[1] for item in scored_tuition[:top_n]]
    
    logger.info(
        f"Selected top {len(top_admissions)} Admissions pages and "
        f"top {len(top_tuition)} Tuition pages (plus {len(home_pages)} home pages)."
    )
    
    return top_admissions, top_tuition, home_pages
