from unittest.mock import patch, MagicMock
from laptopfinder.runners.hunter.alert import render_email, send_email

def test_render_email():
    alerts = [
        {
            "canonical_model": "Test Model",
            "price_aud": 2000,
            "baseline_median_aud": 2500,
            "price_delta_aud": -500,
            "item_web_url": "http://x",
            "decision": {
                "llm_index_score": 85,
                "vram_gb": 16,
                "recommended_action": "SHORTLIST",
                "reasons": ["A", "B", "C"]
            }
        }
    ]
    txt = render_email(alerts)
    assert "Test Model" in txt
    assert "AUD 2000" in txt
    assert "-500 vs median; median 2500" in txt
    assert "index 85/100" in txt
    assert "http://x" in txt

@patch("laptopfinder.runners.hunter.alert.smtplib.SMTP_SSL")
def test_send_email_success(mock_smtp, monkeypatch):
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")
    monkeypatch.setenv("ALERT_EMAIL_TO", "t")
    monkeypatch.setenv("SMTP_PORT", "465")
    
    mock_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_instance
    
    res = send_email([])
    assert res is True
    mock_instance.login.assert_called_once_with("u", "p")
    mock_instance.send_message.assert_called_once()

@patch("laptopfinder.runners.hunter.alert.smtplib.SMTP_SSL")
def test_send_email_network_error(mock_smtp, monkeypatch):
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")
    monkeypatch.setenv("ALERT_EMAIL_TO", "t")
    monkeypatch.setenv("SMTP_PORT", "465")
    
    mock_smtp.side_effect = Exception("network down")
    
    res = send_email([])
    assert res is False # Should catch exception and return False
