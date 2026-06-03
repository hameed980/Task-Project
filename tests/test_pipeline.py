"""
Unit tests for pipeline normalization functions.
"""

from src.pipeline import normalize_date, normalize_currency

def test_normalize_date():
    assert normalize_date("2026-12-15") == "2026-12-15"
    assert normalize_date("December 15, 2026") == "2026-12-15"
    assert normalize_date("12/15/2026") == "2026-12-15"
    assert normalize_date("invalid-date-string") == "invalid-date-string"
    assert normalize_date(None) is None

def test_normalize_currency():
    assert normalize_currency(60150) == 60150
    assert normalize_currency("60,150") == 60150
    assert normalize_currency("$60,150 USD") == 60150
    assert normalize_currency("Free") is None
    assert normalize_currency(None) is None
