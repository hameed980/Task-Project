"""
Module for web crawling university domains.
Limits depth, maintains domain boundaries, and collects page content and metadata.
"""

import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Set, Optional
import requests
from bs4 import BeautifulSoup
from src.utils import setup_logger

logger = setup_logger(__name__)

# Typical pages that require login, auth, or contain irrelevant info to exclude
EXCLUDED_PATTERNS = [
    "/login", "/signin", "/signup", "/register", "/portal", "/auth",
    "shibboleth", "cas/login", "webauth", "canvas", "blackboard",
    "moodle", "library-login", "wp-login.php",
    # Irrelevant content patterns to reduce crawler noise
    "/news/", "/blog", "/directory", "/map", "/event", "/calendar", 
    "/athletics", "/alumni", "/donor", "/staff", "/employee", 
    "/privacy", "/terms", "/legal", "/commencement", "/magazine", 
    "/careers", "/feedback", "/sustainability"
]

class Crawler:
    """A same-domain crawler with maximum depth and auth protection."""
    
    def __init__(self, start_url: str, max_depth: int = 2):
        self.start_url = start_url
        self.max_depth = max_depth
        self.base_domain = urlparse(start_url).netloc
        
        # Track crawled URLs to prevent duplicate requests
        self.visited: Set[str] = set()
        
        # Store results as {url: {title, html, depth, status_code, scraped_at}}
        self.pages: Dict[str, dict] = {}
        
        # Configure requests session with timeout and standard browser headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def should_crawl(self, url: str) -> bool:
        """Determines if a URL should be crawled based on domain, type and pattern rules."""
        try:
            parsed = urlparse(url)
            
            # Restrict crawling to same domain only
            base_clean = self.base_domain.lower().replace("www.", "")
            netloc_clean = parsed.netloc.lower().replace("www.", "")
            if netloc_clean != base_clean and not netloc_clean.endswith(f".{base_clean}"):
                return False
                
            url_path = parsed.path.lower()
            
            # Exclude PDF, zip, docx, media files
            excluded_extensions = (".pdf", ".zip", ".docx", ".doc", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mp3")
            if url_path.endswith(excluded_extensions):
                return False
                
            # Exclude authentication/login pages
            if any(pattern in url_path for pattern in EXCLUDED_PATTERNS):
                return False
                
            return True
        except Exception as e:
            logger.warning(f"Error checking url eligibility {url}: {e}")
            return False

    def get_links(self, html: str, current_url: str) -> List[str]:
        """Extracts and resolves all anchor links from a page's HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            # Resolve relative URLs
            full_url = urljoin(current_url, href)
            # Remove url fragments (e.g. #section1)
            full_url = full_url.split('#')[0]
            links.append(full_url)
        return links

    def crawl_page(self, url: str, depth: int):
        """Recursively crawls a page up to the max depth."""
        if url in self.visited or depth > self.max_depth:
            return
            
        self.visited.add(url)
        logger.info(f"Crawling (Depth {depth}): {url}")
        
        try:
            # Prevent overloading target servers
            time.sleep(0.5)
            
            response = self.session.get(url, timeout=10)
            status_code = response.status_code
            
            if status_code != 200:
                logger.warning(f"Failed to fetch {url} (Status {status_code})")
                return
                
            # Content verification
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                logger.debug(f"Skipping non-HTML page {url} (Content-Type: {content_type})")
                return
                
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title else "Untitled Page"
            
            # Record scraped page metadata & HTML content
            self.pages[url] = {
                "url": url,
                "title": title,
                "html": html,
                "depth": depth,
                "status_code": str(status_code),
                "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # If we haven't reached max depth, gather and crawl links
            if depth < self.max_depth:
                links = self.get_links(html, url)
                for link in links:
                    if self.should_crawl(link):
                        self.crawl_page(link, depth + 1)
                        
        except requests.RequestException as e:
            logger.error(f"Network error crawling {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}")

    def run(self) -> Dict[str, dict]:
        """Starts crawling from the start URL."""
        logger.info(f"Starting same-domain crawl for: {self.start_url}")
        self.crawl_page(self.start_url, depth=0)
        logger.info(f"Crawl completed. Discovered {len(self.pages)} pages.")
        return self.pages
