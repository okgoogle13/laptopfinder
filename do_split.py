import ast
import os
from pathlib import Path

def get_file_content(funcs, names):
    out = []
    for name in names:
        if name in funcs:
            out.append(funcs[name])
            out.append("\n")
    return "\n".join(out)

def main():
    src_file = "src/laptopfinder/runners/ebay_hunter.py"
    with open(src_file, 'r') as f:
        source = f.read()

    # Get imports
    import_lines = []
    for line in source.split('\n'):
        if line.startswith('import ') or line.startswith('from '):
            import_lines.append(line)
        if line.startswith('load_dotenv()'):
            import_lines.append(line)
    imports_str = "\n".join(import_lines) + "\n\n"

    # Get constants
    const_lines = []
    in_const = False
    for line in source.split('\n'):
        if line.startswith('MAX_VISION_IMAGES') or line.startswith('IMAGE_FETCH_TIMEOUT') or line.startswith('UNDERPRICE_DISCOUNT'):
            const_lines.append(line)
        if line.startswith('NEGATIVE_KEYWORDS'):
            in_const = True
        if in_const:
            const_lines.append(line)
            if ']' in line:
                in_const = False
        if line.startswith('CORPUS_PATH') or line.startswith('RESULTS_PATH') or line.startswith('SEEN_PATH'):
            const_lines.append(line)
    
    # We also have prompt constants: TRIAGE_INSTRUCTION, VISION_INSTRUCTION, ENRICH_INSTRUCTION
    for name in ['TRIAGE_INSTRUCTION', 'VISION_INSTRUCTION', 'ENRICH_INSTRUCTION']:
        in_prompt = False
        for line in source.split('\n'):
            if line.startswith(f'{name} = """'):
                in_prompt = True
            if in_prompt:
                const_lines.append(line)
                if line.endswith('"""') and not line.startswith(f'{name} = """'):
                    in_prompt = False
                elif line.startswith(f'{name} = """') and line.endswith('"""') and len(line) > len(f'{name} = """'):
                     in_prompt = False
        
    consts_str = "\n".join(const_lines) + "\n\n"

    module = ast.parse(source)
    lines = source.split('\n')
    
    funcs = {}
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            start_line = node.lineno
            if node.decorator_list:
                start_line = node.decorator_list[0].lineno
            end_line = node.end_lineno
            func_source = '\n'.join(lines[start_line - 1 : end_line])
            funcs[node.name] = func_source

    mapping = {
        'api.py': ['log', '_api_base', '_load_cached_token', 'get_ebay_token', '_marketplace_id', 'ebay_get', 'browse_search', 'get_item', '_fetch_image_bytes'],
        'search.py': ['_build_filter', 'build_queries', 'summary_to_row', '_num', 'collect_corpus'],
        'llm.py': ['gemini_client', '_gemini_json', 'triage_corpus', 'recover_vram_from_images', 'enrich_listing'],
        'enrich.py': ['aspects_to_dict', 'build_listing_text', 'build_metadata', 'build_handoff', 'enrich_and_decide'],
        'score.py': ['compute_baselines', 'annotate_mispricing', 'is_top_acquisition'],
        'state.py': ['load_seen', 'save_seen', '_now', 'write_jsonl'],
        'alert.py': ['render_email', 'send_email']
    }

    out_dir = Path("src/laptopfinder/runners/hunter")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "__init__.py", "w") as f:
        f.write("")

    for fname, func_names in mapping.items():
        content = "from __future__ import annotations\n\n" + imports_str + consts_str
        # we need to cross-import things
        content += "from .api import *\nfrom .search import *\nfrom .llm import *\nfrom .enrich import *\nfrom .score import *\nfrom .state import *\nfrom .alert import *\n\n"
        content += get_file_content(funcs, func_names)
        with open(out_dir / fname, "w") as f:
            f.write(content)

    # Re-write ebay_hunter.py
    main_content = "from __future__ import annotations\n\n" + imports_str + consts_str
    main_content += "from .hunter.api import *\nfrom .hunter.search import *\nfrom .hunter.llm import *\nfrom .hunter.enrich import *\nfrom .hunter.score import *\nfrom .hunter.state import *\nfrom .hunter.alert import *\n\n"
    main_content += get_file_content(funcs, ['run', 'build_parser', 'main'])
    main_content += '\nif __name__ == "__main__":\n    sys.exit(main())\n'
    
    with open(src_file, "w") as f:
        f.write(main_content)

if __name__ == '__main__':
    main()
