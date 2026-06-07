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


def test_parse_cciobjects_filters_noise_articles():
    import json
    
    # Construct a mock cciobjects payload containing both noise articles and valid news articles
    mock_payload = {
        "id": "12345",
        "children": [
            {
                "kind": "Page",
                "attributes": {"Name": "News Page"},
                "children": [
                    # Noise items (should be filtered)
                    {"kind": "Article", "id": "noise_1", "attributes": {"Headline": "v3"}, "content": [{"reference": "1.html"}]},
                    {"kind": "Article", "id": "noise_2", "attributes": {"Headline": "p2"}, "content": [{"reference": "2.html"}]},
                    {"kind": "Article", "id": "noise_3", "attributes": {"Headline": "vertical1"}, "content": [{"reference": "3.html"}]},
                    {"kind": "Article", "id": "noise_4", "attributes": {"Headline": "picture3"}, "content": [{"reference": "4.html"}]},
                    {"kind": "Article", "id": "noise_5", "attributes": {"Headline": "14805"}, "content": [{"reference": "5.html"}]},
                    {"kind": "Article", "id": "noise_6", "attributes": {"Headline": "23bg"}, "content": [{"reference": "6.html"}]},
                    {"kind": "Article", "id": "noise_7", "attributes": {"Headline": "27HyNearby2"}, "content": [{"reference": "7.html"}]},
                    {"kind": "Article", "id": "noise_8", "attributes": {"Headline": "27HyPointr"}, "content": [{"reference": "8.html"}]},
                    {"kind": "Article", "id": "noise_9", "attributes": {"Headline": "promo"}, "content": [{"reference": "9.html"}]},
                    {"kind": "Article", "id": "noise_10", "attributes": {"Headline": "promo3 (2)"}, "content": [{"reference": "10.html"}]},
                    {"kind": "Article", "id": "noise_11", "attributes": {"Headline": "promo_lead_big"}, "content": [{"reference": "11.html"}]},
                    {"kind": "Article", "id": "noise_12", "attributes": {"Headline": "TH28 promo vertical 1"}, "content": [{"reference": "12.html"}]},
                    {"kind": "Article", "id": "noise_13", "attributes": {"Headline": "promo (2)"}, "content": [{"reference": "13.html"}]},
                    {"kind": "Article", "id": "noise_14", "attributes": {"Headline": "SUDOKU"}, "content": [{"reference": "14.html"}]},
                    {"kind": "Article", "id": "noise_15", "attributes": {"Headline": "Sudoku_solution"}, "content": [{"reference": "15.html"}]},
                    {"kind": "Article", "id": "noise_16", "attributes": {"Headline": "text_feedback"}, "content": [{"reference": "16.html"}]},
                    {"kind": "Article", "id": "noise_17", "attributes": {"Headline": "scoreboard"}, "content": [{"reference": "17.html"}]},
                    {"kind": "Article", "id": "noise_18", "attributes": {"Headline": "the results"}, "content": [{"reference": "18.html"}]},
                    {"kind": "Article", "id": "noise_19", "attributes": {"Headline": "live telecast"}, "content": [{"reference": "19.html"}]},
                    {"kind": "Article", "id": "noise_20", "attributes": {"Headline": "ASKUS"}, "content": [{"reference": "20.html"}]},
                    {"kind": "Article", "id": "noise_21", "attributes": {"Headline": "BIG SHOT"}, "content": [{"reference": "21.html"}]},
                    {"kind": "Article", "id": "noise_22", "attributes": {"Headline": "The DAILY QUIZ"}, "content": [{"reference": "22.html"}]},
                    {"kind": "Article", "id": "noise_23", "attributes": {"Headline": "Former Prime Minister ... Here is a quiz on ..."}, "content": [{"reference": "23.html"}]},
                    {"kind": "Article", "id": "noise_24", "attributes": {"Headline": " \xa0 SUDOKU \n "}, "content": [{"reference": "24.html"}]},
                    {"kind": "Article", "id": "noise_25", "attributes": {"Headline": ""}, "content": [{"reference": "25.html"}]},
                    {"kind": "Article", "id": "noise_26", "attributes": {"Headline": "   \n  "}, "content": [{"reference": "26.html"}]},
                    
                    # Valid headlines (should be kept)
                    {"kind": "Article", "id": "valid_1", "attributes": {"Headline": "SC upholds SIR, says it is EC's constitutional duty"}, "content": [{"reference": "v1.html"}]},
                    {"kind": "Article", "id": "valid_2", "attributes": {"Headline": "UPSC releases provisional answer key of Prelims exam"}, "content": [{"reference": "v2.html"}]},
                    {"kind": "Article", "id": "valid_3", "attributes": {"Headline": "3 doctors held"}, "content": [{"reference": "v3.html"}]},
                    {"kind": "Article", "id": "valid_4", "attributes": {"Headline": "10 killed in accident"}, "content": [{"reference": "v4.html"}]},
                    {"kind": "Article", "id": "valid_5", "attributes": {"Headline": "Promotion of trade negotiations"}, "content": [{"reference": "v5.html"}]},
                    {"kind": "Article", "id": "valid_6", "attributes": {"Headline": "Promoting green energy"}, "content": [{"reference": "v6.html"}]},
                    {"kind": "Article", "id": "valid_7", "attributes": {"Headline": "Fire breaks out in nearby building"}, "content": [{"reference": "v7.html"}]},
                    {"kind": "Article", "id": "valid_8", "attributes": {"Headline": "Chennai school wins state quiz contest"}, "content": [{"reference": "v8.html"}]},
                    {"kind": "Article", "id": "valid_9", "attributes": {"Headline": "5G rollout starts in metro cities"}, "content": [{"reference": "v9.html"}]},
                    {"kind": "Article", "id": "valid_10", "attributes": {"Headline": "3D printing of organs"}, "content": [{"reference": "v10.html"}]},
                    {"kind": "Article", "id": "valid_11", "attributes": {"Headline": "24x7 water supply assured"}, "content": [{"reference": "v11.html"}]},
                    {"kind": "Article", "id": "valid_12", "attributes": {"Headline": " \xa0 5G rollout starts \n "}, "content": [{"reference": "v12.html"}]}
                ]
            }
        ]
    }
    
    result = parse_cciobjects(json.dumps(mock_payload))
    pages = result["pages"]
    assert len(pages) == 1
    
    articles = pages[0]["articles"]
    # Verify that only the 12 valid articles are present
    assert len(articles) == 12
    
    valid_ids = {art["id"] for art in articles}
    assert valid_ids == {
        "valid_1", "valid_2", "valid_3", "valid_4", "valid_5", "valid_6",
        "valid_7", "valid_8", "valid_9", "valid_10", "valid_11", "valid_12"
    }


def test_noise_article_news_in_numbers_no_underscores():
    from src.parser import _is_noise_article
    assert _is_noise_article("news in numbers 123") is True


def test_get_article_text_block_fallbacks():
    from src.parser import get_article_text_block
    
    # Case 1: body exists
    art_body = {
        "headline": "Head",
        "highlights": ["High1"],
        "body": ["Body1", "Body2"]
    }
    assert get_article_text_block(art_body) == "Body1\nBody2"
    
    # Case 2: body is empty, highlights exist
    art_high = {
        "headline": "Head",
        "highlights": ["High1", "High2"],
        "body": []
    }
    assert get_article_text_block(art_high) == "High1\nHigh2"
    
    # Case 3: body and highlights empty, headline exists
    art_head = {
        "headline": "Head Text",
        "highlights": [],
        "body": []
    }
    assert get_article_text_block(art_head) == "Head Text"
    
    # Case 4: everything is empty or missing
    art_empty = {
        "headline": "",
        "highlights": [],
        "body": []
    }
    with pytest.raises(ValueError) as excinfo:
        get_article_text_block(art_empty)
    assert "No article content available" in str(excinfo.value)




