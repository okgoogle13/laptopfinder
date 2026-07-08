import glob

files = glob.glob("src/laptopfinder/runners/hunter/*.py") + ["src/laptopfinder/runners/ebay_hunter.py"]

for filepath in files:
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    # remove all load_dotenv()
    new_lines = [line for line in lines if line.strip() != "load_dotenv()"]
    
    # find the last import line
    last_import_idx = -1
    for i, line in enumerate(new_lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i
            
    if last_import_idx != -1:
        new_lines.insert(last_import_idx + 1, "load_dotenv()\n")
        
    with open(filepath, "w") as f:
        f.writelines(new_lines)
