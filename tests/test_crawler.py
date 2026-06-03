"""
Unit tests for crawler same-domain constraints and exclusions.
"""

from unittest.mock import MagicMock
from src.crawler import Crawler

def test_crawler_should_crawl():
    crawler = Crawler("https://www.example.edu", max_depth=2)
    
    # Same domain checks
    assert crawler.should_crawl("https://www.example.edu/admissions") is True
    assert crawler.should_crawl("https://example.edu/tuition") is True
    assert crawler.should_crawl("https://other-school.edu/admissions") is False
    
    # Exclude files
    assert crawler.should_crawl("https://www.example.edu/document.pdf") is False
    assert crawler.should_crawl("https://www.example.edu/image.png") is False
    
    # Exclude login patterns
    assert crawler.should_crawl("https://www.example.edu/portal/login") is False
    assert crawler.should_crawl("https://www.example.edu/wp-login.php") is False

def test_crawler_get_links():
    crawler = Crawler("https://www.example.edu", max_depth=1)
    sample_html = """
    <html>
        <body>
            <a href="/admissions">Admissions</a>
            <a href="https://www.example.edu/tuition#fees">Tuition</a>
            <a href="https://other.com">External</a>
        </body>
    </html>
    """
    links = crawler.get_links(sample_html, "https://www.example.edu")
    assert "https://www.example.edu/admissions" in links
    # Should strip hash fragments
    assert "https://www.example.edu/tuition" in links
