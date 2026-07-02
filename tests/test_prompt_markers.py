from pathlib import Path


def test_prompt_files_have_sentinel_markers():
    prompt_dir = Path(__file__).parent.parent / "prompts"
    expected = {
        "comet_discovery_agent.txt": ["TARGETS", "UMA_MIN_RAM_GB"],
        "alternative_silicon_gemini.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
        "alternative_silicon_perplexity.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
    }
    for filename, markers in expected.items():
        content = (prompt_dir / filename).read_text()
        for name in markers:
            assert f"<!-- BEGIN_INJECT:{name} -->" in content, f"{filename} missing BEGIN_INJECT:{name}"
            assert f"<!-- END_INJECT:{name} -->" in content, f"{filename} missing END_INJECT:{name}"
