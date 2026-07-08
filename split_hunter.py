import ast
from collections import defaultdict

def extract_functions(filepath):
    with open(filepath, 'r') as f:
        source = f.read()
    
    module = ast.parse(source)
    lines = source.split('\n')
    
    funcs = {}
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            # get decorators
            start_line = node.lineno
            if node.decorator_list:
                start_line = node.decorator_list[0].lineno
            end_line = node.end_lineno
            func_source = '\n'.join(lines[start_line - 1 : end_line])
            funcs[node.name] = func_source
    return funcs

if __name__ == '__main__':
    funcs = extract_functions('src/laptopfinder/runners/ebay_hunter.py')
    print("Extracted functions:", list(funcs.keys()))
