"""Prompt content sanity checks."""
from pathlib import Path

PROMPTS = Path(__file__).parent.parent / "prompts"


def test_system_context_mentions_required_platforms():
    text = (PROMPTS / "system_context.md").read_text()
    assert "Apple Silicon UMA" in text
    assert "AMD UMA" in text
    assert "CUDA" in text


def test_bias_guard_requires_justification_for_cuda():
    text = (PROMPTS / "bias_guard_prompt.md").read_text()
    assert "Bias Guard Note" in text
    assert "Apple UMA" in text or "Apple Silicon" in text
    assert "Strix UMA" in text or "Strix Halo" in text
