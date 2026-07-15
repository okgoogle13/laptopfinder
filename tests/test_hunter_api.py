from unittest.mock import patch, MagicMock
from laptopfinder.runners.hunter.api import ebay_get

@patch("laptopfinder.runners.hunter.api.urllib.request.urlopen")
def test_ebay_get_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"test": "data"}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    res = ebay_get("path", {"p": 1}, "fake_token")
    assert res == {"test": "data"}

@patch("laptopfinder.runners.hunter.api.urllib.request.urlopen")
def test_ebay_get_retry_on_429(mock_urlopen):
    import urllib.error
    err = urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"test": "data2"}'
    mock_resp.__enter__.return_value = mock_resp
    
    mock_urlopen.side_effect = [err, mock_resp]
    
    with patch("laptopfinder.runners.hunter.api.time.sleep") as mock_sleep:
        res = ebay_get("path", {}, "fake_token")
        assert res == {"test": "data2"}
        mock_sleep.assert_called_once()

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
