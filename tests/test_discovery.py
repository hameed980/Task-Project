"""
Unit tests for the relevance scoring and ranking module.
"""

from src.discovery import calculate_score, discover_relevant_pages, ADMISSION_SIGNALS, TUITION_SIGNALS

def test_calculate_score():
    url = "https://www.example.edu/admissions/apply-now"
    title = "Undergraduate Admissions and Applications"
    html = "<h1>How to Apply</h1><h3>Deadline Info</h3>"
    
    adm_score = calculate_score(url, title, html, ADMISSION_SIGNALS)
    tui_score = calculate_score(url, title, html, TUITION_SIGNALS)
    
    assert adm_score > 0
    assert adm_score > tui_score

def test_discover_relevant_pages():
    pages = {
        "https://www.example.edu": {
            "url": "https://www.example.edu",
            "title": "Example University Home",
            "html": "Welcome to our home page.",
            "depth": 0,
            "status_code": "200",
            "scraped_at": "2026-06-03 12:00:00"
        },
        "https://www.example.edu/admissions": {
            "url": "https://www.example.edu/admissions",
            "title": "Admissions Office",
            "html": "Learn how to apply and deadline details.",
            "depth": 1,
            "status_code": "200",
            "scraped_at": "2026-06-03 12:00:00"
        },
        "https://www.example.edu/cost-and-fees": {
            "url": "https://www.example.edu/cost-and-fees",
            "title": "Tuition Costs and Financial Aid",
            "html": "Understand tuition fees and calculator tools.",
            "depth": 1,
            "status_code": "200",
            "scraped_at": "2026-06-03 12:00:00"
        }
    }
    
    top_adm, top_tui, home = discover_relevant_pages(pages, top_n=1)
    
    assert len(home) == 1
    assert home[0]["url"] == "https://www.example.edu"
    assert len(top_adm) == 1
    assert top_adm[0]["url"] == "https://www.example.edu/admissions"
    assert len(top_tui) == 1
    assert top_tui[0]["url"] == "https://www.example.edu/cost-and-fees"
