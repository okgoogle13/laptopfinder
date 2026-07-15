from pathlib import Path


def test_prompt_files_have_sentinel_markers():
    prompt_dir = Path(__file__).parent.parent / "prompts"
    archive_dir = Path(__file__).parent.parent / "archive" / "prompts"
    expected = {
        prompt_dir / "comet_discovery_agent.txt": ["TARGETS", "UMA_MIN_RAM_GB"],
        archive_dir / "alternative_silicon_gemini.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
        archive_dir / "alternative_silicon_perplexity.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
    }
    for file_path, markers in expected.items():
        content = file_path.read_text()
        for name in markers:
            assert f"<!-- BEGIN_INJECT:{name} -->" in content, f"{file_path.name} missing BEGIN_INJECT:{name}"
            assert f"<!-- END_INJECT:{name} -->" in content, f"{file_path.name} missing END_INJECT:{name}"
