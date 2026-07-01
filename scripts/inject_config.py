import json
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

SRL_PATH = str(_REPO_ROOT / "config" / "static_reference_layer.json")

PROMPT_FILES = [
    str(_REPO_ROOT / "prompts" / "comet_discovery_agent.txt"),
    str(_REPO_ROOT / "prompts" / "alternative_silicon_gemini.txt"),
    str(_REPO_ROOT / "prompts" / "alternative_silicon_perplexity.txt"),
]


def load_srl(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"SRL not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def build_substitutions(srl: dict) -> dict[str, str]:
    gpu_names = list(srl["target_gpus"].keys())
    watch_names = [entry["name"] for entry in srl["watch_list"]]
    # TARGETS (comet discovery): confirmed targets + watch-list as awareness context
    targets_block = "\n".join(f"- {name}" for name in gpu_names + watch_names)
    # TARGET_GPU_LIST (alt-silicon prompts): confirmed targets only — watch-list must not leak
    gpu_list_block = "\n".join(f"- {name}" for name in gpu_names)

    uma = srl["uma_platforms"]
    return {
        "TARGETS": targets_block,
        "TARGET_GPU_LIST": gpu_list_block,
        "UMA_MIN_RAM_GB": str(uma["min_total_ram_gb_to_shortlist"]),
        "UMA_CHIP_PATTERNS": ", ".join(uma["chip_patterns"]),
    }


def inject_file(path: str, substitutions: dict[str, str]) -> int:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    content = p.read_text(encoding="utf-8")
    count = 0
    for key, value in substitutions.items():
        pattern = (
            rf"(<!-- BEGIN_INJECT:{re.escape(key)} -->)"
            rf".*?"
            rf"(<!-- END_INJECT:{re.escape(key)} -->)"
        )
        replacement = rf"\1\n{value}\n\2"
        new_content, n = re.subn(pattern, replacement, content, flags=re.DOTALL)
        if n:
            content = new_content
            count += n

    if count:
        p.write_text(content, encoding="utf-8")
    return count


def main() -> None:
    srl = load_srl(SRL_PATH)
    substitutions = build_substitutions(srl)
    for path in PROMPT_FILES:
        n = inject_file(path, substitutions)
        print(f"{Path(path).name}: {n} block(s) replaced")


if __name__ == "__main__":
    main()
