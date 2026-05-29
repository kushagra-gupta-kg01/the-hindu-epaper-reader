import pytest
from src.parser import parse_catalog, parse_cciobjects, parse_article

def test_parse_catalog(catalog_mock_data):
    # Test valid city key
    issue_id = parse_catalog(catalog_mock_data, "th_delhi")
    assert issue_id == "186654"
    
    # Test another valid city key from mock data
    issue_id_chennai = parse_catalog(catalog_mock_data, "th_chennai")
    assert issue_id_chennai == "186609"
    
    # Test invalid city key raises ValueError
    with pytest.raises(ValueError) as excinfo:
        parse_catalog(catalog_mock_data, "invalid_city")
    assert "City key invalid_city not found" in str(excinfo.value)

def test_parse_cciobjects(cciobjects_mock_data):
    result = parse_cciobjects(cciobjects_mock_data)
    
    assert "issue_id" in result
    # In mock data, the top level id is KLG1M8C9 or similar. Let's make sure it matches
    assert result["issue_id"] is not None
    
    pages = result["pages"]
    assert len(pages) == 22
    
    # Let's inspect Page 3 (Front Page)
    # Page index is 2 (3rd page)
    front_page = next((p for p in pages if p["page_num"] == 3), None)
    assert front_page is not None
    assert front_page["page_name"] == "Front_Pg"
    
    articles = front_page["articles"]
    assert len(articles) > 0
    
    # Check that articles have the correct fields
    first_article = articles[0]
    assert "id" in first_article
    assert "headline" in first_article
    assert "html_ref" in first_article
    assert first_article["html_ref"].endswith(".html")
    assert "images" in first_article
    assert isinstance(first_article["images"], list)

def test_parse_article(article_mock_html):
    article = parse_article(article_mock_html, "GO1G1NQTF.1")
    
    assert article["id"] == "GO1G1NQTF.1"
    assert "IIT team to conduct" in article["headline"]
    assert article["author"] == "Maitri Porecha"
    assert article["dateline"] == "New Delhi"
    
    # Body should be a list of paragraphs
    assert len(article["body"]) > 0
    assert "Following multiple complaints by Class 12 students" in article["body"][0]
    
    # Highlights
    assert len(article["highlights"]) > 0
    assert "It will provide recommendations" in article["highlights"][0]

def test_parse_article_missing_byline():
    minimal_html = """
    <!doctype html>
    <html>
     <body>
      <h1><p>Simple Headline</p></h1>
      <div class="body">
       <p>First paragraph text.</p>
       <p>Second paragraph text.</p>
      </div>
     </body>
    </html>
    """
    article = parse_article(minimal_html, "TEST_ID")
    
    assert article["id"] == "TEST_ID"
    assert article["headline"] == "Simple Headline"
    assert article["author"] is None
    assert article["dateline"] is None
    assert article["body"] == ["First paragraph text.", "Second paragraph text."]
    assert article["highlights"] == []

def test_parse_cciobjects_deduplicates_images():
    import json
    mock_cciobjects = {
        "id": "12345",
        "children": [
            {
                "kind": "Page",
                "attributes": {"Name": "Front Page"},
                "children": [
                    {
                        "kind": "Article",
                        "id": "art_1",
                        "attributes": {"Name": "Test Article", "Headline": "Test Headline"},
                        "content": [
                            {"reference": "art_1.html"},
                            {"reference": "Public/image1.jpg"}
                        ],
                        "children": [
                            {
                                "kind": "Photo",
                                "content": [
                                    {"reference": "Public/image1.jpg"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    result = parse_cciobjects(json.dumps(mock_cciobjects))
    
    pages = result["pages"]
    assert len(pages) == 1
    articles = pages[0]["articles"]
    assert len(articles) == 1
    article = articles[0]
    
    # Assert image is deduplicated (only appears once)
    assert article["images"] == ["Public/image1.jpg"]


def test_parse_catalog_invalid_json():
    with pytest.raises(ValueError) as excinfo:
        parse_catalog("invalid{json", "th_delhi")
    assert "Failed to parse catalog JSON" in str(excinfo.value)


def test_parse_cciobjects_invalid_json():
    with pytest.raises(ValueError) as excinfo:
        parse_cciobjects("invalid{json")
    assert "Failed to parse cciobjects JSON" in str(excinfo.value)


def test_parse_cciobjects_nested_text_html_ref():
    import json
    mock_payload = {
        "id": "test_issue_id",
        "children": [
            {
                "kind": "Page",
                "attributes": {"Name": "Opinion"},
                "children": [
                    {
                        "kind": "Article",
                        "id": "art_nested_text",
                        "attributes": {
                            "Name": "Nested Article",
                            "Headline": "Nested Headline"
                        },
                        "content": [
                            {"reference": "Public/some_image.jpg"}
                        ],
                        "children": [
                            {
                                "kind": "Text",
                                "content": [
                                    {"reference": "nested_article.html"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    result = parse_cciobjects(json.dumps(mock_payload))
    pages = result["pages"]
    assert len(pages) == 1
    articles = pages[0]["articles"]
    assert len(articles) == 1
    assert articles[0]["html_ref"] == "nested_article.html"


def test_parse_article_headline_no_nested_p():
    html_content = """
    <html>
      <body>
        <h1>Headline Text Direct</h1>
        <div class="body">
          <p>Body paragraph.</p>
        </div>
      </body>
    </html>
    """
    article = parse_article(html_content, "art_1")
    assert article["headline"] == "Headline Text Direct"


