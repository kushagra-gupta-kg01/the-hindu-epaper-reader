import pytest
import os

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture
def catalog_mock_data():
    with open(os.path.join(FIXTURES_DIR, "catalog_mock.json"), "r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture
def cciobjects_mock_data():
    with open(os.path.join(FIXTURES_DIR, "cciobjects_mock.json"), "r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture
def article_mock_html():
    with open(os.path.join(FIXTURES_DIR, "article_mock.html"), "r", encoding="utf-8") as f:
        return f.read()
