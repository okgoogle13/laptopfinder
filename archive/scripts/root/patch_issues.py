import os
import re

# Patch llm.py
with open("src/laptopfinder/runners/hunter/llm.py", "r") as f:
    llm_content = f.read()

# Add retry logic to _gemini_json
gemini_json_replacement = """def _gemini_json(client: genai.Client, model: str, parts: list, temperature: float = 0.1):
    \"\"\"Single Gemini call returning parsed JSON (application/json mode) with 429 backoff.\"\"\"
    from google.genai.errors import APIError
    import time
    
    retries = 4
    backoff = 2.0
    
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=temperature,
                ),
            )
            return json.loads(response.text)
        except APIError as exc:
            if exc.code == 429 and attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                log(f"Gemini HTTP 429 — backing off {wait:.0f}s")
                time.sleep(wait)
                continue
            raise
"""

# Find the old _gemini_json
old_gemini_json_pattern = r"def _gemini_json\(client: genai\.Client, model: str, parts: list, temperature: float = 0\.1\):.*?return json\.loads\(response\.text\)"
llm_content = re.sub(old_gemini_json_pattern, gemini_json_replacement, llm_content, flags=re.DOTALL)

with open("src/laptopfinder/runners/hunter/llm.py", "w") as f:
    f.write(llm_content)

# Patch test_hunter_llm.py
with open("tests/test_hunter_llm.py", "r") as f:
    test_llm = f.read()

test_llm_add = """
@patch("laptopfinder.runners.hunter.llm.genai.Client")
def test_gemini_json_retry_on_429(mock_client_cls):
    from google.genai.errors import APIError
    from laptopfinder.runners.hunter.llm import _gemini_json
    
    mock_client = mock_client_cls.return_value
    err = APIError("Too Many Requests", code=429)
    
    mock_resp = MagicMock()
    mock_resp.text = '{"success": true}'
    
    mock_client.models.generate_content.side_effect = [err, mock_resp]
    
    with patch("laptopfinder.runners.hunter.llm.time.sleep") as mock_sleep:
        res = _gemini_json(mock_client, "model", [])
        assert res == {"success": True}
        mock_sleep.assert_called_once()
"""
if "test_gemini_json_retry_on_429" not in test_llm:
    with open("tests/test_hunter_llm.py", "a") as f:
        f.write("\nfrom unittest.mock import MagicMock\n" + test_llm_add)

# Patch test_hunter_api.py
with open("tests/test_hunter_api.py", "r") as f:
    test_api = f.read()

test_api_add = """
@patch("laptopfinder.runners.hunter.api.urllib.request.urlopen")
@patch("laptopfinder.runners.hunter.api.get_ebay_token")
def test_ebay_get_retry_on_401(mock_get_token, mock_urlopen):
    import urllib.error
    err = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"test": "data_after_401"}'
    mock_resp.__enter__.return_value = mock_resp
    
    mock_urlopen.side_effect = [err, mock_resp]
    mock_get_token.return_value = "new_token"
    
    res = ebay_get("path", {}, "old_token")
    assert res == {"test": "data_after_401"}
    mock_get_token.assert_called_once_with(force=True)
"""
if "test_ebay_get_retry_on_401" not in test_api:
    with open("tests/test_hunter_api.py", "a") as f:
        f.write(test_api_add)

