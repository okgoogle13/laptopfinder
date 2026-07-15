from unittest.mock import patch, MagicMock
from laptopfinder.runners.legacy.hunter.llm import triage_corpus, recover_vram_from_images

@patch("laptopfinder.runners.legacy.hunter.llm.gemini_client")
def test_triage_corpus_empty(mock_client):
    res = triage_corpus(mock_client, "model", [])
    assert res == {}

@patch("laptopfinder.runners.legacy.hunter.llm._gemini_json")
def test_triage_corpus_parses_json(mock_gemini_json):
    mock_gemini_json.return_value = {
        "listings": [{"item_id": "1", "is_relevant": True}]
    }
    corpus = [{"item_id": "1", "title": "Test", "price_aud": 1000, "condition": "NEW", "seller_feedback_pct": 100}]
    res = triage_corpus(None, "model", corpus)
    assert len(res) == 1
    assert res["1"]["item_id"] == "1"

@patch("laptopfinder.runners.legacy.hunter.llm.gemini_client")
def test_recover_vram_from_images(mock_client):
    assert recover_vram_from_images(mock_client, "model", {}) is None

    with patch("laptopfinder.runners.legacy.hunter.llm._gemini_json", return_value={"vram_gb": 16, "verbatim_quote": "16GB GDDR6", "confidence": 1.0}):
        with patch("laptopfinder.runners.legacy.hunter.llm._fetch_image_bytes", return_value=(b"A"*20000, "image/jpeg")):
            res = recover_vram_from_images(mock_client, "model", {"image": {"imageUrl": "http"}})
            assert res == {"vram_gb": 16, "verbatim_quote": "16GB GDDR6", "confidence": 1.0}


@patch("laptopfinder.runners.legacy.hunter.llm.genai.Client")
def test_gemini_json_retry_on_429(mock_client_cls):
    from google.genai.errors import APIError
    from laptopfinder.runners.legacy.hunter.llm import _gemini_json
    
    mock_client = mock_client_cls.return_value
    err = APIError(429, {"error": "Too Many Requests"})
    
    mock_resp = MagicMock()
    mock_resp.text = '{"success": true}'
    
    mock_client.models.generate_content.side_effect = [err, mock_resp]
    
    with patch("time.sleep") as mock_sleep:
        res = _gemini_json(mock_client, "model", [])
        assert res == {"success": True}
        mock_sleep.assert_called_once()
