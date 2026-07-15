import ast
import os
import shutil
from pathlib import Path

def keep_functions(filepath, keep_names, extra_imports):
    with open(filepath, 'r') as f:
        source = f.read()
    module = ast.parse(source)
    lines = source.split('\n')
    
    remove_ranges = []
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name not in keep_names:
            start = node.lineno
            if node.decorator_list:
                start = node.decorator_list[0].lineno
            remove_ranges.append((start - 1, node.end_lineno))
            
    out_lines = []
    for i, line in enumerate(lines):
        remove = False
        for r in remove_ranges:
            if r[0] <= i < r[1]:
                remove = True
                break
        if not remove:
            out_lines.append(line)
            
    content = '\n'.join(out_lines)
    
    # insert extra imports after load_dotenv()
    if extra_imports:
        content = content.replace("load_dotenv()", "load_dotenv()\n" + extra_imports)
        
    # for main, we also need to remove the __main__ block if it's a submodule
    if filepath != "src/laptopfinder/runners/ebay_hunter.py":
        content = content.split('if __name__ == "__main__":')[0]
        
    with open(filepath, 'w') as f:
        f.write(content)

def main():
    src = "src/laptopfinder/runners/ebay_hunter.py"
    out_dir = Path("src/laptopfinder/runners/hunter")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "__init__.py", "w") as f:
        f.write("")

    mapping = {
        'api.py': (['log', '_api_base', '_load_cached_token', 'get_ebay_token', '_marketplace_id', 'ebay_get', 'browse_search', 'get_item', '_fetch_image_bytes'], ""),
        'search.py': (['_build_filter', 'build_queries', 'summary_to_row', '_num', 'collect_corpus'], "from .api import browse_search, log\n"),
        'llm.py': (['gemini_client', '_gemini_json', 'triage_corpus', 'recover_vram_from_images', 'enrich_listing'], "from .api import _fetch_image_bytes, log\n"),
        'enrich.py': (['aspects_to_dict', 'build_listing_text', 'build_metadata', 'build_handoff', 'enrich_and_decide'], "from .api import get_item, log\nfrom .llm import recover_vram_from_images, enrich_listing\nfrom .search import _num\n"),
        'score.py': (['compute_baselines', 'annotate_mispricing', 'is_top_acquisition'], ""),
        'state.py': (['load_seen', 'save_seen', '_now', 'write_jsonl'], ""),
        'alert.py': (['render_email', 'send_email'], "from .state import _now\nfrom .api import log\n")
    }

    for fname, (funcs, extra_imports) in mapping.items():
        dst = out_dir / fname
        shutil.copy(src, dst)
        keep_functions(str(dst), funcs, extra_imports)

    # Now for main ebay_hunter.py
    main_funcs = ['run', 'build_parser', 'main']
    main_imports = """
from .hunter.api import get_ebay_token, log
from .hunter.search import collect_corpus
from .hunter.llm import gemini_client, triage_corpus
from .hunter.enrich import enrich_and_decide
from .hunter.score import compute_baselines, annotate_mispricing, is_top_acquisition
from .hunter.state import load_seen, save_seen, write_jsonl
from .hunter.alert import send_email, render_email
"""
    keep_functions(src, main_funcs, main_imports)

if __name__ == '__main__':
    main()
