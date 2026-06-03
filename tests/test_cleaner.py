"""
Unit tests for the HTML cleaner script.
"""

from src.cleaner import clean_html

def test_clean_html_strips_boilerplate():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <style>body { color: red; }</style>
            <script>console.log('hello');</script>
        </head>
        <body>
            <header>
                <nav>
                    <a href="/">Home</a>
                </nav>
            </header>
            <div id="sidebar" class="menu-navigation">
                Sidebar navigation links here
            </div>
            <main>
                <h1>Welcome to Bucknell University</h1>
                <p>This is the official page.</p>
            </main>
            <footer class="footer-bottom">
                &copy; 2026 Copyright information.
            </footer>
        </body>
    </html>
    """
    
    cleaned = clean_html(html_content)
    
    # Scripts, styles, navs and footers should be stripped
    assert "body { color: red; }" not in cleaned
    assert "console.log" not in cleaned
    assert "Home" not in cleaned
    assert "Sidebar navigation" not in cleaned
    assert "Copyright information" not in cleaned
    
    # Core content should be preserved
    assert "Welcome to Bucknell University" in cleaned
    assert "This is the official page." in cleaned
